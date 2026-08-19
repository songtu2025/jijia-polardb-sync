import logging
import hashlib
import json
import re
import time
from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from app.retry import retry_call


logger = logging.getLogger(__name__)
RAW_JSON_FIELD_PATTERN = re.compile(r"^[A-Za-z0-9_.]+$")
DATE_PARAM_TEMPLATE_PATTERN = re.compile(r"^\{\{\s*(today|yesterday|days_ago:(\d+))\s*\}\}$")
SENSITIVE_RESPONSE_ERROR_MESSAGE = "sensitive response details redacted"


class ApiRequestError(Exception):
    """带请求上下文的 API 请求异常。

    普通异常只包含错误消息，不足以排查是哪一个 URL、哪一组参数失败。这里把
    可安全落库的请求信息一起带出，供 failed_request_log 使用。
    """

    # 失败日志只需要请求上下文，不保存 accessToken 这类鉴权头。
    def __init__(
        self,
        original_error: Exception,
        request_url: str | None,
        request_method: str,
        request_params: dict[str, Any],
        attempt_count: int,
    ):
        super().__init__(str(original_error))
        self.original_error = original_error
        self.request_url = request_url
        self.request_method = request_method
        self.request_params = request_params
        self.attempt_count = attempt_count

    @property
    def retry_count(self) -> int:
        """返回失败前已经发生的重试次数。"""
        return max(self.attempt_count - 1, 0)

class InvalidatedApiTransactionError(Exception):
    """携带失效事务外层收尾所需的最小执行状态。"""

    def __init__(
        self,
        original_error: DBAPIError,
        api_code: str,
        request_count: int,
        api_started_at: datetime,
    ):
        super().__init__(str(original_error))
        self.original_error = original_error
        self.api_code = api_code
        self.request_count = request_count
        self.api_started_at = api_started_at



