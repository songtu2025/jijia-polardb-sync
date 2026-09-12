from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class SyncJobCreateRequest(BaseModel):
    """限制手动任务只能选择既有正整数账号和目录接口。"""

    jijia_account_id: int = Field(gt=0)
    api_code: str = Field(min_length=1, max_length=100)
    range_mode: Literal["checkpoint", "custom"] = "checkpoint"
    start_date: date | None = None
    end_date: date | None = None
    market_ids: list[Annotated[int, Field(strict=True, gt=0)]] | None = None
    preview_token: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_range(self) -> "SyncJobCreateRequest":
        if self.range_mode == "custom":
            if self.start_date is None or self.end_date is None:
                raise ValueError("自定义范围必须同时提供开始和结束日期")
            if self.start_date > self.end_date:
                raise ValueError("开始日期不能晚于结束日期")
        elif self.start_date is not None or self.end_date is not None:
            raise ValueError("系统续传模式不能提交自定义日期")
        return self


class SyncJobPreviewRequest(SyncJobCreateRequest):
    """复用创建参数，保证预览与提交采用同一输入契约。"""
