"""
SQLite database operations for authentication.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from .models import User, EmailVerificationToken, PasswordResetToken


# Database path
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'auth.db')


def get_database_path() -> str:
    """Get the database file path."""
    return os.environ.get('DATABASE_PATH', DATABASE_PATH)


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_database_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize database with required tables."""
    os.makedirs(os.path.dirname(get_database_path()), exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                google_id TEXT UNIQUE,
                password_hash TEXT,
                is_email_verified BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Email verification tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Password reset tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_verification_token ON email_verification_tokens(token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reset_token ON password_reset_tokens(token)')

        conn.commit()


# User operations
def create_user(email: str, google_id: Optional[str] = None) -> User:
    """
    Create a new user.

    Args:
        email: User's email address
        google_id: Google OAuth ID (optional)

    Returns:
        Created User object
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO users (email, google_id, created_at)
               VALUES (?, ?, ?)''',
            (email.lower(), google_id, datetime.utcnow())
        )
        conn.commit()

        return get_user_by_email(email)


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email address."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email.lower(),))
        row = cursor.fetchone()

        if row:
            return User(
                id=row['id'],
                email=row['email'],
                google_id=row['google_id'],
                password_hash=row['password_hash'],
                is_email_verified=bool(row['is_email_verified']),
                is_active=bool(row['is_active']),
                created_at=row['created_at'],
                last_login=row['last_login']
            )
        return None


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()

        if row:
            return User(
                id=row['id'],
                email=row['email'],
                google_id=row['google_id'],
                password_hash=row['password_hash'],
                is_email_verified=bool(row['is_email_verified']),
                is_active=bool(row['is_active']),
                created_at=row['created_at'],
                last_login=row['last_login']
            )
        return None


def update_user_password(user_id: int, password_hash: str) -> bool:
    """Update user's password hash."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (password_hash, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def verify_user_email(user_id: int) -> bool:
    """Mark user's email as verified."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET is_email_verified = TRUE WHERE id = ?',
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def update_last_login(user_id: int) -> bool:
    """Update user's last login timestamp."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (datetime.utcnow(), user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


# Email verification token operations
def create_verification_token(user_id: int, token: str, expires_at: datetime) -> bool:
    """Create an email verification token."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Invalidate any existing tokens for this user
        cursor.execute(
            'DELETE FROM email_verification_tokens WHERE user_id = ?',
            (user_id,)
        )
        # Create new token
        cursor.execute(
            '''INSERT INTO email_verification_tokens (user_id, token, expires_at)
               VALUES (?, ?, ?)''',
            (user_id, token, expires_at)
        )
        conn.commit()
        return True


def get_verification_token(token: str) -> Optional[EmailVerificationToken]:
    """Get verification token if valid and unused."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT * FROM email_verification_tokens
               WHERE token = ? AND used_at IS NULL AND expires_at > ?''',
            (token, datetime.utcnow())
        )
        row = cursor.fetchone()

        if row:
            return EmailVerificationToken(
                id=row['id'],
                user_id=row['user_id'],
                token=row['token'],
                expires_at=row['expires_at'],
                used_at=row['used_at']
            )
        return None


def consume_verification_token(token: str) -> bool:
    """Mark verification token as used."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE email_verification_tokens SET used_at = ? WHERE token = ?',
            (datetime.utcnow(), token)
        )
        conn.commit()
        return cursor.rowcount > 0


# Password reset token operations
def create_reset_token(user_id: int, token: str, expires_at: datetime) -> bool:
    """Create a password reset token."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Invalidate any existing tokens for this user
        cursor.execute(
            'DELETE FROM password_reset_tokens WHERE user_id = ?',
            (user_id,)
        )
        # Create new token
        cursor.execute(
            '''INSERT INTO password_reset_tokens (user_id, token, expires_at)
               VALUES (?, ?, ?)''',
            (user_id, token, expires_at)
        )
        conn.commit()
        return True


def get_reset_token(token: str) -> Optional[PasswordResetToken]:
    """Get reset token if valid and unused."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT * FROM password_reset_tokens
               WHERE token = ? AND used_at IS NULL AND expires_at > ?''',
            (token, datetime.utcnow())
        )
        row = cursor.fetchone()

        if row:
            return PasswordResetToken(
                id=row['id'],
                user_id=row['user_id'],
                token=row['token'],
                expires_at=row['expires_at'],
                used_at=row['used_at']
            )
        return None


def consume_reset_token(token: str) -> bool:
    """Mark reset token as used."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE password_reset_tokens SET used_at = ? WHERE token = ?',
            (datetime.utcnow(), token)
        )
        conn.commit()
        return cursor.rowcount > 0
