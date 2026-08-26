from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebSettings(BaseSettings):
    """集中管理身份认证和邮件配置。"""

    app_env: str = "local"
    public_web_url: str = "http://localhost:5173"
    session_cookie_name: str = "jijia_session"
    session_cookie_secure: bool = False
    session_absolute_hours: int = 12
    session_idle_minutes: int = 120
    invitation_ttl_hours: int = 24
    password_min_length: int = 12
    login_max_failures: int = 5
    login_lock_minutes: int = 15

    mail_provider: Literal["smtp", "console", "fake"] = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production_settings(self) -> "WebSettings":
        """阻止生产环境使用会泄露邀请链接的本地邮件方式。"""
        if self.app_env.lower() in {"prod", "production"}:
            if self.mail_provider != "smtp":
                raise ValueError("Production requires MAIL_PROVIDER=smtp")
            if not self.session_cookie_secure:
                raise ValueError("Production requires SESSION_COOKIE_SECURE=true")
            if not self.session_cookie_name.startswith("__Host-"):
                raise ValueError("Production session cookie must use the __Host- prefix")
        return self


@lru_cache
def get_web_settings() -> WebSettings:
    """加载并缓存 Web 服务配置。"""
    return WebSettings()
