"""
Utility functions for authentication.
"""
import os
from urllib.parse import urlencode


def get_base_url() -> str:
    """
    Get the base URL for the application.

    Returns:
        Base URL string
    """
    return os.environ.get('APP_BASE_URL', 'http://localhost:8501')


def generate_verification_link(token: str) -> str:
    """
    Generate a full URL for email verification.

    Args:
        token: Verification token

    Returns:
        Full verification URL
    """
    base_url = get_base_url()
    params = urlencode({'verify': token})
    return f"{base_url}?{params}"


def generate_reset_link(token: str) -> str:
    """
    Generate a full URL for password reset.

    Args:
        token: Reset token

    Returns:
        Full reset URL
    """
    base_url = get_base_url()
    params = urlencode({'reset': token})
    return f"{base_url}?{params}"


def sanitize_email(email: str) -> str:
    """
    Sanitize and normalize an email address.

    Args:
        email: Email address to sanitize

    Returns:
        Normalized email address
    """
    return email.strip().lower()
