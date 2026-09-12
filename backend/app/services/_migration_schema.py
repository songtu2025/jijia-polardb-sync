from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, RowMapping

SchemaRow = RowMapping
IndexSpec = tuple[int, tuple[str, ...]]


def read_information_schema_columns(
    connection: Connection,
    table_names: Sequence[str],
) -> list[RowMapping]:
    """读取指定表的列结构。"""
    table_filter = ", ".join(f"'{table_name}'" for table_name in table_names)
    return list(
        connection.execute(
            text(
                f"""
                SELECT
                  TABLE_NAME AS table_name,
                  COLUMN_NAME AS column_name,
                  DATA_TYPE AS data_type,
                  IS_NULLABLE AS is_nullable,
                  CHARACTER_MAXIMUM_LENGTH AS character_maximum_length,
                  COLUMN_DEFAULT AS column_default,
                  EXTRA AS extra,
                  COLUMN_TYPE AS column_type
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name IN ({table_filter})
                """
            )
        ).mappings()
    )


def read_information_schema_indexes(
    connection: Connection,
    table_names: Sequence[str],
) -> list[RowMapping]:
    """读取指定表的索引列结构。"""
    table_filter = ", ".join(f"'{table_name}'" for table_name in table_names)
    return list(
        connection.execute(
            text(
                f"""
                SELECT
                  TABLE_NAME AS table_name,
                  INDEX_NAME AS index_name,
                  NON_UNIQUE AS non_unique,
                  SEQ_IN_INDEX AS seq_in_index,
                  COLUMN_NAME AS column_name
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name IN ({table_filter})
                """
            )
        ).mappings()
    )


def read_information_schema_tables(
    connection: Connection,
    table_names: Sequence[str],
) -> list[RowMapping]:
    """读取指定表的存储引擎。"""
    table_filter = ", ".join(f"'{table_name}'" for table_name in table_names)
    return list(
        connection.execute(
            text(
                f"""
                SELECT TABLE_NAME AS table_name, ENGINE AS engine
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_name IN ({table_filter})
                """
            )
        ).mappings()
    )


def normalize_column_default(value: Any) -> str | None:
    """统一数据库默认值的等价写法。"""
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"current_timestamp()", "current_timestamp", "now()", "now"}:
        return "current_timestamp"
    return normalized


def bounded_character_length(row: SchemaRow) -> int | None:
    """只校验 CHAR/VARCHAR 的声明长度，TEXT 长度由类型本身约束。"""
    data_type = str(row["data_type"]).lower()
    value = row["character_maximum_length"]
    if data_type not in {"char", "varchar"} or value is None:
        return None
    return int(value)


def normalize_column_data_type(row: SchemaRow) -> str:
    """保留 BIGINT 符号位，避免 signed/unsigned 结构漂移被误放行。"""
    data_type = str(row["data_type"]).lower()
    if data_type == "bigint" and "unsigned" in str(row["column_type"]).lower().split():
        return "bigint unsigned"
    return data_type


def build_index_specs(rows: Iterable[SchemaRow]) -> dict[tuple[str, str], IndexSpec]:
    """按索引列顺序生成稳定且不含业务数据的结构摘要。"""
    grouped: dict[tuple[str, str], list[tuple[int, str, int]]] = {}
    for row in rows:
        key = (str(row["table_name"]), str(row["index_name"]))
        grouped.setdefault(key, []).append(
            (
                int(row["seq_in_index"]),
                str(row["column_name"]),
                int(row["non_unique"]),
            )
        )
    return {
        key: (
            sorted(parts)[0][2],
            tuple(part[1] for part in sorted(parts)),
        )
        for key, parts in grouped.items()
    }
