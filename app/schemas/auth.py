"""Authentication request and response schemas."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.core.security import validate_password_strength

StrongPassword = Annotated[
    str,
    Field(min_length=8, max_length=128),
    AfterValidator(validate_password_strength),
]


class LoginRequest(BaseModel):
    """Credentials submitted for JWT authentication."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """JWT access token returned after successful login."""

    access_token: str
    token_type: str = "bearer"
    must_change_password: bool


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
