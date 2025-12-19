"""
Utility functions for authentication.
"""
import os
from urllib.parse import urlencode


def get_base_url() -> str:
    """
    Get the base URL for the application.
    
    Priority:
    1. APP_BASE_URL environment variable (explicit override)
    2. Auto-detect Cloud Run URL if running on Cloud Run
    3. Fall back to localhost for local development

    Returns:
        Base URL string
    """
    # Check for explicit APP_BASE_URL setting (highest priority)
    explicit_url = os.environ.get('APP_BASE_URL')
    if explicit_url:
        return explicit_url.rstrip('/')
    
    # Check if running on Cloud Run
    k_service = os.environ.get('K_SERVICE')
    if k_service:
        # Cloud Run URLs have a hash that we can't predict automatically
        # The most reliable way is to set APP_BASE_URL explicitly in Cloud Run env vars
        # We'll try to construct a reasonable URL, but it may not be exact
        region = os.environ.get('K_REGION', os.environ.get('REGION', 'us-central1'))
        
        # Try to construct the URL
        # Note: Cloud Run URLs typically have format: https://SERVICE-HASH-REGION.a.run.app
        # Since we can't predict the hash, this is a best-effort attempt
        # For production, set APP_BASE_URL to the exact URL from Cloud Run console
        return f"https://{k_service}.{region}.run.app"
    
    # Fall back to localhost for local development
    return 'http://localhost:8501'


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
