"""
Security utilities for password hashing and token generation.
"""
import bcrypt
import secrets
import re
from datetime import datetime, timedelta
from typing import Tuple


class SecurityManager:
    """Handles password hashing and token generation."""

    TOKEN_EXPIRY_HOURS = 24  # For email verification
    RESET_TOKEN_EXPIRY_HOURS = 1  # For password reset
    BCRYPT_ROUNDS = 12

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=SecurityManager.BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            password_hash: Stored hash to compare against

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception:
            return False

    @staticmethod
    def generate_token() -> str:
        """
        Generate a cryptographically secure random token.

        Returns:
            URL-safe token string
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def get_verification_token_expiry() -> datetime:
        """Get expiry datetime for email verification tokens."""
        return datetime.utcnow() + timedelta(hours=SecurityManager.TOKEN_EXPIRY_HOURS)

    @staticmethod
    def get_reset_token_expiry() -> datetime:
        """Get expiry datetime for password reset tokens."""
        return datetime.utcnow() + timedelta(hours=SecurityManager.RESET_TOKEN_EXPIRY_HOURS)

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password meets security requirements.

        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            return False, "Password must contain at least one special character"

        return True, "Password meets requirements"
