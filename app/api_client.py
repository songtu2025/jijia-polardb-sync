from typing import Any
from urllib.parse import urljoin

import requests

from app.auth import AccessToken
from app.config import AppSettings


class JijiaApiClient:
    """积加业务接口客户端。

    该类只负责发请求、检查基础响应格式并返回原始 payload；分页、入库、
    重试和日志由 `SyncEngine` 统一控制，避免 HTTP 层掺入同步状态。
    """

    def __init__(self, settings: AppSettings, timeout_seconds: int = 30):
        """创建可复用的 requests Session。"""
        self.settings = settings
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def request(
        self,
        api_config: dict[str, Any],
        token: AccessToken,
        params_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """执行一次真实业务接口请求。

        `params_override` 用于分页场景：同步引擎每次生成当前页参数后传进来；
        非分页接口则直接使用 YAML 配置里的默认 params。
        """
        method = str(api_config.get("method", "POST")).upper()
        url = self.request_url(api_config)
        # 分页时由调用方传入单页参数；未传入时使用 YAML 中的默认 params。
        params = params_override if params_override is not None else api_config.get("params") or {}
        headers = {"accessToken": token.value}

        timeout_seconds = int(api_config.get("timeout_seconds") or self.timeout_seconds)
        if method == "POST":
            response = self.session.post(url, json=params, headers=headers, timeout=timeout_seconds)
        elif method == "GET":
            response = self.session.get(url, params=params, headers=headers, timeout=timeout_seconds)
        else:
            raise ValueError(f"unsupported API method: {method}")

        response.raise_for_status()
        payload = response.json()
        code = payload.get("code")
        if code not in (0, 200):
            messages = payload.get("messages") or [f"API request failed: {api_config.get('api_code')}"]
            raise ValueError(str(messages[0]))
        return payload

    def request_url(self, api_config: dict[str, Any]) -> str:
        """根据单个 API 配置生成完整请求 URL。"""
        return self._open_api_url(str(api_config["path"]))

    def _open_api_url(self, path: str) -> str:
        """拼接开放平台网关 URL。

        与认证客户端保持同一套路径规则：配置可以只写业务路径，也可以写已经
        带网关前缀的路径。
        """
        prefix = self.settings.jijia_open_gateway_prefix.strip("/")
        clean_path = path.lstrip("/")
        if prefix and not clean_path.startswith(prefix + "/"):
            clean_path = f"{prefix}/{clean_path}"
        return urljoin(self.settings.jijia_base_url.rstrip("/") + "/", clean_path)
