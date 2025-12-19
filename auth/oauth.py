"""
Google OAuth 2.0 integration for authentication.
"""
import os
import json
from typing import Optional, Dict, Any
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


class GoogleOAuth:
    """Handles Google OAuth 2.0 authentication flow."""

    SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]

    def __init__(self):
        self.client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
        self.client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
        self.redirect_uri = os.environ.get('GOOGLE_OAUTH_REDIRECT_URI', 'http://localhost:8501')

    def is_configured(self) -> bool:
        """Check if OAuth credentials are configured."""
        return bool(self.client_id and self.client_secret)

    def get_client_config(self) -> Dict[str, Any]:
        """Get OAuth client configuration."""
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        flow = Flow.from_client_config(
            self.get_client_config(),
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )

        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'
        )

        return authorization_url

    def get_user_info(self, auth_code: str) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for user information.

        Args:
            auth_code: Authorization code from OAuth callback

        Returns:
            Dictionary with user info (email, google_id, name) or None on failure
        """
        try:
            flow = Flow.from_client_config(
                self.get_client_config(),
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )

            # Exchange code for tokens
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials

            # Verify the ID token
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                self.client_id
            )

            return {
                'email': id_info.get('email'),
                'google_id': id_info.get('sub'),
                'name': id_info.get('name', ''),
                'picture': id_info.get('picture', ''),
                'email_verified': id_info.get('email_verified', False)
            }

        except Exception as e:
            print(f"OAuth error: {e}")
            return None

    def verify_id_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Google ID token.

        Args:
            token: ID token to verify

        Returns:
            Token claims if valid, None otherwise
        """
        try:
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                self.client_id
            )

            # Verify issuer
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return None

            return id_info

        except Exception as e:
            print(f"Token verification error: {e}")
            return None
