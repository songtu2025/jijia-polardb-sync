from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests
import yaml

DOC_TREE_URL = "https://open.gerpgo.com/api/openAdmin/doc/tree"
DOC_DETAIL_URL = "https://open.gerpgo.com/api/openAdmin/doc/detail?id={doc_id}"

READ_OPS = {"page", "list", "query", "detail", "get", "tree"}
WRITE_HINTS = {
    "update",
    "save",
    "create",
    "add",
    "delete",
    "remove",
    "import",
    "submit",
    "sync",
    "cancel",
    "approve",
    "upload",
    "confirm",
}
PAGE_FIELDS = {"page", "pagesize", "pageSize", "pageNo", "size", "current", "limit"}
OPTIONAL_QUERY_OBJECTS = {"condition", "param", "params", "query", "filter"}
SENSITIVE_WORDS = [
    "phone",
    "mobile",
    "email",
    "mail",
    "address",
    "addr",
    "token",
    "password",
    "passwd",
    "secret",
    "credential",
    "身份证",
    "电话",
    "手机",
    "邮箱",
    "地址",
    "令牌",
    "密码",
]
SENSITIVE_PATTERN = re.compile("|".join(re.escape(word) for word in SENSITIVE_WORDS), re.IGNORECASE)
HIGH_RISK_MENU_ROOTS = {"订单", "财务", "客服", "物流", "销售"}
HIGH_RISK_URL_WORDS = [
    "order",
    "fee",
    "cost",
    "payment",
    "refund",
    "asset",
    "finance",
    "delivery",
    "shipment",
    "voice",
    "review",
    "feedback",
]
HIGH_RISK_URL_PATTERN = re.compile("|".join(re.escape(word) for word in HIGH_RISK_URL_WORDS), re.IGNORECASE)
KNOWN_RISK_REVIEW_PATHS = {
    # 这些路径已有真实探测结论：编码、限流、数组入参或敏感字段边界尚未稳定，不应反复作为普通候选。
    "/middle/base/marketNames/query",
    "/purchase/inventory/purchaseSaleStorageSelf/page",
    "/operation/sts/trafficSkuAnalysis/page",
    "/purchase/store/multiTypeWarehouse/page",
    "/purchase/srm/quickInbound/query",
}


def classify_api_detail(detail: dict[str, Any]) -> dict[str, Any]:
    """按同步风险把积加文档详情归类。

    分类只使用公开文档元数据，不读取 `.env`，不请求真实业务接口。结果用于判断
    后续接入顺序：可直接读、依赖上游参数、含敏感字段、写操作或暂不适配。
    """
    op_type = str(detail.get("opType") or "").lower()
    api_url = str(detail.get("apiUrl") or "")
    request_body = detail.get("requestBody") or []
    response_body = detail.get("responseBody") or []

    required_fields = _required_body_fields(request_body)
    business_required_fields = [
        field for field in required_fields if field not in PAGE_FIELDS and field not in OPTIONAL_QUERY_OBJECTS
    ]
    has_page = _has_page_response(response_body)
    has_list = _has_list_response(response_body)
    has_sensitive = _has_sensitive_response_fields(response_body)

    if _is_write_like(op_type, api_url):
        classification = "write_or_mutation"
    elif business_required_fields:
        classification = "requires_upstream_params"
    elif has_sensitive:
        classification = "sensitive_review"
    elif has_page or has_list or op_type in READ_OPS:
        classification = "direct_read_candidate"
    else:
        classification = "unsupported_shape_review"

    return {
        "classification": classification,
        "method": str(detail.get("erpMethod") or "").upper(),
        "op_type": op_type,
        "required_body_fields": required_fields,
        "business_required_fields": business_required_fields,
        "has_page_response": has_page,
        "has_list_response": has_list,
        "has_sensitive_response_fields": has_sensitive,
    }


