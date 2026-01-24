"""
Email sending utilities for TinyBase.

Provides SMTP-based email sending with support for password reset emails.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tinybase.settings import config

logger = logging.getLogger(__name__)

_template_dir_suffix = Path("templates") / "emails"

# Internal template directory (fallback)
_internal_template_dir = Path(__file__).parent.parent / _template_dir_suffix

# Template environment - will be initialized on first use
_template_env: Environment | None = None


def _get_template_env() -> Environment:
    """
    Get or create the template environment.

    Checks for user templates in the current working directory first,
    then falls back to internal templates.

    Returns:
        Jinja2 Environment configured with appropriate template loader
    """
    global _template_env

    if _template_env is not None:
        return _template_env

    # Check for user templates in working directory
    user_template_dir = Path.cwd() / _template_dir_suffix
    template_dirs = []

    if user_template_dir.exists() and any(user_template_dir.glob("*.tpl")):
        # User has custom templates
        template_dirs.append(str(user_template_dir))
        logger.info(f"Using custom email templates from {user_template_dir}")
    else:
        # Fallback to internal templates
        template_dirs.append(str(_internal_template_dir))
        logger.debug(f"Using internal email templates from {_internal_template_dir}")

    # Create environment with fallback loader
    _template_env = Environment(
        loader=FileSystemLoader(template_dirs),
        autoescape=select_autoescape(["html", "xml"], default_for_string=True),
    )

    return _template_env


def _render_template(template_name: str, context: dict) -> str:
    """
    Render an email template with the given context.

    Args:
        template_name: Base name of the template (without extension)
        context: Dictionary of variables to pass to the template

    Returns:
        HTML email body
    """
    env = _get_template_env()
    template = env.get_template(f"{template_name}.tpl")
    return template.render(**context)


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    """
    Send an email using SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body

    Returns:
        True if email was sent successfully, False otherwise
    """

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

        # Add HTML part
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
    instance_name = config.email_from_name

    subject = f"[{instance_name}] Password Reset Request"

    context = {
        "instance_name": instance_name,
        "reset_url": reset_url,
    }

    html_body = _render_template("password-reset-request", context)

    return send_email(to_email, subject, html_body)


def send_account_creation_email(to_email: str, login_url: str | None = None) -> bool:
    """
    Send an account creation welcome email.

    Args:
        to_email: Recipient email address
        login_url: Optional URL to the login page

    Returns:
        True if email was sent successfully, False otherwise
    """
    instance_name = config.email_from_name

    subject = f"Welcome to {instance_name}!"

    context = {
        "instance_name": instance_name,
        "email": to_email,
        "login_url": login_url,
    }

    html_body = _render_template("account-creation", context)

    return send_email(to_email, subject, html_body)


def send_login_link_email(to_email: str, login_url: str, expiry_minutes: int = 15) -> bool:
    """
    Send a login link email.

    Args:
        to_email: Recipient email address
        login_url: Full URL to the login page with token
        expiry_minutes: Number of minutes until the link expires

    Returns:
        True if email was sent successfully, False otherwise
    """
    instance_name = config.email_from_name

    subject = f"[{instance_name}] Login Link"

    context = {
        "instance_name": instance_name,
        "login_url": login_url,
        "expiry_minutes": expiry_minutes,
    }

    html_body = _render_template("login-with-link", context)

    return send_email(to_email, subject, html_body)


def send_admin_report_email(
    to_email: str,
    report_date: str,
    summary: dict | None = None,
    collections: dict | None = None,
    functions: dict | None = None,
    users: dict | None = None,
    notes: str | None = None,
) -> bool:
    """
    Send an admin report email.

    Args:
        to_email: Recipient email address
        report_date: Date/time when the report was generated
        summary: Optional summary metrics dictionary
        collections: Optional dictionary mapping collection names to record counts
        functions: Optional dictionary mapping function names to statistics
        users: Optional dictionary with user statistics (total, admins, regular)
        notes: Optional additional notes to include in the report

    Returns:
        True if email was sent successfully, False otherwise
    """
    instance_name = config.email_from_name

    subject = f"[{instance_name}] Admin Report - {report_date}"

    context = {
        "instance_name": instance_name,
        "report_date": report_date,
        "summary": summary,
        "collections": collections,
        "functions": functions,
        "users": users,
        "notes": notes,
    }

    html_body = _render_template("admin-report", context)

    return send_email(to_email, subject, html_body)
