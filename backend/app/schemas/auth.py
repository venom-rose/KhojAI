import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.app.security.password import validate_password_strength


class UserRegisterIn(BaseModel):
    """Payload for registering a new user account."""

    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password")
    full_name: Optional[str] = Field(None, max_length=150, description="Optional full name")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(msg)
        return v


class UserLoginIn(BaseModel):
    """Payload for user login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="User password")


class UserOut(BaseModel):
    """Public user profile representation (never includes password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """Authentication token response containing access token and user metadata."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Lifetime in seconds")
    user: UserOut


class RefreshTokenIn(BaseModel):
    """Optional payload for explicit refresh token submission in body."""

    refresh_token: Optional[str] = Field(None, description="Optional explicit refresh/session token")


class MessageResponse(BaseModel):
    """Generic status and message response."""

    ok: bool = True
    message: str