def execution_plan_for_api(item: dict[str, Any]) -> dict[str, str]:
    """给覆盖矩阵中的单个 API 标记下一步执行层级。

    `classification` 只说明公开文档形态；这里再结合是否已配置、是否启用、
    菜单域和 URL 风险，给后续阶段一个可执行分流，避免把订单、财务、
    客服、物流费用等高风险接口误当成普通低风险候选。
    """
    if item.get("configured_enabled"):
        return {
            "execution_bucket": "configured",
            "execution_stage": "configured_enabled",
            "execution_reason": "已进入 enabled 批量同步。",
        }

    if item.get("configured_api_code"):
        return {
            "execution_bucket": "configured",
            "execution_stage": "configured_disabled",
            "execution_reason": "已配置但默认关闭，需按数据量、窗口和批量耗时评估后再启用。",
        }

    classification = item.get("classification")
    if classification == "requires_upstream_params":
        return {
            "execution_bucket": "needs_upstream_params",
            "execution_stage": "needs_param_source",
            "execution_reason": "公开文档显示存在业务必填参数，需先证明真实上游参数来源。",
        }
    if classification == "sensitive_review":
        return {
            "execution_bucket": "needs_sensitive_review",
            "execution_stage": "needs_sensitive_review",
            "execution_reason": "公开文档响应或接口域可能包含敏感信息，需先做字段审查和脱敏边界确认。",
        }
    if classification == "write_or_mutation":
        return {
            "execution_bucket": "defer_or_review",
            "execution_stage": "defer_write_or_mutation",
            "execution_reason": "写入或确认类接口不属于当前只读备份同步范围，默认暂缓。",
        }
    if classification == "direct_read_candidate":
        if item.get("api_url") in KNOWN_RISK_REVIEW_PATHS:
            return {
                "execution_bucket": "defer_or_review",
                "execution_stage": "known_risk_review",
                "execution_reason": "该接口已有真实探测风险记录，需有新证据后再重新评估。",
            }
        if _needs_domain_risk_review(item):
            return {
                "execution_bucket": "defer_or_review",
                "execution_stage": "risk_review_before_probe",
                "execution_reason": "接口位于订单、财务、客服、物流或销售等高风险域，需先人工确认字段和调用边界。",
            }
        return {
            "execution_bucket": "can_probe",
            "execution_stage": "can_probe_next",
            "execution_reason": "未配置的低风险直读候选，可按默认 disabled 小窗口探测。",
        }

    return {
        "execution_bucket": "defer_or_review",
        "execution_stage": "unsupported_shape_review",
        "execution_reason": "公开文档形态暂不适配当前同步引擎，需单独确认请求和响应结构。",
    }


