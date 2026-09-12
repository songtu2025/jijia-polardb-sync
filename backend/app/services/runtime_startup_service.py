import logging

from sqlalchemy.engine import Engine

from app.api_config_registry import load_official_catalog, load_published_api_configs
from backend.app.core.config import WebSettings
from backend.app.services.runtime_target_verifier import verify_runtime_target

PRODUCTION_ENVIRONMENTS = {"prod", "production"}
logger = logging.getLogger(__name__)


def validate_runtime_startup(settings: WebSettings, engine: Engine) -> None:
    """启动 API 或 Worker 前验证已发布配置和生产数据库目标。"""
    try:
        api_configs = load_published_api_configs(engine)
        load_official_catalog(settings.api_catalog_path)
        if not api_configs:
            raise ValueError("Published API catalog is empty")
    except Exception:
        # 配置异常可能包含数据库或原始值，启动日志只允许输出稳定错误码。
        raise RuntimeError("RUNTIME_API_CONFIG_INVALID") from None
    if settings.app_env.lower() not in PRODUCTION_ENVIRONMENTS:
        return

    result = verify_runtime_target(engine)
    if result.status != "pass":
        # 只暴露稳定错误码，禁止把数据库异常正文带入进程启动日志。
        raise RuntimeError(f"RUNTIME_TARGET_NOT_READY:{result.code}")
    if result.details:
        logger.warning(
            "RUNTIME_SCHEMA_INDEX_DRIFT unexpected_non_unique=%s legacy_non_unique=%s",
            result.details.get("unexpectedNonUniqueIndexCount", 0),
            result.details.get("legacyNonUniqueIndexCount", 0),
        )
