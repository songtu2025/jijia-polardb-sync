from typing import Any


def transform_order(raw_item: dict[str, Any]) -> dict[str, Any]:
    """订单数据转换占位。

    当前没有真实订单字段文档，所以不猜测字段含义，直接返回原始数据。等确认
    积加订单接口字段后，再在这里做字段清洗、重命名或类型转换。
    """
    return raw_item
