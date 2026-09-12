import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

RAW_JSON_FIELD_PATTERN = re.compile(r"^[A-Za-z0-9_.]+$")


@dataclass(frozen=True)
class RawJsonParamSource:
    """描述从已落库 raw_json 生成请求参数所需的完整输入。"""

    account_id: int
    target_api_code: str
    source_api_code: str | None
    fields: tuple[Mapping[str, Any], ...]
    filters: tuple[Mapping[str, Any], ...]
    limit: int
    offset: int
    exclude_existing_target: bool = False
    refresh_before: datetime | None = None

    @property
    def uses_array_field(self) -> bool:
        """判断配置是否包含需要展开的数组字段。"""
        return any("[]" in str(field.get("source_field") or "") for field in self.fields)


@dataclass(frozen=True)
class RawJsonParamTarget:
    """记录查询列对应的请求字段及列表包装规则。"""

    name: str
    wrap_in_list: bool


@dataclass(frozen=True)
class RawJsonFieldQuery:
    """保存普通 raw_json 字段查询和结果映射规则。"""

    sql: str
    parameters: dict[str, Any]
    targets: tuple[RawJsonParamTarget, ...]


@dataclass(frozen=True)
class RawJsonArrayQuery:
    """保存数组字段查询和数组展开规则。"""

    sql: str
    parameters: dict[str, Any]
    target: RawJsonParamTarget
    array_path: str
    value_path: str
    limit: int
    offset: int


def build_raw_json_field_query(source: RawJsonParamSource) -> RawJsonFieldQuery:
    """校验字段配置并生成普通 raw_json 参数来源查询。"""
    source_api_code = _required_source_api_code(source)
    raw_json_column = "source_data.raw_json" if source.exclude_existing_target else "raw_json"
    select_parts, select_expressions, where_parts, targets = _field_query_parts(
        source.fields,
        raw_json_column,
    )
    parameters: dict[str, Any] = {
        "jijia_account_id": source.account_id,
        "source_api_code": source_api_code,
        "limit": source.limit,
        "offset": source.offset,
    }
    where_parts.extend(
        _filter_query_parts(
            source.filters,
            raw_json_column,
            parameters,
        )
    )

    from_clause = "raw_api_data source_data" if source.exclude_existing_target else "raw_api_data"
    api_code_column = "source_data.api_code" if source.exclude_existing_target else "api_code"
    account_column = (
        "source_data.jijia_account_id" if source.exclude_existing_target else "jijia_account_id"
    )
    join_clause = _target_join_clause(
        source,
        select_expressions[0],
        where_parts,
        parameters,
    )
    aliases = [f"source_{index}" for index in range(len(source.fields))]
    order_clause = ", ".join(aliases)
    if source.refresh_before is not None:
        order_clause = f"MIN(target_data.updated_at), {order_clause}"
    sql = f"""
        SELECT {", ".join(select_parts)}
        FROM {from_clause}
        {join_clause}
        WHERE {account_column} = :jijia_account_id
          AND {api_code_column} = :source_api_code
          AND {" AND ".join(where_parts)}
        GROUP BY {", ".join(aliases)}
        ORDER BY {order_clause}
        LIMIT :limit
        OFFSET :offset
    """
    return RawJsonFieldQuery(sql, parameters, targets)


def field_rows_to_params(
    rows: Iterable[Mapping[str, Any]],
    query: RawJsonFieldQuery,
) -> list[dict[str, Any]]:
    """按查询列顺序把数据库行转换成请求参数。"""
    params_list = []
    for row in rows:
        params = {}
        for index, target in enumerate(query.targets):
            value = str(row[f"source_{index}"])
            params[target.name] = [value] if target.wrap_in_list else value
        params_list.append(params)
    return params_list


def build_raw_json_array_query(source: RawJsonParamSource) -> RawJsonArrayQuery:
    """校验单层数组配置并生成读取 raw_json 的查询。"""
    source_api_code = _required_source_api_code(source)
    if source.filters:
        raise ValueError("raw_json array param source does not support filters")
    if len(source.fields) != 1:
        raise ValueError("raw_json array param source supports exactly one field")

    field = source.fields[0]
    source_field = str(field.get("source_field") or "")
    target_field = str(field.get("target_field") or "")
    if not source_field.startswith("raw_json.") or not target_field:
        raise ValueError(f"invalid raw_json param field: {source_field}")

    raw_json_path = source_field.removeprefix("raw_json.")
    if raw_json_path.count("[]") != 1:
        raise ValueError(f"invalid raw_json array param field: {source_field}")
    array_path, value_path = raw_json_path.split("[]", 1)
    value_path = value_path.removeprefix(".")
    if (
        not RAW_JSON_FIELD_PATTERN.match(array_path)
        or not value_path
        or not RAW_JSON_FIELD_PATTERN.match(value_path)
    ):
        raise ValueError(f"invalid raw_json array param field: {source_field}")

    sql = """
        SELECT raw_json
        FROM raw_api_data
        WHERE jijia_account_id = :jijia_account_id
          AND api_code = :source_api_code
          AND raw_json IS NOT NULL
        ORDER BY id
    """
    return RawJsonArrayQuery(
        sql=sql,
        parameters={
            "jijia_account_id": source.account_id,
            "source_api_code": source_api_code,
        },
        target=RawJsonParamTarget(
            name=target_field,
            wrap_in_list=bool(field.get("wrap_in_list")),
        ),
        array_path=array_path,
        value_path=value_path,
        limit=source.limit,
        offset=source.offset,
    )