def build_catalog(api_config_path: str | Path = "config/api_config.example.yaml") -> dict[str, Any]:
    """拉取公开文档目录和详情，生成当前 API 覆盖矩阵。"""
    configured_by_path = _load_configured_apis(api_config_path)
    tree = _get_json(DOC_TREE_URL).get("data") or []
    api_nodes = list(_walk_menu(tree))
    catalog = []
    errors = []

    for menu_path, api in api_nodes:
        doc_id = api.get("id")
        try:
            detail = _get_json(DOC_DETAIL_URL.format(doc_id=doc_id)).get("data") or {}
            classified = classify_api_detail(detail)
            configured_api = configured_by_path.get(detail.get("apiUrl"))
            item = {
                "doc_id": doc_id,
                "menu_path": " > ".join(menu_path),
                "api_name": detail.get("apiName") or api.get("name") or "",
                "api_url": detail.get("apiUrl") or api.get("url") or "",
                "method": classified["method"],
                "op_type": classified["op_type"],
                "classification": classified["classification"],
                "required_body_fields": classified["required_body_fields"],
                "business_required_fields": classified["business_required_fields"],
                "has_page_response": classified["has_page_response"],
                "has_list_response": classified["has_list_response"],
                "has_sensitive_response_fields": classified["has_sensitive_response_fields"],
                "configured_api_code": configured_api.get("api_code") if configured_api else "",
                "configured_enabled": bool(configured_api.get("enabled")) if configured_api else False,
            }
            item.update(execution_plan_for_api(item))
            catalog.append(item)
        except requests.RequestException as error:
            errors.append({"doc_id": doc_id, "error": str(error)})
        time.sleep(0.02)

    return {
        "source": {
            "tree_url": DOC_TREE_URL,
            "detail_url_template": DOC_DETAIL_URL,
        },
        "summary": _summarize_catalog(catalog, errors, configured_by_path),
        "apis": sorted(catalog, key=lambda item: (item["menu_path"], item["doc_id"] or 0)),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成积加开放平台公开文档 API 覆盖矩阵")
    parser.add_argument("--api-config", default="config/api_config.example.yaml", help="本地 API YAML 配置路径")
    parser.add_argument("--output", help="输出 JSON 文件路径；不传则只打印摘要")
    parser.add_argument("--summary", action="store_true", help="打印摘要")
    args = parser.parse_args()

    catalog = build_catalog(args.api_config)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.summary or not args.output:
        print(json.dumps(catalog["summary"], ensure_ascii=False, indent=2))


def _summarize_catalog(
    catalog: list[dict[str, Any]], errors: list[dict[str, Any]], configured_by_path: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    classification_counts = Counter(item["classification"] for item in catalog)
    execution_bucket_counts = Counter(item["execution_bucket"] for item in catalog)
    execution_stage_counts = Counter(item["execution_stage"] for item in catalog)
    menu_counts = Counter(item["menu_path"].split(" > ")[0] for item in catalog)
    return {
        "tree_api_count": len(catalog) + len(errors),
        "detail_success_count": len(catalog),
        "detail_error_count": len(errors),
        "configured_real_api_count": len(configured_by_path),
        "configured_enabled_real_api_count": sum(1 for api in configured_by_path.values() if api.get("enabled")),
        "classification_counts": dict(sorted(classification_counts.items())),
        "execution_bucket_counts": dict(sorted(execution_bucket_counts.items())),
        "execution_stage_counts": dict(sorted(execution_stage_counts.items())),
        "menu_counts": dict(sorted(menu_counts.items())),
    }


def _load_configured_apis(api_config_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(api_config_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    configured = {}
    for api in data.get("apis") or []:
        api_path = str(api.get("path") or "")
        if api_path and not api_path.startswith("/replace/"):
            configured[api_path] = api
    return configured


def _get_json(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def _walk_menu(nodes: list[dict[str, Any]], path: tuple[str, ...] = ()):
    for node in nodes or []:
        menu_name = node.get("menuName") or node.get("menuCode") or ""
        current_path = path + (menu_name,)
        for api in node.get("apiList") or []:
            yield current_path, api
        yield from _walk_menu(node.get("subMenu") or [], current_path)


def _flatten_fields(fields: list[dict[str, Any]], prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    result = []
    for field in fields or []:
        name = str(field.get("name") or "")
        full_name = f"{prefix}.{name}" if prefix and name else name or prefix
        result.append((full_name, field))
        result.extend(_flatten_fields(field.get("children") or [], full_name))
    return result


def _required_body_fields(fields: list[dict[str, Any]]) -> list[str]:
    return [str(field.get("name") or "") for field in fields or [] if field.get("must") is True]


def _has_page_response(fields: list[dict[str, Any]]) -> bool:
    names = {name for name, _ in _flatten_fields(fields)}
    return "data.rows" in names or any(name.endswith(".rows") for name in names)


def _has_list_response(fields: list[dict[str, Any]]) -> bool:
    for name, field in _flatten_fields(fields):
        if name == "data" and "array" in str(field.get("type") or "").lower():
            return True
    return False


def _has_sensitive_response_fields(fields: list[dict[str, Any]]) -> bool:
    for name, field in _flatten_fields(fields):
        text = f"{name} {field.get('description') or ''}"
        if SENSITIVE_PATTERN.search(text):
            return True
    return False


def _is_write_like(op_type: str, api_url: str) -> bool:
    url = api_url.lower()
    return (
        op_type in WRITE_HINTS
        or any(hint in op_type for hint in WRITE_HINTS)
        or any(
            fragment in url
            for fragment in ["/update", "/delete", "/save", "/create", "/add", "/import", "/upload", "/confirm"]
        )
    )


def _needs_domain_risk_review(item: dict[str, Any]) -> bool:
    menu_root = str(item.get("menu_path") or "").split(" > ")[0]
    if menu_root in HIGH_RISK_MENU_ROOTS:
        return True
    text = f"{item.get('api_url') or ''} {item.get('api_name') or ''}"
    return bool(HIGH_RISK_URL_PATTERN.search(text))


if __name__ == "__main__":
    main()
