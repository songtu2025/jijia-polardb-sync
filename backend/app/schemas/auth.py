from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from backend.app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class InvitationValidateRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)


class RegisterRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetValidateRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)


class PasswordResetCompleteRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)
    new_password: str = Field(min_length=1, max_length=200)


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role: UserRole


class InvitationView(BaseModel):
    id: int
    email: str
    role: UserRole
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None


class InvitationValidationView(BaseModel):
    email: str
    role: UserRole
    expires_at: datetime
