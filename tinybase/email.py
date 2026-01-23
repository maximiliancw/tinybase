"""
Email sending utilities for TinyBase.

Provides SMTP-based email sending with support for password reset emails.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from tinybase.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """
    Send an email using SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        text_body: Optional plain text email body

    Returns:
        True if email was sent successfully, False otherwise
    """
    config = settings()

    # Check if email is enabled
    if not config.email_enabled:
        logger.error("Email sending requested but email is not enabled")
        return False

    # Validate SMTP configuration
    if not config.email_smtp_host:
        logger.error("Email enabled but SMTP host not configured")
        return False

    if not config.email_from_address:
        logger.error("Email enabled but from address not configured")
        return False

    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{config.email_from_name} <{config.email_from_address}>"
        msg["To"] = to_email

        # Add text and HTML parts
        if text_body:
            text_part = MIMEText(text_body, "plain")
            msg.attach(text_part)

        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        # Connect to SMTP server
        with smtplib.SMTP(config.email_smtp_host, config.email_smtp_port) as server:
            # Start TLS if using port 587
            if config.email_smtp_port == 587:
                server.starttls()

            # Authenticate if credentials provided
            if config.email_smtp_user and config.email_smtp_password:
                server.login(config.email_smtp_user, config.email_smtp_password)

            # Send email
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True

    except Exception as e:
        logger.error(f"Failed to send email via SMTP: {e}")
        return False


def send_password_reset_email(to_email: str, reset_token: str, reset_url: str) -> bool:
    """
    Send a password reset email.

    Args:
        to_email: Recipient email address
        reset_token: Password reset token
        reset_url: Full URL to the password reset page

    Returns:
        True if email was sent successfully, False otherwise
    """
    config = settings()
    instance_name = config.email_from_name

    subject = f"[{instance_name}] Password Reset Request"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
            .button:hover {{ background-color: #0056b3; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Password Reset Request</h2>
            <p>You requested to reset your password for your {instance_name} account.</p>
            <p>Click the button below to reset your password:</p>
            <a href="{reset_url}" class="button">Reset Password</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #666;">{reset_url}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this password reset, you can safely ignore this email.</p>
            <div class="footer">
                <p>This is an automated message from {instance_name}.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
Password Reset Request

You requested to reset your password for your {instance_name} account.

Click this link to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this password reset, you can safely ignore this email.

This is an automated message from {instance_name}.
    """

    return send_email(to_email, subject, html_body, text_body)
