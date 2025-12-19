"""
Authentication module for AI Podcast Generator.

Provides user authentication, email verification, and password management.
"""
from .database import (
    init_database,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_password,
    verify_user_email,
    update_last_login,
    create_verification_token,
    get_verification_token,
    consume_verification_token,
    create_reset_token,
    get_reset_token,
    consume_reset_token
)
from .models import User, EmailVerificationToken, PasswordResetToken, UserSession
from .email_service import EmailService
from .security import SecurityManager
from .utils import (
    get_base_url,
    generate_verification_link,
    generate_reset_link,
    sanitize_email
)

__all__ = [
    # Database functions
    'init_database',
    'create_user',
    'get_user_by_email',
    'get_user_by_id',
    'update_user_password',
    'verify_user_email',
    'update_last_login',
    'create_verification_token',
    'get_verification_token',
    'consume_verification_token',
    'create_reset_token',
    'get_reset_token',
    'consume_reset_token',
    # Models
    'User',
    'EmailVerificationToken',
    'PasswordResetToken',
    'UserSession',
    # Classes
    'EmailService',
    'SecurityManager',
    # Utilities
    'get_base_url',
    'generate_verification_link',
    'generate_reset_link',
    'sanitize_email'
]
