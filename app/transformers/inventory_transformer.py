from typing import Any


def transform_inventory(raw_item: dict[str, Any]) -> dict[str, Any]:
    """库存数据转换占位。

    暂不编造仓库、SKU、可售数等字段映射，避免后续真实接口字段不一致时误导使用方。
    """
    return raw_item
