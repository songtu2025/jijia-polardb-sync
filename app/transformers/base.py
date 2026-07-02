from typing import Any, Protocol


class Transformer(Protocol):
    """结构化转换器协议。

    第一版同步以保存原始 JSON 为主，转换器只是预留扩展点。后续如果需要把
    订单、商品、库存拆进业务宽表，各 transformer 只要实现这个方法即可。
    """

    def transform(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        """把单条原始接口数据转换成结构化字典。"""
        ...
