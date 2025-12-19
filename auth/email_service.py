"""
Email service for sending verification and notification emails via Gmail SMTP.
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional


class EmailService:
    """Handles email sending via Gmail SMTP."""

    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.environ.get('GMAIL_SENDER_EMAIL', '')
        self.sender_password = os.environ.get('GMAIL_APP_PASSWORD', '')
        self.admin_email = os.environ.get(
            'ADMIN_NOTIFICATION_EMAIL',
            'dinesh.katiyar@trustassist.ai'
        )

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email using Gmail SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text fallback (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.sender_email or not self.sender_password:
            print("Email credentials not configured")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email

            # Add plain text version
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)

            # Add HTML version
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, to_email, msg.as_string())

            return True

        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def send_verification_email(self, to_email: str, verification_link: str) -> bool:
        """
        Send email verification link.

        Args:
            to_email: Recipient email address
            verification_link: Full verification URL

        Returns:
            True if sent successfully
        """
        subject = "Verify your email - AI Podcast Generator"

        html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{
            background-color: #4CAF50;
            color: white;
            padding: 14px 28px;
            text-decoration: none;
            display: inline-block;
            border-radius: 5px;
        }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to AI Podcast Generator!</h1>
        <p>Thank you for signing up. Please verify your email address by clicking the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verification_link}" class="button">Verify Email Address</a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all;">{verification_link}</p>
        <p>This link will expire in 24 hours.</p>
        <div class="footer">
            <p>If you did not create an account, please ignore this email.</p>
        </div>
    </div>
</body>
</html>
'''

        text_content = f'''
Welcome to AI Podcast Generator!

Thank you for signing up. Please verify your email address by clicking the link below:

{verification_link}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.
'''

        return self._send_email(to_email, subject, html_content, text_content)

    def send_password_reset_email(self, to_email: str, reset_link: str) -> bool:
        """
        Send password reset link.

        Args:
            to_email: Recipient email address
            reset_link: Full password reset URL

        Returns:
            True if sent successfully
        """
        subject = "Password Reset - AI Podcast Generator"

        html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{
            background-color: #2196F3;
            color: white;
            padding: 14px 28px;
            text-decoration: none;
            display: inline-block;
            border-radius: 5px;
        }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        .warning {{ color: #f44336; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Password Reset Request</h1>
        <p>We received a request to reset your password. Click the button below to create a new password:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" class="button">Reset Password</a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all;">{reset_link}</p>
        <p class="warning"><strong>This link will expire in 1 hour.</strong></p>
        <div class="footer">
            <p>If you did not request a password reset, please ignore this email. Your password will remain unchanged.</p>
        </div>
    </div>
</body>
</html>
'''

        text_content = f'''
Password Reset Request

We received a request to reset your password. Click the link below to create a new password:

{reset_link}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email. Your password will remain unchanged.
'''

        return self._send_email(to_email, subject, html_content, text_content)

    def send_admin_notification(self, new_user_email: str, google_id: Optional[str] = None) -> bool:
        """
        Send notification to admin about new user registration.

        Args:
            new_user_email: New user's email address
            google_id: User's Google ID (optional)

        Returns:
            True if sent successfully
        """
        subject = "New User Registration - AI Podcast Generator"
        registration_date = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

        html_content = f'''
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .info-box {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>New User Registration</h1>
        <p>A new user has registered for the AI Podcast Generator application.</p>
        <div class="info-box">
            <p><strong>Email:</strong> {new_user_email}</p>
            <p><strong>Registration Date:</strong> {registration_date}</p>
            <p><strong>Google ID:</strong> {google_id or 'N/A'}</p>
        </div>
        <p>This is an automated notification.</p>
    </div>
</body>
</html>
'''

        text_content = f'''
New User Registration

A new user has registered for the AI Podcast Generator application.

Email: {new_user_email}
Registration Date: {registration_date}
Google ID: {google_id or 'N/A'}

This is an automated notification.
'''

        return self._send_email(self.admin_email, subject, html_content, text_content)
