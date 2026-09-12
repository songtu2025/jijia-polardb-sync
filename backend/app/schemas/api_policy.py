from datetime import date

from pydantic import BaseModel, Field

from backend.app.models.account_api_policy import ScheduleMode, WindowMode


class ApiPolicyUpdateRequest(BaseModel):
    enabled: bool
    schedule_mode: ScheduleMode
    schedule_expr: str | None = Field(default=None, max_length=100)
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)
    window_mode: WindowMode | None = None
    lookback_days: int | None = Field(default=None, ge=1, le=3650)
    start_date: date | None = None


class ApiPolicyBatchItem(ApiPolicyUpdateRequest):
    api_code: str = Field(min_length=1, max_length=100)


class ApiPolicyBatchUpdateRequest(BaseModel):
    items: list[ApiPolicyBatchItem] = Field(min_length=1, max_length=100)
