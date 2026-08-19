from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class AppSettings(BaseSettings):
    """集中管理运行配置。

    配置来源优先级由 pydantic-settings 处理：环境变量优先，其次读取项目根目录
    `.env`，最后才使用这里的默认值。默认值只用于本地开发或示例，真实部署时
    必须通过环境变量覆盖 API 凭证和数据库密码。
    """

    app_env: str = "local"
    log_level: str = "INFO"
    log_dir: Path = Path("logs")

    jijia_base_url: str = "https://open.gerpgo.com"
    jijia_open_gateway_prefix: str = "/api/open"
    jijia_app_id: str = "your_app_id"
    jijia_app_key: str = "your_app_key"
    jijia_token_url: str = "/api_token"
    jijia_token_cache_path: Path = Path("logs/token_cache.json")

    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "jijia_sync"
    db_user: str = "your_db_user"
    db_password: str = "your_db_password"

    api_config_path: Path = Field(default=Path("config/api_config.example.yaml"))

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> URL:
        """生成 SQLAlchemy 使用的 MySQL 连接串。

        这里不在日志中输出连接串，因为其中包含数据库用户名和密码。
        `charset=utf8mb4` 用于保证中文、表情和其他 4 字节字符能完整写入。
        """
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )


def load_settings() -> AppSettings:
    """读取项目运行配置。

    调用方不需要知道 `.env` 或环境变量的读取细节，只依赖返回的
    `AppSettings` 对象即可。
    """
    return AppSettings()


def load_api_configs(path: str | Path) -> list[dict[str, Any]]:
    """读取 YAML 中的接口同步配置。

    YAML 顶层必须包含 `apis` 列表，每项显式声明唯一 api_code、path 和布尔
    enabled，避免缺失或字符串值被同步引擎误判为启用。
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"API config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    apis = data.get("apis", [])
    if not isinstance(apis, list):
        raise ValueError("API config field 'apis' must be a list")

    seen_api_codes = set()
    for index, api in enumerate(apis):
        if not isinstance(api, dict):
            raise ValueError(f"API config item at index {index} must be a mapping")

        api_code = api.get("api_code")
        if not isinstance(api_code, str) or not api_code.strip():
            raise ValueError(f"API config item at index {index} must define api_code")
        if api_code in seen_api_codes:
            raise ValueError(f"Duplicate API config api_code: {api_code}")
        seen_api_codes.add(api_code)

        path_value = api.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ValueError(f"API config {api_code} must define path")
        if "enabled" not in api or type(api["enabled"]) is not bool:
            raise ValueError(f"API config {api_code} enabled must be a boolean")

    return apis
