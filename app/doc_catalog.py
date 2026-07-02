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
WRITE_HINTS = {"update", "save", "create", "add", "delete", "remove", "import", "submit", "sync", "cancel", "approve", "upload"}
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
            catalog.append(
                {
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
            )
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
    menu_counts = Counter(item["menu_path"].split(" > ")[0] for item in catalog)
    return {
        "tree_api_count": len(catalog) + len(errors),
        "detail_success_count": len(catalog),
        "detail_error_count": len(errors),
        "configured_real_api_count": len(configured_by_path),
        "configured_enabled_real_api_count": sum(1 for api in configured_by_path.values() if api.get("enabled")),
        "classification_counts": dict(sorted(classification_counts.items())),
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
        or any(fragment in url for fragment in ["/update", "/delete", "/save", "/create", "/add", "/import", "/upload"])
    )


if __name__ == "__main__":
    main()
