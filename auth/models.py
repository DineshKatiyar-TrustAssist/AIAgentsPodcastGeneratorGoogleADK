"""
Pydantic models for authentication.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class User(BaseModel):
    """User model for database operations."""
    id: Optional[int] = None
    email: EmailStr
    google_id: Optional[str] = None
    password_hash: Optional[str] = None
    is_email_verified: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class EmailVerificationToken(BaseModel):
    """Token for email verification."""
    id: Optional[int] = None
    user_id: int
    token: str
    expires_at: datetime
    used_at: Optional[datetime] = None


class PasswordResetToken(BaseModel):
    """Token for password reset."""
    id: Optional[int] = None
    user_id: int
    token: str
    expires_at: datetime
    used_at: Optional[datetime] = None


class UserSession(BaseModel):
    """User session state for Streamlit."""
    user_id: int
    email: str
    is_authenticated: bool = False
    is_email_verified: bool = False
    has_password: bool = False


class PasswordValidationResult(BaseModel):
    """Result of password validation."""
    is_valid: bool
    message: str = ""