class SyncEngine:
    """同步调度核心。

    该类负责把 API 配置、HTTP 客户端和数据库写入串起来。第一版以保存原始
    JSON 为主，不在这里做复杂字段转换，确保备份链路简单可靠。
    """

    def __init__(self, api_configs: list[dict[str, Any]], engine: Engine | None = None):
        """保存接口配置和可选数据库引擎。

        dry-run 不需要数据库；mock、单接口测试和真实同步都需要 engine。
        """
        self.api_configs = api_configs
        self.engine = engine

    def dry_run(self) -> None:
        """只检查已启用的 API 配置能否被加载。

        这个模式不请求积加接口、不连接数据库，适合快速确认 YAML 基本可读。
        """
        enabled_apis = self._enabled_apis()
        logger.info("loaded %s enabled API config(s)", len(enabled_apis))
        for api in enabled_apis:
            logger.info("api config ready: %s", api.get("api_code", "<missing api_code>"))

    def probe_api(self, api_code: str, api_client: Any, token: Any) -> dict[str, int | str]:
        """只请求分页接口首页，返回后续同步所需的安全汇总。

        预检不创建数据库引擎、不写入批次、raw、checkpoint 或失败日志。"""

        api = self._api_by_code(api_code)
        page_config = api.get("page") or {}
        if not page_config.get("enabled") or not page_config.get("total_field"):
            raise ValueError("pagination probe requires enabled page config and total_field")
        if api.get("param_source"):
            raise ValueError("pagination probe does not support param_source APIs")
        if (api.get("date_window") or {}).get("enabled"):
            raise ValueError("pagination probe does not support date_window APIs")

        page_no_field = str(page_config.get("page_no_field") or "page")
        page_size_field = str(page_config.get("page_size_field") or "pagesize")
        page_size = int(page_config.get("page_size") or 20)
        params = self._request_params(api)
        self._set_by_path(
            params,
            page_no_field,
            int(self._get_by_path(params, page_no_field) or 1),
        )
        self._set_by_path(params, page_size_field, page_size)

        payload, request_count = self._request_with_retry(api, api_client, token, params)
        total_count = self._response_total(payload, api)
        if total_count is None:
            raise ValueError("pagination probe response does not contain a valid total")
        required_pages = self._required_page_count(api, total_count)
        if required_pages is None:
            raise ValueError("pagination probe cannot calculate required pages")
        return {
            "api_code": api_code,
            "total_count": total_count,
            "page_size": page_size,
            "required_pages": required_pages,
            "request_count": request_count,
        }

    def mock_sync(self) -> str:
        """写入一批 mock 同步数据。

        用于没有真实积加 API 或测试账号时验证数据库表结构、幂等写入和日志表
        是否可用。返回本次生成的 sync_batch_no。
        """
        if self.engine is None:
            raise ValueError("mock sync requires database engine")

        enabled_apis = self._enabled_apis()
        batch_no = self._new_batch_no()
        started_at = datetime.now()
        success_api_count = 0
        failed_api_count = 0

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO sync_batch (
                      sync_batch_no, status, started_at, total_api_count
                    ) VALUES (
                      :sync_batch_no, 'running', :started_at, :total_api_count
                    )
                    """
                ),
                {
                    "sync_batch_no": batch_no,
                    "started_at": started_at,
                    "total_api_count": len(enabled_apis),
                },
            )

            for api in enabled_apis:
                # mock 模式也按真实同步的日志粒度写入，方便验证排障链路。
                api_code = api.get("api_code")
                api_started_at = datetime.now()
                try:
                    items = self._mock_items(api)
                    for item in items:
                        self._insert_raw_item(connection, api, item, batch_no)

                    connection.execute(
                        text(
                            """
                            INSERT INTO sync_api_log (
                              sync_batch_no, api_code, status, request_count,
                              success_count, failed_count, started_at, finished_at
                            ) VALUES (
                              :sync_batch_no, :api_code, 'success', 1,
                              :success_count, 0, :started_at, :finished_at
                            )
                            """
                        ),
                        {
                            "sync_batch_no": batch_no,
                            "api_code": api_code,
                            "success_count": len(items),
                            "started_at": api_started_at,
                            "finished_at": datetime.now(),
                        },
                    )
                    success_api_count += 1
                except Exception as error:
                    failed_api_count += 1
                    connection.execute(
                        text(
                            """
                            INSERT INTO sync_api_log (
                              sync_batch_no, api_code, status, request_count,
                              success_count, failed_count, started_at,
                              finished_at, error_message
                            ) VALUES (
                              :sync_batch_no, :api_code, 'failed', 1,
                              0, 1, :started_at, :finished_at, :error_message
                            )
                            """
                        ),
                        {
                            "sync_batch_no": batch_no,
                            "api_code": api_code,
                            "started_at": api_started_at,
                            "finished_at": datetime.now(),
                            "error_message": str(error),
                        },
                    )

            status = "success" if failed_api_count == 0 else "partial_failed"
            connection.execute(
                text(
                    """
                    UPDATE sync_batch
                    SET status = :status,
                        finished_at = :finished_at,
                        success_api_count = :success_api_count,
                        failed_api_count = :failed_api_count,
                        message = :message
                    WHERE sync_batch_no = :sync_batch_no
                    """
                ),
                {
                    "status": status,
                    "finished_at": datetime.now(),
                    "success_api_count": success_api_count,
                    "failed_api_count": failed_api_count,
                    "message": "mock sync finished",
                    "sync_batch_no": batch_no,
                },
            )

        logger.info("mock sync finished: %s", batch_no)
        return batch_no

    def sync_api_configs(self) -> int:
        """把 YAML API 配置同步到 api_config 表。

        这是配置快照命令，不请求任何积加业务接口。重复执行按 api_code
        upsert，方便数据库侧查看当前项目认定的接口配置。
        """
        if self.engine is None:
            raise ValueError("sync api configs requires database engine")

        with self.engine.begin() as connection:
            for api in self.api_configs:
                connection.execute(
                    text(
                        """
                        INSERT INTO api_config (
                          api_code, api_name, enabled, method, path, config_json
                        ) VALUES (
                          :api_code, :api_name, :enabled, :method, :path, :config_json
                        )
                        ON DUPLICATE KEY UPDATE
                          api_name = VALUES(api_name),
                          enabled = VALUES(enabled),
                          method = VALUES(method),
                          path = VALUES(path),
                          config_json = VALUES(config_json)
                        """
                    ),
                    {
                        "api_code": api["api_code"],
                        "api_name": api.get("name") or api["api_code"],
                        "enabled": 1 if api["enabled"] is True else 0,
                        "method": str(api.get("method", "POST")).upper(),
                        "path": api["path"],
                        "config_json": json.dumps(api, ensure_ascii=False, sort_keys=True, default=str),
                    },
                )

        return len(self.api_configs)

    def test_api_once(self, api_code: str, api_client: Any, token: Any) -> dict[str, Any]:
        """执行单个真实 API 并写入数据库。

        该方法会创建独立批次，便于接入新接口时按 api_code 单独验证请求、
        分页、入库和日志，不影响完整同步任务的批次统计。
        """
        if self.engine is None:
            raise ValueError("test api requires database engine")

        api = self._api_by_code(api_code)
        if api.get("commit_per_page"):
            return self._test_api_once_commit_per_page(api, api_client, token)

        batch_no = self._new_batch_no()
        started_at = datetime.now()

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO sync_batch (
                      sync_batch_no, status, started_at, total_api_count
                    ) VALUES (
                      :sync_batch_no, 'running', :started_at, 1
                    )
                    """
                ),
                {"sync_batch_no": batch_no, "started_at": started_at},
            )

        result = self._sync_api_with_transaction(api, batch_no, api_client, token)

        status = "success" if result["failed_count"] == 0 else "failed"
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE sync_batch
                    SET status = :status,
                        finished_at = :finished_at,
                        success_api_count = :success_api_count,
                        failed_api_count = :failed_api_count,
                        message = :message
                    WHERE sync_batch_no = :sync_batch_no
                    """
                ),
                {
                    "status": status,
                    "finished_at": datetime.now(),
                    "success_api_count": 1 if result["failed_count"] == 0 else 0,
                    "failed_api_count": result["failed_count"],
                    "message": "test api finished",
                    "sync_batch_no": batch_no,
                },
            )

        return {
            "batch_no": batch_no,
            "item_count": result["item_count"],
            "request_count": result["request_count"],
            "failed_count": result["failed_count"],
        }

    def _test_api_once_commit_per_page(self, api: dict[str, Any], api_client: Any, token: Any) -> dict[str, Any]:
        """用短事务验证单个宽表分页接口。

        销售表现这类接口单页字段很宽、页间还要限流。如果把 HTTP 请求、sleep
        和所有 raw 写入放在同一个事务里，远程 PolarDB 连接更容易在长时间空闲
        或大批量写入时失效。该路径只由 YAML 显式开启，避免改变普通接口行为。
        """
        if self.engine is None:
            raise ValueError("test api requires database engine")

        batch_no = self._new_batch_no()
        started_at = datetime.now()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO sync_batch (
                      sync_batch_no, status, started_at, total_api_count
                    ) VALUES (
                      :sync_batch_no, 'running', :started_at, 1
                    )
                    """
                ),
                {"sync_batch_no": batch_no, "started_at": started_at},
            )

        result = self._sync_api_with_page_transactions(api, batch_no, api_client, token)
        status = "success" if result["failed_count"] == 0 else "failed"
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE sync_batch
                    SET status = :status,
                        finished_at = :finished_at,
                        success_api_count = :success_api_count,
                        failed_api_count = :failed_api_count,
                        message = :message
                    WHERE sync_batch_no = :sync_batch_no
                    """
                ),
                {
                    "status": status,
                    "finished_at": datetime.now(),
                    "success_api_count": 1 if result["failed_count"] == 0 else 0,
                    "failed_api_count": result["failed_count"],
                    "message": "test api finished",
                    "sync_batch_no": batch_no,
                },
            )

        return {
            "batch_no": batch_no,
            "item_count": result["item_count"],
            "request_count": result["request_count"],
            "failed_count": result["failed_count"],
        }

    def sync_enabled_apis(self, api_client: Any, token: Any) -> dict[str, Any]:
        """同步所有启用的真实 API。

        一个批次内顺序执行多个接口；单个接口失败会记录失败日志并继续执行
        后续接口，最后根据成功/失败数量汇总批次状态。
        """
        if self.engine is None:
            raise ValueError("sync enabled requires database engine")

        enabled_apis = self._enabled_apis()
        # 一个 sync_batch 表示一次调度运行；批次头先提交，避免长任务运行中外部完全看不到 batch。
        batch_no = self._new_batch_no()
        started_at = datetime.now()
        total_item_count = 0
        total_request_count = 0
        success_api_count = 0
        failed_api_count = 0

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO sync_batch (
                      sync_batch_no, status, started_at, total_api_count
                    ) VALUES (
                      :sync_batch_no, 'running', :started_at, :total_api_count
                    )
                    """
                ),
                {
                    "sync_batch_no": batch_no,
                    "started_at": started_at,
                    "total_api_count": len(enabled_apis),
                },
            )

        # 普通 API 仍按接口提交；显式 commit_per_page 的宽表接口由其内部按页开启短事务。
        for api in enabled_apis:
            if api.get("commit_per_page"):
                result = self._sync_api_with_page_transactions(api, batch_no, api_client, token)
            else:
                result = self._sync_api_with_transaction(api, batch_no, api_client, token)
            total_item_count += result["item_count"]
            total_request_count += result["request_count"]
            if result["failed_count"]:
                failed_api_count += 1
            else:
                success_api_count += 1

        if failed_api_count == 0:
            status = "success"
        elif success_api_count > 0:
            status = "partial_failed"
        else:
            status = "failed"

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE sync_batch
                    SET status = :status,
                        finished_at = :finished_at,
                        success_api_count = :success_api_count,
                        failed_api_count = :failed_api_count,
                        message = :message
                    WHERE sync_batch_no = :sync_batch_no
                    """
                ),
                {
                    "status": status,
                    "finished_at": datetime.now(),
                    "success_api_count": success_api_count,
                    "failed_api_count": failed_api_count,
                    "message": "sync enabled finished",
                    "sync_batch_no": batch_no,
                },
            )

        return {
            "batch_no": batch_no,
            "api_count": len(enabled_apis),
            "item_count": total_item_count,
            "request_count": total_request_count,
            "failed_count": failed_api_count,
        }

    def _sync_api_with_transaction(
        self,
        api: dict[str, Any],
        batch_no: str,
        api_client: Any,
        token: Any,
    ) -> dict[str, int]:
        """在事务外处理失效连接，确保失败日志使用新事务。"""
        if self.engine is None:
            raise ValueError("sync api requires database engine")

        try:
            with self.engine.begin() as connection:
                return self._sync_api_in_batch(
                    connection,
                    api,
                    batch_no,
                    api_client,
                    token,
                )
        except InvalidatedApiTransactionError as error:
            with self.engine.begin() as connection:
                self._insert_api_log(
                    connection,
                    batch_no,
                    error.api_code,
                    "failed",
                    error.request_count,
                    0,
                    1,
                    error.api_started_at,
                    str(error.original_error),
                )
            return {"item_count": 0, "request_count": error.request_count, "failed_count": 1}


    def _record_api_failure_in_transaction(
        self,
        connection: Any,
        batch_no: str,
        api_code: str,
        error: Exception,
        request_count: int,
        item_count: int,
        api_started_at: datetime,
    ) -> int:
        """在有效事务中写失败上下文，失效时交给外层新事务收尾。"""
        if isinstance(error, DBAPIError) and error.connection_invalidated:
            raise InvalidatedApiTransactionError(
                error,
                api_code,
                request_count,
                api_started_at,
            ) from error

        if isinstance(error, ApiRequestError):
            request_count += error.attempt_count

        try:
            if isinstance(error, ApiRequestError):
                self._insert_failed_request(connection, batch_no, api_code, error)
            self._insert_api_log(
                connection,
                batch_no,
                api_code,
                "failed",
                request_count,
                item_count,
                1,
                api_started_at,
                str(error),
            )
        except DBAPIError as log_error:
            if log_error.connection_invalidated:
                raise InvalidatedApiTransactionError(
                    log_error,
                    api_code,
                    request_count,
                    api_started_at,
                ) from log_error
            raise
        return request_count


    def _sync_api_in_batch(
        self,
        connection: Any,
        api: dict[str, Any],
        batch_no: str,
        api_client: Any,
        token: Any,
    ) -> dict[str, int]:
        """在已有批次内同步单个 API。

        这里是单接口执行的主流程：分页请求 -> 提取列表 -> 写 raw_api_data ->
        更新 checkpoint -> 写 sync_api_log。异常会被吞进日志表，调用方通过
        failed_count 判断接口是否成功。
        """
        api_code = api["api_code"]
        item_count = 0
        request_count = 0
        failed_count = 0
        last_page = 0
        total_count: int | None = None
        api_started_at = datetime.now()

        if api.get("param_source"):
            return self._sync_api_from_param_source_in_batch(connection, api, batch_no, api_client, token)

        try:
            date_window_caught_up = self._date_window_caught_up(api, connection)
            for page_no, payload, attempt_count in self._paged_payloads(api, api_client, token, connection):
                # request_count 统计真实 HTTP 尝试次数，包含失败后的重试次数。
                request_count += attempt_count
                last_page = page_no
                total_count = self._response_total(payload, api)
                self._ensure_pagination_capacity(api, total_count)
                items = self._response_items(payload, api)
                self._insert_raw_items(connection, api, items, batch_no)
                item_count += len(items)
                self._sleep_between_pages(api, page_no, total_count)

            self._ensure_pagination_not_truncated(api, item_count, total_count)
            if date_window_caught_up:
                checkpoint_extra = self._date_window_caught_up_checkpoint_extra(api, connection)
            else:
                checkpoint_extra = self._date_window_checkpoint_extra(api, self._request_params(api, connection))
            self._update_checkpoint(
                connection,
                api_code,
                batch_no,
                item_count,
                request_count,
                last_page,
                total_count,
                extra=checkpoint_extra,
            )
            self._insert_api_log(connection, batch_no, api_code, "success", request_count, item_count, 0, api_started_at)
        except Exception as error:
            failed_count = 1
            request_count = self._record_api_failure_in_transaction(
                connection,
                batch_no,
                api_code,
                error,
                request_count,
                item_count,
                api_started_at,
            )

        return {"item_count": item_count, "request_count": request_count, "failed_count": failed_count}

    def _sync_api_with_page_transactions(
        self,
        api: dict[str, Any],
        batch_no: str,
        api_client: Any,
        token: Any,
    ) -> dict[str, int]:
        """按页短事务同步单个分页接口。

        该方法只用于显式配置的宽表接口。HTTP 请求不包在数据库事务里；每页
        raw 写入单独提交，最后再写 checkpoint 和接口日志。
        """
        if self.engine is None:
            raise ValueError("page transaction sync requires database engine")
        if api.get("param_source"):
            raise ValueError("commit_per_page does not support param_source APIs")

        api_code = api["api_code"]
        item_count = 0
        request_count = 0
        failed_count = 0
        last_page = 0
        total_count: int | None = None
        api_started_at = datetime.now()

        try:
            date_window_caught_up, base_params = self._short_transaction_base_params(api)
            if not date_window_caught_up:
                for page_no, payload, attempt_count in self._paged_payloads_from_params(
                    api,
                    api_client,
                    token,
                    base_params,
                ):
                    request_count += attempt_count
                    last_page = page_no
                    total_count = self._response_total(payload, api)
                    self._ensure_pagination_capacity(api, total_count)
                    items = self._response_items(payload, api)
                    self._insert_raw_items_in_page_transaction(
                        api,
                        items,
                        batch_no,
                        data_date_override=self._data_date_from_params(api, base_params),
                    )
                    item_count += len(items)
                    self._sleep_between_pages(api, page_no, total_count)

            self._ensure_pagination_not_truncated(api, item_count, total_count)
            if date_window_caught_up:
                checkpoint_extra = self._date_window_caught_up_checkpoint_extra(api, None)
            else:
                checkpoint_extra = self._date_window_checkpoint_extra(api, base_params)
            with self.engine.begin() as connection:
                self._update_checkpoint(
                    connection,
                    api_code,
                    batch_no,
                    item_count,
                    request_count,
                    last_page,
                    total_count,
                    extra=checkpoint_extra,
                )
                self._insert_api_log(connection, batch_no, api_code, "success", request_count, item_count, 0, api_started_at)
        except Exception as error:
            failed_count = 1
            if isinstance(error, ApiRequestError):
                request_count += error.attempt_count
            with self.engine.begin() as connection:
                if isinstance(error, ApiRequestError):
                    self._insert_failed_request(connection, batch_no, api_code, error)
                self._insert_api_log(
                    connection,
                    batch_no,
                    api_code,
                    "failed",
                    request_count,
                    item_count,
                    failed_count,
                    api_started_at,
                    str(error),
                )

        return {"item_count": item_count, "request_count": request_count, "failed_count": failed_count}

    def _insert_raw_items_in_page_transaction(
        self,
        api: dict[str, Any],
        items: list[dict[str, Any]],
        batch_no: str,
        data_date_override: Any = None,
    ) -> None:
        """在独立短事务中写入单页 raw 数据，失效连接只重试一次。

        远程数据库可能在连接已取出后、执行写入时瞬时断线，此时 pool_pre_ping
        无法提前发现。raw 写入本身是幂等 upsert，因此连接被 SQLAlchemy 明确认定
        为失效时可以安全地用新连接重试一次；其他数据库错误仍直接抛出。
        """
        if self.engine is None:
            raise ValueError("page transaction sync requires database engine")

        for attempt in range(2):
            try:
                with self.engine.begin() as connection:
                    self._insert_raw_items(
                        connection,
                        api,
                        items,
                        batch_no,
                        data_date_override=data_date_override,
                    )
                return
            except DBAPIError as error:
                if attempt == 1 or not error.connection_invalidated:
                    raise
                logger.warning("raw page write connection invalidated; retrying api=%s", api["api_code"])

    def _short_transaction_base_params(self, api: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """为短事务同步生成本次请求参数。

        日期窗口需要读取 checkpoint，但这个读取应在请求前短暂完成，不能把后续
        HTTP 分页和 sleep 一起包进数据库事务。
        """
        if not (api.get("date_window") or {}).get("enabled"):
            return False, self._request_params(api, None)
        if self.engine is None:
            raise ValueError("page transaction sync requires database engine")

        with self.engine.begin() as connection:
            caught_up = self._date_window_caught_up(api, connection)
            params = self._request_params(api, connection)
        return caught_up, params

    def _data_date_from_params(self, api: dict[str, Any], params: dict[str, Any]) -> Any:
        """从请求参数取 raw 数据日期。

        少数报表接口的行数据不返回日期，只能用本次请求窗口标记数据归属日期。
        """
        field = api.get("data_date_param")
        if not field:
            return None
        return self._get_by_path(params, str(field))

    def _paged_payloads_from_params(
        self,
        api: dict[str, Any],
        api_client: Any,
        token: Any,
        base_params: dict[str, Any],
    ) -> Any:
        """基于已解析参数分页请求，避免每页重新打开 checkpoint 读取事务。"""
        page_config = api.get("page") or {}
        if not page_config.get("enabled", False):
            payload, attempt_count = self._request_with_retry(api, api_client, token, deepcopy(base_params))
            yield 1, payload, attempt_count
            return

        page_no_field = page_config.get("page_no_field", "page")
        page_size_field = page_config.get("page_size_field", "pagesize")
        page_size = int(page_config.get("page_size") or 20)
        max_pages = self._pagination_max_pages(api)
        page_no = int(self._get_by_path(api.get("params") or {}, str(page_no_field)) or 1)
        pages_requested = 0

        while max_pages is None or pages_requested < max_pages:
            params = deepcopy(base_params)
            self._set_by_path(params, str(page_no_field), page_no)
            self._set_by_path(params, str(page_size_field), page_size)

            payload, attempt_count = self._request_with_retry(api, api_client, token, params)
            pages_requested += 1
            yield page_no, payload, attempt_count

            total = self._response_total(payload, api)
            if total is None:
                break
            if page_no * page_size >= total:
                break
            page_no += 1

    def _sync_api_from_param_source_in_batch(
        self,
        connection: Any,
        api: dict[str, Any],
        batch_no: str,
        api_client: Any,
        token: Any,
    ) -> dict[str, int]:
        """同步依赖上游参数的单对象接口。

        当前只实现最小闭环：从已同步的 `raw_api_data.source_primary_key`
        取少量参数，逐个请求详情接口，再沿用原始 JSON 入库、日志和 checkpoint。
        """
        api_code = api["api_code"]
        param_sets: list[dict[str, Any]] = []
        item_count = 0
        request_count = 0
        failed_count = 0
        total_count = 0
        api_started_at = datetime.now()

        try:
            if self._date_window_caught_up(api, connection):
                checkpoint_extra = self._date_window_caught_up_checkpoint_extra(api, connection)
                self._update_checkpoint(
                    connection,
                    api_code,
                    batch_no,
                    item_count,
                    request_count,
                    0,
                    total_count,
                    extra=checkpoint_extra,
                )
                self._insert_api_log(
                    connection,
                    batch_no,
                    api_code,
                    "success",
                    request_count,
                    item_count,
                    0,
                    api_started_at,
                )
                return {"item_count": item_count, "request_count": request_count, "failed_count": failed_count}

            param_source = api.get("param_source") or {}
            param_limit = int(param_source.get("limit") or 10)
            param_offset = self._param_source_offset(connection, api)
            param_sets = self._source_param_sets(connection, api, offset=param_offset)
            total_count = len(param_sets)
            for index, source_params in enumerate(param_sets, start=1):
                params = self._request_params(api, connection)
                params.update(source_params)
                payload, attempt_count = self._request_with_retry(api, api_client, token, params)
                request_count += attempt_count
                items = self._response_items(payload, api)
                self._insert_raw_items(
                    connection,
                    api,
                    items,
                    batch_no,
                    source_primary_key=self._source_primary_key_from_params(api, params),
                )
                item_count += len(items)
                self._sleep_between_param_requests(api, index, total_count)

            checkpoint_extra = {
                "param_offset": param_offset,
                "param_limit": param_limit,
                "next_param_offset": param_offset + total_count,
            }
            date_window_extra = self._date_window_checkpoint_extra(api, self._request_params(api, connection))
            if date_window_extra:
                checkpoint_extra.update(date_window_extra)

            self._update_checkpoint(
                connection,
                api_code,
                batch_no,
                item_count,
                request_count,
                total_count,
                total_count,
                extra=checkpoint_extra,
            )
            self._insert_api_log(connection, batch_no, api_code, "success", request_count, item_count, 0, api_started_at)
        except Exception as error:
            failed_count = 1
            request_count = self._record_api_failure_in_transaction(
                connection,
                batch_no,
                api_code,
                error,
                request_count,
                item_count,
                api_started_at,
            )

        return {"item_count": item_count, "request_count": request_count, "failed_count": failed_count}

    def _enabled_apis(self) -> list[dict[str, Any]]:
        """返回 YAML 中启用的接口配置。"""
        return [api for api in self.api_configs if api.get("enabled") is True]

    def _api_by_code(self, api_code: str) -> dict[str, Any]:
        """按 api_code 查找单个接口配置。"""
        for api in self.api_configs:
            if api.get("api_code") == api_code:
                return api
        raise ValueError(f"API config not found: {api_code}")

    def _insert_raw_item(
        self,
        connection: Any,
        api: dict[str, Any],
        item: dict[str, Any],
        batch_no: str,
    ) -> None:
        """兼容单条写入入口，内部复用批量写入。"""
        self._insert_raw_items(connection, api, [item], batch_no)

    def _insert_raw_items(
        self,
        connection: Any,
        api: dict[str, Any],
        items: list[dict[str, Any]],
        batch_no: str,
        source_primary_key: str | None = None,
        data_date_override: Any = None,
    ) -> None:
        """把接口原始数据批量写入 raw_api_data。

        幂等策略分两层：如果配置了业务主键，就用 `api_code + source_primary_key`
        覆盖更新；无稳定主键时，`api_code + data_hash` 可以避免同一份 JSON
        重复插入。raw_json 始终保存完整原始数据。
        """
        if not items:
            return

        api_code = api["api_code"]
        primary_key_field = (api.get("primary_key") or {}).get("field")
        rows = []
        for item in items:
            item_primary_key = self._normalize_source_primary_key(source_primary_key)
            if item_primary_key is None and primary_key_field:
                item_primary_key = self._normalize_source_primary_key(item.get(primary_key_field))
            rows.append(
                {
                    "api_code": api_code,
                    "source_primary_key": item_primary_key,
                    "data_hash": self._data_hash(item),
                    "raw_json": json.dumps(item, ensure_ascii=False, sort_keys=True, default=str),
                    "data_date": self._coerce_data_date(data_date_override) or self._data_date(api, item),
                    "sync_batch_no": batch_no,
                }
            )

        statement = text(
            """
            INSERT INTO raw_api_data (
              api_code, source_primary_key, data_hash, raw_json,
              data_date, sync_batch_no
            ) VALUES (
              :api_code, :source_primary_key, :data_hash, :raw_json,
              :data_date, :sync_batch_no
            )
            ON DUPLICATE KEY UPDATE
              data_hash = VALUES(data_hash),
              raw_json = VALUES(raw_json),
              data_date = VALUES(data_date),
              sync_batch_no = VALUES(sync_batch_no)
            """
        )
        write_batch_size = int(api.get("write_batch_size") or len(rows))
        write_batch_size = max(write_batch_size, 1)
        for start in range(0, len(rows), write_batch_size):
            # 销售表现这类宽表 raw_json 很大，分块写入可以避免单次 executemany 过大导致远程连接中断。
            connection.execute(statement, rows[start : start + write_batch_size])

    def _source_primary_key_from_params(self, api: dict[str, Any], params: dict[str, Any]) -> str | None:
        """从请求参数提取 raw 主键。

        参数型详情接口的稳定业务键有时只存在于请求参数中，例如采购订单详情的
        `poCode`。这里仅把该值写入 `source_primary_key`，不写回 raw_json，保证
        `raw_json` 仍是接口返回的原始数据。
        """
        param_field = (api.get("primary_key") or {}).get("param_field")
        if not param_field:
            return None
        value = self._get_by_path(params, str(param_field))
        return self._normalize_source_primary_key(value)

    def _normalize_source_primary_key(self, value: Any) -> str | None:
        """把缺失主键规范为 SQL NULL，同时保留数值零。"""
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        if value is None or str(value) == "":
            return None
        return str(value)

    def _insert_api_log(
        self,
        connection: Any,
        batch_no: str,
        api_code: str,
        status: str,
        request_count: int,
        success_count: int,
        failed_count: int,
        started_at: datetime,
        error_message: str | None = None,
    ) -> None:
        """写入单个 API 在本批次内的执行摘要。"""
        if error_message is not None and self._has_sensitive_response(api_code):
            error_message = SENSITIVE_RESPONSE_ERROR_MESSAGE
        connection.execute(
            text(
                """
                INSERT INTO sync_api_log (
                  sync_batch_no, api_code, status, request_count,
                  success_count, failed_count, started_at, finished_at, error_message
                ) VALUES (
                  :sync_batch_no, :api_code, :status, :request_count,
                  :success_count, :failed_count, :started_at, :finished_at, :error_message
                )
                """
            ),
            {
                "sync_batch_no": batch_no,
                "api_code": api_code,
                "status": status,
                "request_count": request_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "started_at": started_at,
                "finished_at": datetime.now(),
                "error_message": error_message,
            },
        )

    def _mock_items(self, api: dict[str, Any]) -> list[dict[str, Any]]:
        """根据 API 配置生成一条 mock 数据。

        mock 数据会尽量使用配置里的 primary_key 和 date_field，方便验证真实配置
        对入库字段的影响。
        """
        api_code = api["api_code"]
        primary_key_field = (api.get("primary_key") or {}).get("field") or "mockId"
        date_field = api.get("date_field") or "updatedAt"
        return [
            {
                primary_key_field: f"mock-{api_code}-001",
                date_field: date.today().isoformat(),
                "apiCode": api_code,
                "mock": True,
            }
        ]

    def _data_hash(self, item: dict[str, Any]) -> str:
        """计算原始 JSON 的稳定哈希。

        `sort_keys=True` 保证同一对象字段顺序不同也得到相同哈希；`default=str`
        让 date/datetime 等对象能安全序列化。
        """
        raw_json = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    def _response_items(self, payload: dict[str, Any], api: dict[str, Any]) -> list[dict[str, Any]]:
        """从接口响应中提取列表数据。

        列表路径由 YAML 的 `page.list_field` 控制，例如 `data.rows`。详情接口
        可以用 `response.item_field` 把单个对象包装成一条 raw 记录；少数基础
        配置接口只返回字符串，用 `response.scalar_field` 包装成单条对象入库。
        """
        response_config = api.get("response") or {}
        scalar_field = response_config.get("scalar_field")
        if scalar_field:
            value = self._get_by_path(payload, scalar_field)
            if value is None:
                return []
            target_field = response_config.get("scalar_target_field") or str(scalar_field).split(".")[-1]
            item = {target_field: value}
            return [item] if self._has_required_primary_key(api, item) else []

        item_field = response_config.get("item_field")
        if item_field:
            item = self._get_by_path(payload, item_field)
            if item is None:
                return []
            if isinstance(item, dict):
                return [item] if self._has_required_primary_key(api, item) else []
            if isinstance(item, list):
                return [row for row in item if isinstance(row, dict) and self._has_required_primary_key(api, row)]
            raise ValueError(f"response item field is not an object or list: {item_field}")

        list_field = (api.get("page") or {}).get("list_field", "data.rows")
        items = self._get_by_path(payload, list_field)
        if items is None:
            return []
        if not isinstance(items, list):
            raise ValueError(f"response list field is not a list: {list_field}")
        return [item for item in items if isinstance(item, dict) and self._has_required_primary_key(api, item)]

    def _has_required_primary_key(self, api: dict[str, Any], item: dict[str, Any]) -> bool:
        """按配置决定是否保留响应记录。

        有些详情接口查不到数据时会返回一个字段齐全但主键为空的对象。只有当
        YAML 明确声明主键必填时才过滤，避免影响历史上允许空主键的接口。
        """
        primary_key = api.get("primary_key") or {}
        if not primary_key.get("required"):
            return True

        primary_key_field = primary_key.get("field")
        if not primary_key_field:
            return True

        value = item.get(primary_key_field)
        return value is not None and str(value) != ""

    def _paged_payloads(
        self,
        api: dict[str, Any],
        api_client: Any,
        token: Any,
        connection: Any | None = None,
    ) -> Any:
        """按分页配置逐页产出接口响应。

        非分页接口只请求一次。分页接口会在每次请求前覆盖页码和页大小，并用
        total 判断是否已经到最后一页；配置 max_pages 时继续把它作为保护阈值。
        """
        if self._date_window_caught_up(api, connection):
            return

        page_config = api.get("page") or {}
        if not page_config.get("enabled", False):
            params = self._request_params(api, connection)
            payload, attempt_count = self._request_with_retry(api, api_client, token, params)
            yield 1, payload, attempt_count
            return

        page_no_field = page_config.get("page_no_field", "page")
        page_size_field = page_config.get("page_size_field", "pagesize")
        page_size = int(page_config.get("page_size") or 20)
        # 未配置 max_pages 时遵循实时 total；已有配置继续作为测试阶段保护。
        max_pages = self._pagination_max_pages(api)
        page_no = int(self._get_by_path(api.get("params") or {}, str(page_no_field)) or 1)
        pages_requested = 0

        while max_pages is None or pages_requested < max_pages:
            params = self._request_params(api, connection)
            self._set_by_path(params, str(page_no_field), page_no)
            self._set_by_path(params, str(page_size_field), page_size)

            payload, attempt_count = self._request_with_retry(api, api_client, token, params)
            pages_requested += 1
            yield page_no, payload, attempt_count

            total = self._response_total(payload, api)
            if total is None:
                break
            if page_no * page_size >= total:
                break
            page_no += 1

    def _request_params(
        self,
        api: dict[str, Any],
        connection: Any | None = None,
        today: date | None = None,
    ) -> dict[str, Any]:
        """读取并解析 YAML 请求参数。

        日期模板解决滚动窗口这类通用需求；`date_window` 进一步用 checkpoint
        推进历史窗口，避免超大表只能靠全量分页。
        """
        params = self._resolve_param_templates(api.get("params") or {}, today)
        window = self._date_window_params(api, connection, today)
        if window:
            params.update(window)
        return params

    def _resolve_param_templates(self, value: Any, today: date | None = None) -> Any:
        """递归解析请求参数中的日期占位符。"""
        current_date = today or date.today()
        if isinstance(value, dict):
            return {key: self._resolve_param_templates(item, current_date) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve_param_templates(item, current_date) for item in value]
        if not isinstance(value, str):
            return value

        match = DATE_PARAM_TEMPLATE_PATTERN.match(value)
        if not match:
            return value

        token = match.group(1)
        if token == "today":
            return current_date.isoformat()
        if token == "yesterday":
            return (current_date - timedelta(days=1)).isoformat()
        if token.startswith("days_ago:"):
            return (current_date - timedelta(days=int(match.group(2)))).isoformat()
        return value

    def _date_window_params(
        self,
        api: dict[str, Any],
        connection: Any | None = None,
        today: date | None = None,
    ) -> dict[str, str] | None:
        """根据 date_window 配置生成单次请求的日期窗口。"""
        window_config = api.get("date_window") or {}
        if not window_config.get("enabled"):
            return None

        start_field = str(window_config.get("start_field") or "")
        end_field = str(window_config.get("end_field") or "")
        default_start = str(window_config.get("default_start") or "")
        window_days = int(window_config.get("days") or 1)
        if not start_field or not end_field or not default_start:
            raise ValueError(f"invalid date_window config: {api.get('api_code')}")

        start_date = self._date_window_start(api, connection) or date.fromisoformat(default_start)
        end_date = start_date + timedelta(days=max(window_days, 1) - 1)
        current_date = self._date_window_sync_until(window_config, today)
        if start_date > current_date:
            return None
        if end_date > current_date:
            end_date = current_date

        window_params: dict[str, Any] = {}
        self._set_by_path(window_params, start_field, start_date.isoformat())
        self._set_by_path(window_params, end_field, end_date.isoformat())
        return window_params

    def _date_window_start(self, api: dict[str, Any], connection: Any | None) -> date | None:
        """从 checkpoint 中读取下一次日期窗口起点。"""
        if connection is None:
            return None

        result = connection.execute(
            text(
                """
                SELECT checkpoint_value
                FROM sync_checkpoint
                WHERE api_code = :api_code
                """
            ),
            {"api_code": api["api_code"]},
        )
        row = result.mappings().first()
        if not row or not row.get("checkpoint_value"):
            return None

        try:
            checkpoint = json.loads(str(row["checkpoint_value"]))
        except json.JSONDecodeError:
            return None

        next_window_start = checkpoint.get("next_window_start")
        if not next_window_start:
            return None
        return date.fromisoformat(str(next_window_start))

    def _date_window_caught_up(
        self,
        api: dict[str, Any],
        connection: Any | None = None,
        today: date | None = None,
    ) -> bool:
        """判断日期窗口是否已经推进到今天之后。"""
        window_config = api.get("date_window") or {}
        if not window_config.get("enabled"):
            return False

        default_start = str(window_config.get("default_start") or "")
        if not default_start:
            return False

        start_date = self._date_window_start(api, connection) or date.fromisoformat(default_start)
        current_date = self._date_window_sync_until(window_config, today)
        return start_date > current_date

    def _date_window_sync_until(self, window_config: dict[str, Any], today: date | None = None) -> date:
        """计算日期窗口本次允许同步到哪一天。

        默认允许同步到今天；严格报表接口可配置 `lag_days`，只同步已完整
        结束的历史日，避免当天数据尚未稳定时提前推进 checkpoint。
        """
        lag_days = max(int(window_config.get("lag_days") or 0), 0)
        return (today or date.today()) - timedelta(days=lag_days)

    def _date_window_caught_up_checkpoint_extra(
        self,
        api: dict[str, Any],
        connection: Any | None = None,
    ) -> dict[str, Any] | None:
        """日期窗口追平时保留下一窗口，避免空跑后丢失推进位置。"""
        window_config = api.get("date_window") or {}
        if not window_config.get("enabled"):
            return None

        default_start = str(window_config.get("default_start") or "")
        if not default_start:
            return None

        start_date = self._date_window_start(api, connection) or date.fromisoformat(default_start)
        return {
            "next_window_start": start_date.isoformat(),
            "window_days": int(window_config.get("days") or 1),
            "skipped_reason": "date_window_caught_up",
        }

    def _date_window_checkpoint_extra(self, api: dict[str, Any], params: dict[str, Any]) -> dict[str, Any] | None:
        """生成写入 checkpoint 的日期窗口推进信息。"""
        window_config = api.get("date_window") or {}
        if not window_config.get("enabled"):
            return None

        start_field = str(window_config.get("start_field") or "")
        end_field = str(window_config.get("end_field") or "")
        if not start_field or not end_field:
            return None

        window_start_value = self._get_by_path(params, start_field)
        window_end_value = self._get_by_path(params, end_field)
        if not window_start_value or not window_end_value:
            return None

        window_start = date.fromisoformat(str(window_start_value))
        window_end = date.fromisoformat(str(window_end_value))
        return {
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "next_window_start": (window_end + timedelta(days=1)).isoformat(),
            "window_days": int(window_config.get("days") or 1),
        }

    def _ensure_pagination_not_truncated(
        self,
        api: dict[str, Any],
        item_count: int,
        total_count: int | None,
    ) -> None:
        """阻止分页接口在数据未拉满时记录成功 checkpoint。

        只对启用分页且配置了有效 total 的接口校验；非分页接口和官方明确
        没有有效 total 的接口保持原行为。
        """
        page_config = api.get("page") or {}
        if not page_config.get("enabled") or total_count is None:
            return
        if item_count >= total_count:
            return
        raise ValueError(
            "pagination truncated: "
            f"api_code={api.get('api_code')} item_count={item_count} "
            f"total_count={total_count} page_size={page_config.get('page_size')} "
            f"max_pages={page_config.get('max_pages')}"
        )

    @staticmethod
    def _pagination_max_pages(api: dict[str, Any]) -> int | None:
        """读取可选分页保护值；未配置时由实时 total 决定页数。"""
        value = (api.get("page") or {}).get("max_pages")
        if value is None:
            return None
        return max(int(value), 1)

    def _required_page_count(self, api: dict[str, Any], total_count: int | None) -> int | None:
        """根据响应总数计算完成本次分页至少需要的请求页数。"""
        page_config = api.get("page") or {}
        if not page_config.get("enabled") or total_count is None:
            return None
        page_size = int(page_config.get("page_size") or 20)
        return max(1, (total_count + page_size - 1) // page_size)

    def _ensure_pagination_capacity(self, api: dict[str, Any], total_count: int | None) -> None:
        """在写入首页 raw 前确认固定上限足够，或实时 total 有效。"""
        page_config = api.get("page") or {}
        if not page_config.get("enabled"):
            return

        max_pages = self._pagination_max_pages(api)
        if max_pages is None:
            if total_count is None or total_count < 0:
                raise ValueError(
                    "total-driven pagination requires valid total: "
                    f"api_code={api.get('api_code')} total_count={total_count}"
                )
            return

        required_pages = self._required_page_count(api, total_count)
        if required_pages is None or max_pages >= required_pages:
            return
        raise ValueError(
            "pagination capacity insufficient: "
            f"api_code={api.get('api_code')} total_count={total_count} "
            f"page_size={page_config.get('page_size')} max_pages={max_pages} "
            f"required_pages={required_pages}"
        )

    def _source_param_sets(
        self,
        connection: Any,
        api: dict[str, Any],
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """从已入库的上游 raw 数据生成请求参数。

        当前支持三种最小来源：`source_primary_key` 单字段、从 raw_json 点路径
        提取参数，以及从 raw_json 的单层数组展开参数。raw_json 点路径来源可附加
        固定等值过滤，用于只取某类上游单据。
        """
        param_source = api.get("param_source") or {}
        source_api_code = param_source.get("source_api_code")
        fields = param_source.get("fields") or []
        limit = int(param_source.get("limit") or 10)
        offset = self._param_source_offset(connection, api) if offset is None else offset
        refresh_before = None
        if (
            param_source.get("exclude_existing_target")
            and param_source.get("refresh_after_days") is not None
        ):
            refresh_before = datetime.now() - timedelta(
                days=max(int(param_source["refresh_after_days"]), 0)
            )

        if fields:
            return self._source_param_sets_from_raw_json_fields(
                connection,
                api["api_code"],
                source_api_code,
                fields,
                param_source.get("filters") or [],
                limit,
                offset,
                bool(param_source.get("exclude_existing_target")),
                refresh_before,
            )

        source_field = param_source.get("source_field")
        target_field = param_source.get("target_field")

        if source_field != "source_primary_key":
            raise ValueError(f"unsupported param source field: {source_field}")
        if not source_api_code or not target_field:
            raise ValueError(f"invalid param_source config: {api.get('api_code')}")

        if param_source.get("exclude_existing_target"):
            target_condition = "target_data.id IS NULL"
            order_clause = "source_data.source_primary_key"
            query_params: dict[str, Any] = {
                "source_api_code": source_api_code,
                "target_api_code": api["api_code"],
                "limit": limit,
                "offset": offset,
            }
            if refresh_before is not None:
                target_condition = (
                    "(target_data.id IS NULL OR target_data.updated_at < :refresh_before)"
                )
                query_params["refresh_before"] = refresh_before
                order_clause = "target_data.updated_at, source_data.source_primary_key"
            result = connection.execute(
                text(
                    f"""
                    SELECT source_data.source_primary_key AS source_value
                    FROM raw_api_data source_data
                    LEFT JOIN raw_api_data target_data
                      ON target_data.api_code = :target_api_code
                     AND target_data.source_primary_key = source_data.source_primary_key
                    WHERE source_data.api_code = :source_api_code
                      AND source_data.source_primary_key IS NOT NULL
                      AND source_data.source_primary_key <> ''
                      AND {target_condition}
                    ORDER BY {order_clause}
                    LIMIT :limit
                    OFFSET :offset
                    """
                ),
                query_params,
            )
            return [{target_field: str(row["source_value"])} for row in result.mappings().all()]

        result = connection.execute(
            text(
                """
                SELECT source_primary_key AS source_value
                FROM raw_api_data
                WHERE api_code = :source_api_code
                  AND source_primary_key IS NOT NULL
                  AND source_primary_key <> ''
                ORDER BY source_primary_key
                LIMIT :limit
                OFFSET :offset
                """
            ),
            {"source_api_code": source_api_code, "limit": limit, "offset": offset},
        )
        return [{target_field: str(row["source_value"])} for row in result.mappings().all()]

    def _param_source_offset(self, connection: Any, api: dict[str, Any]) -> int:
        """计算依赖参数来源的读取窗口起点。

        `offset` 仍是人工配置的基准值；只有显式开启 `auto_advance` 时才读取
        checkpoint，避免影响仍在手动小样本验证的依赖接口。
        """
        param_source = api.get("param_source") or {}
        base_offset = int(param_source.get("offset") or 0)
        if param_source.get("exclude_existing_target"):
            # 目标表缺失扫描自身就是进度边界，不能再叠加历史 OFFSET。
            return base_offset
        if not param_source.get("auto_advance"):
            return base_offset

        result = connection.execute(
            text(
                """
                SELECT checkpoint_value
                FROM sync_checkpoint
                WHERE api_code = :api_code
                """
            ),
            {"api_code": api["api_code"]},
        )
        row = result.mappings().first()
        if not row or not row.get("checkpoint_value"):
            return base_offset

        try:
            checkpoint = json.loads(str(row["checkpoint_value"]))
        except json.JSONDecodeError:
            return base_offset

        if checkpoint.get("next_param_offset") is not None:
            return int(checkpoint["next_param_offset"])
        if checkpoint.get("param_offset") is not None and checkpoint.get("param_limit") is not None:
            return int(checkpoint["param_offset"]) + int(checkpoint["param_limit"])
        if checkpoint.get("total_count") is not None:
            return base_offset + int(checkpoint["total_count"])
        return base_offset

    def _source_param_sets_from_raw_json_fields(
        self,
        connection: Any,
        target_api_code: str,
        source_api_code: str | None,
        fields: list[dict[str, Any]],
        filters: list[dict[str, Any]],
        limit: int,
        offset: int,
        exclude_existing_target: bool = False,
        refresh_before: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """从上游 raw_json 顶层字段生成请求参数。"""
        if not source_api_code:
            raise ValueError("invalid param_source config: missing source_api_code")
        if any("[]" in str(field.get("source_field") or "") for field in fields):
            return self._source_param_sets_from_raw_json_array_field(
                connection,
                source_api_code,
                fields,
                filters,
                limit,
                offset,
            )

        select_parts = []
        select_expressions = []
        where_parts = []
        query_params: dict[str, Any] = {"source_api_code": source_api_code, "limit": limit, "offset": offset}
        target_fields = []
        wrap_in_list_fields = []
        raw_json_column = "source_data.raw_json" if exclude_existing_target else "raw_json"
        from_clause = "raw_api_data source_data" if exclude_existing_target else "raw_api_data"
        api_code_column = "source_data.api_code" if exclude_existing_target else "api_code"
        for index, field in enumerate(fields):
            source_field = str(field.get("source_field") or "")
            target_field = str(field.get("target_field") or "")
            if not source_field.startswith("raw_json.") or not target_field:
                raise ValueError(f"invalid raw_json param field: {source_field}")

            raw_json_path = source_field.removeprefix("raw_json.")
            if not RAW_JSON_FIELD_PATTERN.match(raw_json_path):
                raise ValueError(f"invalid raw_json param field: {source_field}")

            expression = f"JSON_UNQUOTE(JSON_EXTRACT({raw_json_column}, '$.{raw_json_path}'))"
            alias = f"source_{index}"
            select_parts.append(f"{expression} AS {alias}")
            select_expressions.append(expression)
            where_parts.append(f"{expression} IS NOT NULL AND {expression} <> ''")
            target_fields.append(target_field)
            wrap_in_list_fields.append(bool(field.get("wrap_in_list")))

        for index, filter_config in enumerate(filters):
            source_field = str(filter_config.get("source_field") or "")
            if not source_field.startswith("raw_json."):
                raise ValueError(f"invalid raw_json param filter: {source_field}")

            raw_json_path = source_field.removeprefix("raw_json.")
            if not RAW_JSON_FIELD_PATTERN.match(raw_json_path):
                raise ValueError(f"invalid raw_json param filter: {source_field}")
            if "equals" not in filter_config:
                raise ValueError(f"invalid raw_json param filter: {source_field}")

            expression = f"JSON_UNQUOTE(JSON_EXTRACT({raw_json_column}, '$.{raw_json_path}'))"
            param_name = f"filter_{index}"
            where_parts.append(f"{expression} = :{param_name}")
            query_params[param_name] = str(filter_config["equals"])

        join_clause = ""
        if exclude_existing_target:
            # 目标表缺失扫描用第一个来源字段作为目标 source_primary_key，对应 transfer_detail 的 code。
            join_clause = f"""
            LEFT JOIN raw_api_data target_data
              ON target_data.api_code = :target_api_code
             AND target_data.source_primary_key = {select_expressions[0]}
            """
            if refresh_before is None:
                where_parts.append("target_data.id IS NULL")
            else:
                where_parts.append(
                    "(target_data.id IS NULL OR target_data.updated_at < :refresh_before)"
                )
                query_params["refresh_before"] = refresh_before
            query_params["target_api_code"] = target_api_code

        aliases = [f"source_{index}" for index in range(len(fields))]
        order_clause = ", ".join(aliases)
        if refresh_before is not None:
            order_clause = f"MIN(target_data.updated_at), {order_clause}"
        sql = f"""
            SELECT {", ".join(select_parts)}
            FROM {from_clause}
            {join_clause}
            WHERE {api_code_column} = :source_api_code
              AND {" AND ".join(where_parts)}
            GROUP BY {", ".join(aliases)}
            ORDER BY {order_clause}
            LIMIT :limit
            OFFSET :offset
        """
        result = connection.execute(text(sql), query_params)
        rows = []
        for row in result.mappings().all():
            params = {}
            for index, target_field in enumerate(target_fields):
                value = str(row[f"source_{index}"])
                params[target_field] = (
                    [value] if wrap_in_list_fields[index] else value
                )
            rows.append(params)
        return rows

    def _source_param_sets_from_raw_json_array_field(
        self,
        connection: Any,
        source_api_code: str,
        fields: list[dict[str, Any]],
        filters: list[dict[str, Any]],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        """从上游 raw_json 的单层数组展开请求参数。

        目前只支持一个数组字段，例如 `raw_json.marketListVos[].marketId`。
        这是为了覆盖店铺授权信息里的站点列表，同时避免把数组 join、复杂过滤
        和多字段同位绑定一次性做复杂。
        """
        if filters:
            raise ValueError("raw_json array param source does not support filters")
        if len(fields) != 1:
            raise ValueError("raw_json array param source supports exactly one field")

        field = fields[0]
        source_field = str(field.get("source_field") or "")
        target_field = str(field.get("target_field") or "")
        wrap_in_list = bool(field.get("wrap_in_list"))
        if not source_field.startswith("raw_json.") or not target_field:
            raise ValueError(f"invalid raw_json param field: {source_field}")

        raw_json_path = source_field.removeprefix("raw_json.")
        if raw_json_path.count("[]") != 1:
            raise ValueError(f"invalid raw_json array param field: {source_field}")

        array_path, value_path = raw_json_path.split("[]", 1)
        value_path = value_path.removeprefix(".")
        if not RAW_JSON_FIELD_PATTERN.match(array_path) or not value_path or not RAW_JSON_FIELD_PATTERN.match(value_path):
            raise ValueError(f"invalid raw_json array param field: {source_field}")

        result = connection.execute(
            text(
                """
                SELECT raw_json
                FROM raw_api_data
                WHERE api_code = :source_api_code
                  AND raw_json IS NOT NULL
                ORDER BY id
                """
            ),
            {"source_api_code": source_api_code},
        )

        values = set()
        for row in result.mappings().all():
            raw_json = row.get("raw_json")
            if isinstance(raw_json, str):
                try:
                    item = json.loads(raw_json)
                except json.JSONDecodeError:
                    continue
            elif isinstance(raw_json, dict):
                item = raw_json
            else:
                continue

            array_items = self._get_by_path(item, array_path)
            if not isinstance(array_items, list):
                continue
            for array_item in array_items:
                if not isinstance(array_item, dict):
                    continue
                value = self._get_by_path(array_item, value_path)
                if value is not None and str(value) != "":
                    values.add(str(value))

        selected_values = sorted(values)[offset : offset + limit]
        return [
            {target_field: [value] if wrap_in_list else value}
            for value in selected_values
        ]

    def _request_with_retry(
        self,
        api: dict[str, Any],
        api_client: Any,
        token: Any,
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], int]:
        """带重试地执行一次接口请求。

        返回值同时包含响应 payload 和真实尝试次数，后者会进入 sync_api_log；
        如果最终失败，则包装成 ApiRequestError，保留可排查的请求上下文。
        """
        retry_config = api.get("retry") or {}
        retries = int(retry_config.get("retries") or 3)
        delay_seconds = float(retry_config.get("delay_seconds") or 1)
        attempt_count = 0

        def request_once() -> dict[str, Any]:
            nonlocal attempt_count
            attempt_count += 1
            return api_client.request(api, token, params)

        try:
            # retry_call 只负责重试；attempt_count 用来给 sync_api_log 和失败日志做可追踪记录。
            return retry_call(request_once, retries=retries, delay_seconds=delay_seconds), attempt_count
        except Exception as error:
            request_url = api_client.request_url(api) if hasattr(api_client, "request_url") else None
            method = str(api.get("method", "POST")).upper()
            raise ApiRequestError(error, request_url, method, params, attempt_count) from error

    def _response_total(self, payload: dict[str, Any], api: dict[str, Any]) -> int | None:
        """从响应中读取总条数。

        没配置 total_field 时返回 None，分页循环会保守地只请求当前页。
        """
        total_field = (api.get("page") or {}).get("total_field")
        if not total_field:
            return None
        total = self._get_by_path(payload, total_field)
        if total is None:
            return None
        return int(total)

    def _sleep_between_pages(self, api: dict[str, Any], page_no: int, total_count: int | None) -> None:
        """在分页请求之间按配置限流。

        只有确认还有下一页时才 sleep，避免最后一页无意义等待。
        """
        page_config = api.get("page") or {}
        page_size = int(page_config.get("page_size") or 20)
        if total_count is None or page_no * page_size >= total_count:
            return
        sleep_seconds = float((api.get("rate_limit") or {}).get("sleep_seconds") or 0)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    def _sleep_between_param_requests(self, api: dict[str, Any], index: int, total_count: int) -> None:
        """依赖参数接口逐个请求时复用同一套限流配置。"""
        if index >= total_count:
            return
        sleep_seconds = float((api.get("rate_limit") or {}).get("sleep_seconds") or 0)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    def _update_checkpoint(
        self,
        connection: Any,
        api_code: str,
        batch_no: str,
        item_count: int,
        request_count: int,
        last_page: int,
        total_count: int | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """更新单个 API 的同步检查点。

        默认记录分页执行摘要；依赖参数接口可以额外写入参数窗口，后续运行据此
        自动推进下一批 offset。
        """
        # checkpoint_value 暂存分页摘要，后续接入增量接口时再替换为业务时间或游标。
        checkpoint_data = {
            "last_page": last_page,
            "request_count": request_count,
            "item_count": item_count,
            "total_count": total_count,
        }
        if extra:
            checkpoint_data.update(extra)
        checkpoint_value = json.dumps(
            checkpoint_data,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        connection.execute(
            text(
                """
                INSERT INTO sync_checkpoint (
                  api_code, checkpoint_value, checkpoint_time, last_sync_batch_no
                ) VALUES (
                  :api_code, :checkpoint_value, :checkpoint_time, :last_sync_batch_no
                )
                ON DUPLICATE KEY UPDATE
                  checkpoint_value = VALUES(checkpoint_value),
                  checkpoint_time = VALUES(checkpoint_time),
                  last_sync_batch_no = VALUES(last_sync_batch_no)
                """
            ),
            {
                "api_code": api_code,
                "checkpoint_value": checkpoint_value,
                "checkpoint_time": datetime.now(),
                "last_sync_batch_no": batch_no,
            },
        )

    def _insert_failed_request(
        self,
        connection: Any,
        batch_no: str,
        api_code: str,
        error: ApiRequestError,
    ) -> None:
        """写入失败请求明细。

        普通接口保存 URL、方法、业务参数、HTTP 状态和响应体，便于后续重放
        或排查；敏感响应接口不保存业务参数、响应正文和原始错误。accessToken
        始终不会进入该表。
        """
        # request_params 是业务请求体，不包含 accessToken；鉴权头不落库。
        response = getattr(error.original_error, "response", None)
        status_code = getattr(response, "status_code", None)
        response_body = getattr(response, "text", None)
        error_message = str(error.original_error)
        request_params = json.dumps(
            error.request_params, ensure_ascii=False, default=str
        )
        if self._has_sensitive_response(api_code):
            # 人员等敏感响应只允许成功时进入 raw_json，失败链路保留状态但不保存正文。
            request_params = None
            response_body = None
            error_message = SENSITIVE_RESPONSE_ERROR_MESSAGE
        connection.execute(
            text(
                """
                INSERT INTO failed_request_log (
                  sync_batch_no, api_code, request_url, request_method,
                  request_params, response_status_code, response_body,
                  error_message, retry_count
                ) VALUES (
                  :sync_batch_no, :api_code, :request_url, :request_method,
                  :request_params, :response_status_code, :response_body,
                  :error_message, :retry_count
                )
                """
            ),
            {
                "sync_batch_no": batch_no,
                "api_code": api_code,
                "request_url": error.request_url,
                "request_method": error.request_method,
                "request_params": request_params,
                "response_status_code": status_code,
                "response_body": response_body,
                "error_message": error_message,
                "retry_count": error.retry_count,
            },
        )

    def _has_sensitive_response(self, api_code: str) -> bool:
        """判断接口响应是否需要在失败日志中隐藏正文和原始错误。

        测试和内部调用可直接传入未注册的临时 API，此时沿用普通接口行为。
        """
        api = next(
            (item for item in self.api_configs if item.get("api_code") == api_code),
            None,
        )
        return bool(api and api.get("sensitive_response"))

    def _get_by_path(self, data: dict[str, Any], path: str) -> Any:
        """按点分路径读取嵌套字典字段。

        例如 `data.rows` 会依次读取 payload["data"]["rows"]。中途遇到非字典
        或缺失字段时返回 None。
        """
        current: Any = data
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def _set_by_path(self, data: dict[str, Any], path: str, value: Any) -> None:
        """按点分路径写入嵌套字典字段。"""
        current = data
        parts = path.split(".")
        for part in parts[:-1]:
            nested = current.get(part)
            if not isinstance(nested, dict):
                nested = {}
                current[part] = nested
            current = nested
        current[parts[-1]] = value

    def _data_date(self, api: dict[str, Any], item: dict[str, Any]) -> date | None:
        """从单条数据中提取业务日期。

        date_field 由 YAML 配置控制。只取前 10 位是为了兼容常见的
        `YYYY-MM-DD HH:mm:ss` 或 ISO datetime 字符串。
        """
        date_field = api.get("date_field")
        if not date_field or not item.get(date_field):
            return None
        return self._coerce_data_date(item[date_field])

    def _coerce_data_date(self, value: Any) -> date | None:
        """把配置来源的 ISO 日期或 13 位毫秒时间戳转成 date。"""
        if not value:
            return None
        if isinstance(value, date):
            return value
        text_value = str(value)
        if len(text_value) == 13 and text_value.isdigit():
            return datetime.fromtimestamp(
                int(text_value) / 1000,
                tz=ZoneInfo("Asia/Shanghai"),
            ).date()
        return date.fromisoformat(text_value[:10])

    def _new_batch_no(self) -> str:
        """生成本次同步批次号。"""
        return datetime.now().strftime("sync_%Y%m%d_%H%M%S_%f")
