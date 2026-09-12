from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.api_config_registry import load_official_catalog
from backend.app.services.api_policy_service import list_catalog_data, load_catalog


def list_connected_catalog_data(
    db: Session,
    official_catalog_path: str | Path,
    account_id: int | None = None,
) -> list[dict[str, object]]:
    """为已接入接口补充官方一级业务域，仅用于接口中心展示。"""
    official_domains = {
        str(item["doc_id"]): str(item.get("menu_path") or "").split(">", maxsplit=1)[0].strip()
        for item in load_official_catalog(official_catalog_path)
        if item.get("doc_id") is not None and str(item.get("menu_path") or "").strip()
    }
    return [
        {
            **item,
            "officialDomain": official_domains.get(str(item["officialDocId"]))
            if item.get("officialDocId") is not None
            else None,
        }
        for item in list_catalog_data(db, account_id)
    ]


def list_official_catalog_data(
    db: Session,
    official_catalog_path: str | Path,
) -> list[dict[str, object]]:
    """合并官方目录与已发布配置，供接口中心查看待接入范围。"""
    configured_by_path: dict[str, list[dict[str, Any]]] = {}
    for config in load_catalog(db):
        configured_by_path.setdefault(str(config["path"]), []).append(config)

    result = []
    for item in load_official_catalog(official_catalog_path):
        path = str(item.get("api_url") or "")
        configured = configured_by_path.get(path, [])
        configured_codes = [str(config["api_code"]) for config in configured]
        enabled_codes = [
            str(config["api_code"])
            for config in configured
            if bool((config.get("_registry") or {}).get("platformEnabled"))
        ]
        configured_methods = sorted(
            {str(config.get("method") or "POST").upper() for config in configured}
        )
        official_method = str(item.get("method") or "").upper()
        result.append(
            {
                "docId": item.get("doc_id"),
                "menuPath": str(item.get("menu_path") or "其他"),
                "name": str(item.get("api_name") or path or "未命名接口"),
                "path": path,
                "method": official_method,
                "classification": item.get("classification"),
                "executionStage": item.get("execution_stage"),
                "executionReason": item.get("execution_reason"),
                "requiredFields": list(item.get("required_body_fields") or []),
                "businessRequiredFields": list(item.get("business_required_fields") or []),
                "responseFields": list(item.get("response_fields") or []),
                "hasPageResponse": bool(item.get("has_page_response")),
                "hasListResponse": bool(item.get("has_list_response")),
                "sensitive": bool(item.get("has_sensitive_response_fields")),
                "systemConfigured": bool(configured_codes),
                "configuredApiCodes": configured_codes,
                "platformEnabledApiCodes": enabled_codes,
                "configuredMethods": configured_methods,
                "methodMismatch": bool(
                    configured_methods
                    and official_method
                    and official_method not in configured_methods
                ),
            }
        )
    return result
