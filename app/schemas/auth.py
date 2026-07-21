"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials submitted for JWT authentication."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """JWT access token returned after successful login."""

    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    """Response returned after a successful logout."""

    message: str = "Logged out successfully"


class TokenPayload(BaseModel):
    """Decoded JWT payload fields used inside the application."""

    sub: str
    role: str
    exp: int | None = None
