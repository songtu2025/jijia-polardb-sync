from pydantic import BaseModel, Field, model_validator


class JijiaAccountCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    app_id: str = Field(min_length=1, max_length=200)
    app_key: str = Field(min_length=1, max_length=500)


class JijiaAccountUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    app_id: str | None = Field(default=None, min_length=1, max_length=200)
    app_key: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def require_app_key_for_new_app_id(self) -> "JijiaAccountUpdateRequest":
        """更换 appId 时必须同时提交与其匹配的新 appKey。"""
        if self.app_id is not None and self.app_key is None:
            raise ValueError("更换 appId 时必须同时提交 appKey")
        if self.name is None and self.app_id is None and self.app_key is None:
            raise ValueError("至少提交一个需要修改的字段")
        return self
