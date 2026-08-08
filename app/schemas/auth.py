"""Authentication request and response schemas."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.core.security import validate_password_strength
from app.core.validators import NormalizedEmail

StrongPassword = Annotated[
    str,
    Field(min_length=8, max_length=128),
    AfterValidator(validate_password_strength),
]


class LoginRequest(BaseModel):
    """Credentials submitted for JWT authentication."""

    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Access and refresh credentials returned after login or refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool


class RefreshRequest(BaseModel):
    """Opaque refresh token submitted to rotate a persistent session."""

    refresh_token: str = Field(min_length=1, max_length=512)


class ChangePasswordRequest(BaseModel):
    """Current and replacement credentials for self-service password change."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: StrongPassword


class PasswordChangeResponse(BaseModel):
    """Response returned after changing or resetting a password."""

    message: str = "Password changed successfully"


class LogoutResponse(BaseModel):
    """Response returned after a successful logout."""

    message: str = "Logged out successfully"


class TokenPayload(BaseModel):
    """Decoded JWT payload fields used inside the application."""

    sub: str
    role: str
    exp: int | None = None
    sid: str | None = None