def array_rows_to_params(
    rows: Iterable[Mapping[str, Any]],
    query: RawJsonArrayQuery,
    get_by_path: Callable[[dict[str, Any], str], Any],
) -> list[dict[str, Any]]:
    """解析数据库中的 raw_json，并展开、去重、排序数组字段值。"""
    values: set[str] = set()
    for row in rows:
        item = _raw_json_object(row.get("raw_json"))
        if item is None:
            continue
        array_items = get_by_path(item, query.array_path)
        if not isinstance(array_items, list):
            continue
        for array_item in array_items:
            if not isinstance(array_item, dict):
                continue
            value = get_by_path(array_item, query.value_path)
            if value is not None and str(value) != "":
                values.add(str(value))

    selected_values = sorted(values)[query.offset : query.offset + query.limit]
    return [
        {query.target.name: ([value] if query.target.wrap_in_list else value)}
        for value in selected_values
    ]


def _required_source_api_code(source: RawJsonParamSource) -> str:
    if not source.source_api_code:
        raise ValueError("invalid param_source config: missing source_api_code")
    return source.source_api_code


def _field_query_parts(
    fields: tuple[Mapping[str, Any], ...],
    raw_json_column: str,
) -> tuple[list[str], list[str], list[str], tuple[RawJsonParamTarget, ...]]:
    select_parts = []
    select_expressions = []
    where_parts = []
    targets = []
    for index, field in enumerate(fields):
        source_field = str(field.get("source_field") or "")
        target_field = str(field.get("target_field") or "")
        if not target_field:
            raise ValueError(f"invalid raw_json param field: {source_field}")
        expression = _raw_json_expression(source_field, raw_json_column, "field")
        alias = f"source_{index}"
        select_parts.append(f"{expression} AS {alias}")
        select_expressions.append(expression)
        where_parts.append(f"{expression} IS NOT NULL AND {expression} <> ''")
        targets.append(
            RawJsonParamTarget(
                name=target_field,
                wrap_in_list=bool(field.get("wrap_in_list")),
            )
        )
    return select_parts, select_expressions, where_parts, tuple(targets)


def _filter_query_parts(
    filters: tuple[Mapping[str, Any], ...],
    raw_json_column: str,
    parameters: dict[str, Any],
) -> list[str]:
    where_parts = []
    for index, filter_config in enumerate(filters):
        source_field = str(filter_config.get("source_field") or "")
        expression = _raw_json_expression(source_field, raw_json_column, "filter")
        if "equals" not in filter_config:
            raise ValueError(f"invalid raw_json param filter: {source_field}")
        param_name = f"filter_{index}"
        where_parts.append(f"{expression} = :{param_name}")
        parameters[param_name] = str(filter_config["equals"])
    return where_parts


def _raw_json_expression(source_field: str, column: str, error_kind: str) -> str:
    if not source_field.startswith("raw_json."):
        raise ValueError(f"invalid raw_json param {error_kind}: {source_field}")
    raw_json_path = source_field.removeprefix("raw_json.")
    if not RAW_JSON_FIELD_PATTERN.match(raw_json_path):
        raise ValueError(f"invalid raw_json param {error_kind}: {source_field}")
    return f"JSON_UNQUOTE(JSON_EXTRACT({column}, '$.{raw_json_path}'))"


def _target_join_clause(
    source: RawJsonParamSource,
    source_key_expression: str,
    where_parts: list[str],
    parameters: dict[str, Any],
) -> str:
    if not source.exclude_existing_target:
        return ""
    if source.refresh_before is None:
        where_parts.append("target_data.id IS NULL")
    else:
        where_parts.append("(target_data.id IS NULL OR target_data.updated_at < :refresh_before)")
        parameters["refresh_before"] = source.refresh_before
    parameters["target_api_code"] = source.target_api_code
    return f"""
        LEFT JOIN raw_api_data target_data
          ON target_data.jijia_account_id = :jijia_account_id
         AND target_data.api_code = :target_api_code
         AND target_data.source_primary_key = {source_key_expression}
        """


def _raw_json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, dict) else None
    return value if isinstance(value, dict) else None
