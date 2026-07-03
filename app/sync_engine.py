import logging
import hashlib
import json
import re
import time
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.retry import retry_call


logger = logging.getLogger(__name__)
RAW_JSON_FIELD_PATTERN = re.compile(r"^[A-Za-z0-9_.]+$")


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
                        "enabled": 1 if api.get("enabled", True) else 0,
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

            result = self._sync_api_in_batch(connection, api, batch_no, api_client, token)

            status = "success" if result["failed_count"] == 0 else "failed"
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
        # 一个 sync_batch 表示一次调度运行；多个 enabled API 共用这个批次，逐个写 sync_api_log。
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

            for api in enabled_apis:
                result = self._sync_api_in_batch(connection, api, batch_no, api_client, token)
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
            for page_no, payload, attempt_count in self._paged_payloads(api, api_client, token):
                # request_count 统计真实 HTTP 尝试次数，包含失败后的重试次数。
                request_count += attempt_count
                last_page = page_no
                items = self._response_items(payload, api)
                self._insert_raw_items(connection, api, items, batch_no)
                item_count += len(items)
                total_count = self._response_total(payload, api)
                self._sleep_between_pages(api, page_no, total_count)

            self._update_checkpoint(connection, api_code, batch_no, item_count, request_count, last_page, total_count)
            self._insert_api_log(connection, batch_no, api_code, "success", request_count, item_count, 0, api_started_at)
        except Exception as error:
            failed_count = 1
            if isinstance(error, ApiRequestError):
                request_count += error.attempt_count
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
            param_source = api.get("param_source") or {}
            param_limit = int(param_source.get("limit") or 10)
            param_offset = self._param_source_offset(connection, api)
            param_sets = self._source_param_sets(connection, api, offset=param_offset)
            total_count = len(param_sets)
            for index, source_params in enumerate(param_sets, start=1):
                params = dict(api.get("params") or {})
                params.update(source_params)
                payload, attempt_count = self._request_with_retry(api, api_client, token, params)
                request_count += attempt_count
                items = self._response_items(payload, api)
                self._insert_raw_items(connection, api, items, batch_no)
                item_count += len(items)
                self._sleep_between_param_requests(api, index, total_count)

            self._update_checkpoint(
                connection,
                api_code,
                batch_no,
                item_count,
                request_count,
                total_count,
                total_count,
                extra={
                    "param_offset": param_offset,
                    "param_limit": param_limit,
                    "next_param_offset": param_offset + total_count,
                },
            )
            self._insert_api_log(connection, batch_no, api_code, "success", request_count, item_count, 0, api_started_at)
        except Exception as error:
            failed_count = 1
            if isinstance(error, ApiRequestError):
                request_count += error.attempt_count
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

    def _enabled_apis(self) -> list[dict[str, Any]]:
        """返回 YAML 中启用的接口配置。"""
        return [api for api in self.api_configs if api.get("enabled", True)]

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
            source_primary_key = str(item.get(primary_key_field)) if primary_key_field else None
            rows.append(
                {
                    "api_code": api_code,
                    "source_primary_key": source_primary_key,
                    "data_hash": self._data_hash(item),
                    "raw_json": json.dumps(item, ensure_ascii=False, sort_keys=True, default=str),
                    "data_date": self._data_date(api, item),
                    "sync_batch_no": batch_no,
                }
            )

        # SQLAlchemy 收到参数列表时会走 executemany，避免远程 PolarDB 逐条往返。
        connection.execute(
            text(
                """
                INSERT INTO raw_api_data (
                  api_code, source_primary_key, data_hash, raw_json,
                  data_date, sync_batch_no
                ) VALUES (
                  :api_code, :source_primary_key, :data_hash, :raw_json,
                  :data_date, :sync_batch_no
                )
                ON DUPLICATE KEY UPDATE
                  raw_json = VALUES(raw_json),
                  data_date = VALUES(data_date),
                  sync_batch_no = VALUES(sync_batch_no)
                """
            ),
            rows,
        )

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
        可以用 `response.item_field` 把单个对象包装成一条 raw 记录。
        """
        item_field = (api.get("response") or {}).get("item_field")
        if item_field:
            item = self._get_by_path(payload, item_field)
            if item is None:
                return []
            if isinstance(item, dict):
                return [item]
            if isinstance(item, list):
                return [row for row in item if isinstance(row, dict)]
            raise ValueError(f"response item field is not an object or list: {item_field}")

        list_field = (api.get("page") or {}).get("list_field", "data.rows")
        items = self._get_by_path(payload, list_field)
        if items is None:
            return []
        if not isinstance(items, list):
            raise ValueError(f"response list field is not a list: {list_field}")
        return [item for item in items if isinstance(item, dict)]

    def _paged_payloads(self, api: dict[str, Any], api_client: Any, token: Any) -> Any:
        """按分页配置逐页产出接口响应。

        非分页接口只请求一次。分页接口会在每次请求前覆盖页码和页大小，并用
        total 判断是否已经到最后一页；max_pages 是接入阶段的保护阈值。
        """
        page_config = api.get("page") or {}
        if not page_config.get("enabled", False):
            params = api.get("params") or {}
            payload, attempt_count = self._request_with_retry(api, api_client, token, params)
            yield 1, payload, attempt_count
            return

        page_no_field = page_config.get("page_no_field", "page")
        page_size_field = page_config.get("page_size_field", "pagesize")
        page_size = int(page_config.get("page_size") or 20)
        # max_pages 是测试阶段保护，避免分页字段异常时无限请求。
        max_pages = int(page_config.get("max_pages") or 1)
        page_no = int((api.get("params") or {}).get(page_no_field) or 1)
        pages_requested = 0

        while pages_requested < max_pages:
            params = dict(api.get("params") or {})
            params[page_no_field] = page_no
            params[page_size_field] = page_size

            payload, attempt_count = self._request_with_retry(api, api_client, token, params)
            pages_requested += 1
            yield page_no, payload, attempt_count

            total = self._response_total(payload, api)
            if total is None:
                break
            if page_no * page_size >= total:
                break
            page_no += 1

    def _source_param_sets(
        self,
        connection: Any,
        api: dict[str, Any],
        offset: int | None = None,
    ) -> list[dict[str, Any]]:
        """从已入库的上游 raw 数据生成请求参数。

        当前支持两种最小来源：`source_primary_key` 单字段，以及从 raw_json
        顶层字段提取参数。raw_json 来源可附加固定等值过滤，用于只取某类上游单据。
        """
        param_source = api.get("param_source") or {}
        source_api_code = param_source.get("source_api_code")
        fields = param_source.get("fields") or []
        limit = int(param_source.get("limit") or 10)
        offset = self._param_source_offset(connection, api) if offset is None else offset

        if fields:
            return self._source_param_sets_from_raw_json_fields(
                connection,
                source_api_code,
                fields,
                param_source.get("filters") or [],
                limit,
                offset,
            )

        source_field = param_source.get("source_field")
        target_field = param_source.get("target_field")

        if source_field != "source_primary_key":
            raise ValueError(f"unsupported param source field: {source_field}")
        if not source_api_code or not target_field:
            raise ValueError(f"invalid param_source config: {api.get('api_code')}")

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
        source_api_code: str | None,
        fields: list[dict[str, Any]],
        filters: list[dict[str, Any]],
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        """从上游 raw_json 顶层字段生成请求参数。"""
        if not source_api_code:
            raise ValueError("invalid param_source config: missing source_api_code")

        select_parts = []
        where_parts = []
        query_params: dict[str, Any] = {"source_api_code": source_api_code, "limit": limit, "offset": offset}
        target_fields = []
        for index, field in enumerate(fields):
            source_field = str(field.get("source_field") or "")
            target_field = str(field.get("target_field") or "")
            if not source_field.startswith("raw_json.") or not target_field:
                raise ValueError(f"invalid raw_json param field: {source_field}")

            raw_json_path = source_field.removeprefix("raw_json.")
            if not RAW_JSON_FIELD_PATTERN.match(raw_json_path):
                raise ValueError(f"invalid raw_json param field: {source_field}")

            expression = f"JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.{raw_json_path}'))"
            alias = f"source_{index}"
            select_parts.append(f"{expression} AS {alias}")
            where_parts.append(f"{expression} IS NOT NULL AND {expression} <> ''")
            target_fields.append(target_field)

        for index, filter_config in enumerate(filters):
            source_field = str(filter_config.get("source_field") or "")
            if not source_field.startswith("raw_json."):
                raise ValueError(f"invalid raw_json param filter: {source_field}")

            raw_json_path = source_field.removeprefix("raw_json.")
            if not RAW_JSON_FIELD_PATTERN.match(raw_json_path):
                raise ValueError(f"invalid raw_json param filter: {source_field}")
            if "equals" not in filter_config:
                raise ValueError(f"invalid raw_json param filter: {source_field}")

            expression = f"JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.{raw_json_path}'))"
            param_name = f"filter_{index}"
            where_parts.append(f"{expression} = :{param_name}")
            query_params[param_name] = str(filter_config["equals"])

        aliases = [f"source_{index}" for index in range(len(fields))]
        sql = f"""
            SELECT {", ".join(select_parts)}
            FROM raw_api_data
            WHERE api_code = :source_api_code
              AND {" AND ".join(where_parts)}
            GROUP BY {", ".join(aliases)}
            ORDER BY {", ".join(aliases)}
            LIMIT :limit
            OFFSET :offset
        """
        result = connection.execute(text(sql), query_params)
        rows = []
        for row in result.mappings().all():
            rows.append({target_field: str(row[f"source_{index}"]) for index, target_field in enumerate(target_fields)})
        return rows

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

        这里保存 URL、方法、业务参数、HTTP 状态和响应体，便于后续重放或排查；
        accessToken 不会进入该表。
        """
        # request_params 是业务请求体，不包含 accessToken；鉴权头不落库。
        response = getattr(error.original_error, "response", None)
        status_code = getattr(response, "status_code", None)
        response_body = getattr(response, "text", None)
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
                "request_params": json.dumps(error.request_params, ensure_ascii=False, default=str),
                "response_status_code": status_code,
                "response_body": response_body,
                "error_message": str(error.original_error),
                "retry_count": error.retry_count,
            },
        )

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

    def _data_date(self, api: dict[str, Any], item: dict[str, Any]) -> date | None:
        """从单条数据中提取业务日期。

        date_field 由 YAML 配置控制。只取前 10 位是为了兼容常见的
        `YYYY-MM-DD HH:mm:ss` 或 ISO datetime 字符串。
        """
        date_field = api.get("date_field")
        if not date_field or not item.get(date_field):
            return None
        return date.fromisoformat(str(item[date_field])[:10])

    def _new_batch_no(self) -> str:
        """生成本次同步批次号。"""
        return datetime.now().strftime("sync_%Y%m%d_%H%M%S_%f")
