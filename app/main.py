import argparse
import logging

from requests import HTTPError, RequestException
from sqlalchemy.exc import SQLAlchemyError

from app.auth import JijiaAuthClient
from app.api_client import JijiaApiClient
from app.config import load_api_configs, load_settings
from app.db import check_db_connection, create_db_engine
from app.logger import setup_logging
from app.sync_engine import SyncEngine


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    每个参数都对应一个独立的运行模式，方便部署前分步骤验证：先测数据库，
    再测 token，最后再跑 mock 或真实接口同步。
    """
    parser = argparse.ArgumentParser(description="积加开放平台到 PolarDB MySQL 同步服务")
    parser.add_argument("--check-db", action="store_true", help="只检查数据库连接")
    parser.add_argument("--mock-sync", action="store_true", help="写入一批 mock 同步数据")
    parser.add_argument("--test-token", action="store_true", help="测试获取积加 accessToken")
    parser.add_argument("--test-api", help="测试单个积加 API，并写入 raw_api_data")
    parser.add_argument("--sync-api", help="同步单个真实积加 API，并写入 raw_api_data")
    parser.add_argument("--sync-enabled", action="store_true", help="同步 YAML 中 enabled=true 的真实积加 API")
    parser.add_argument("--sync-api-configs", action="store_true", help="同步 YAML API 配置到 api_config 表")
    return parser.parse_args()


def main() -> None:
    """命令行入口。

    入口层只负责选择运行模式和处理顶层异常；真正的认证、请求、入库逻辑
    分别交给 AuthClient、ApiClient 和 SyncEngine，避免主函数堆积业务细节。
    """
    args = parse_args()
    settings = load_settings()
    setup_logging(settings.log_dir, settings.log_level)
    logger = logging.getLogger(__name__)

    if args.check_db:
        _check_db(settings)
        logger.info("database connection ok")
        return

    if args.test_token:
        _test_token(settings)
        return

    api_configs = load_api_configs(settings.api_config_path)
    if args.sync_api_configs:
        _sync_api_configs(settings, api_configs)
        return

    if args.sync_enabled:
        _sync_enabled(settings, api_configs)
        return

    # sync-api 和 test-api 共用同一条单接口执行链路，差别只在命令语义。
    if args.sync_api:
        _run_single_api(settings, api_configs, args.sync_api, "sync api")
        return

    if args.test_api:
        _run_single_api(settings, api_configs, args.test_api, "test api")
        return

    if args.mock_sync:
        engine = create_db_engine(settings)
        try:
            batch_no = SyncEngine(api_configs, engine).mock_sync()
        except SQLAlchemyError:
            logger.error("mock sync failed: check database connection, schema, and privileges")
            raise SystemExit(1)
        logger.info("mock sync batch created: %s", batch_no)
        return

    SyncEngine(api_configs).dry_run()
    logger.info("dry-run finished; use --mock-sync to verify database writes")


def _check_db(settings) -> None:
    """检查数据库连接是否可用。

    这是上线前最小验证命令，只执行 `SELECT 1`，不会写入任何业务表。
    """
    engine = create_db_engine(settings)
    try:
        check_db_connection(engine)
    except SQLAlchemyError:
        logging.getLogger(__name__).error(
            "database connection failed: check .env credentials, network allowlist, and user privileges"
        )
        raise SystemExit(1)


def _test_token(settings) -> None:
    """测试积加 accessToken 获取流程。

    成功时只打印过期信息，不打印 token 本身，避免在终端或日志里泄露凭证。
    """
    logger = logging.getLogger(__name__)
    try:
        token = JijiaAuthClient(settings).get_access_token()
    except HTTPError as error:
        status_code = error.response.status_code if error.response is not None else "unknown"
        logger.error("access token request failed: http_status=%s", status_code)
        raise SystemExit(1)
    except ValueError as error:
        logger.error("access token request failed: %s", error)
        raise SystemExit(1)
    except RequestException:
        logger.error("access token request failed: check API host and network")
        raise SystemExit(1)

    logger.info("access token ok; expires_in=%s expires_out=%s", token.expires_in, token.expires_out)


def _sync_api_configs(settings, api_configs) -> None:
    """把 YAML API 配置写入数据库 api_config 表。

    该命令只同步配置元数据，不获取 token，也不请求任何真实业务接口。
    """
    logger = logging.getLogger(__name__)
    engine = create_db_engine(settings)
    try:
        count = SyncEngine(api_configs, engine).sync_api_configs()
    except SQLAlchemyError:
        logger.error("sync api configs failed: check database schema and privileges")
        raise SystemExit(1)

    logger.info("api configs synced: count=%s", count)


def _sync_enabled(settings, api_configs) -> None:
    """同步 YAML 中所有 enabled=true 的接口。

    这是生产定时任务应使用的主入口：一次运行创建一个 sync_batch，并为每个
    API 写入独立的 sync_api_log。
    """
    logger = logging.getLogger(__name__)
    engine = create_db_engine(settings)
    try:
        token = JijiaAuthClient(settings).get_access_token()
        result = SyncEngine(api_configs, engine).sync_enabled_apis(JijiaApiClient(settings), token)
    except HTTPError as error:
        status_code = error.response.status_code if error.response is not None else "unknown"
        logger.error("sync enabled failed: http_status=%s", status_code)
        raise SystemExit(1)
    except (RequestException, SQLAlchemyError, ValueError):
        logger.error("sync enabled failed: check API config, token, database schema, and privileges")
        raise SystemExit(1)

    if result["failed_count"]:
        logger.error("sync enabled finished with failed APIs: batch=%s failed=%s", result["batch_no"], result["failed_count"])
        raise SystemExit(1)
    logger.info(
        "sync enabled ok: batch=%s apis=%s rows=%s requests=%s",
        result["batch_no"],
        result["api_count"],
        result["item_count"],
        result["request_count"],
    )


def _run_single_api(settings, api_configs, api_code: str, action_label: str) -> None:
    """同步单个指定 API。

    主要用于接入新接口时小范围验证配置、分页和入库结果，避免一上来跑完整
    API 列表导致排查范围过大。
    """
    logger = logging.getLogger(__name__)
    engine = create_db_engine(settings)
    try:
        token = JijiaAuthClient(settings).get_access_token()
        result = SyncEngine(api_configs, engine).test_api_once(api_code, JijiaApiClient(settings), token)
    except HTTPError as error:
        status_code = error.response.status_code if error.response is not None else "unknown"
        logger.error("%s failed: http_status=%s", action_label, status_code)
        raise SystemExit(1)
    except (RequestException, SQLAlchemyError, ValueError):
        logger.error("%s failed: check API config, token, database schema, and privileges", action_label)
        raise SystemExit(1)

    if result["failed_count"]:
        logger.error("%s failed: batch=%s", action_label, result["batch_no"])
        raise SystemExit(1)
    logger.info(
        "%s ok: api_code=%s batch=%s rows=%s requests=%s",
        action_label,
        api_code,
        result["batch_no"],
        result["item_count"],
        result["request_count"],
    )


if __name__ == "__main__":
    main()
