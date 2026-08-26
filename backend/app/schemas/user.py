from datetime import datetime

from pydantic import BaseModel

from backend.app.models.user import UserRole, UserStatus


class UserView(BaseModel):
    id: int
    email: str
    display_name: str | None
    role: UserRole
    status: UserStatus
    last_login_at: datetime | None
    created_at: datetime


class UserUpdateRequest(BaseModel):
    role: UserRole | None = None
    status: UserStatus | None = None
