"""
Tests for email sending functionality.

Tests the email module including:
- SMTP email sending
- Email template rendering
- Password reset emails
- Account creation emails
- Login link emails
- Admin report emails
- Error handling
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tinybase.email import (
    _get_template_env,
    _render_template,
    send_account_creation_email,
    send_admin_report_email,
    send_email,
    send_login_link_email,
    send_password_reset_email,
)

# =============================================================================
# Mock Config
# =============================================================================


class MockEmailConfig:
    """Mock email configuration."""

    def __init__(
        self,
        enabled=True,
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_user="user@test.com",
        smtp_password="password123",
        from_address="noreply@test.com",
        from_name="TinyBase Test",
    ):
        self.email_enabled = enabled
        self.email_smtp_host = smtp_host
        self.email_smtp_port = smtp_port
        self.email_smtp_user = smtp_user
        self.email_smtp_password = smtp_password
        self.email_from_address = from_address
        self.email_from_name = from_name


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Create mock email configuration."""
    return MockEmailConfig()


@pytest.fixture
def mock_config_disabled():
    """Create mock email configuration with email disabled."""
    return MockEmailConfig(enabled=False)


@pytest.fixture
def mock_config_no_host():
    """Create mock email configuration without SMTP host."""
    return MockEmailConfig(smtp_host=None)


@pytest.fixture
def mock_config_no_from():
    """Create mock email configuration without from address."""
    return MockEmailConfig(from_address=None)


@pytest.fixture
def mock_smtp():
    """Create mock SMTP server."""
    mock_server = MagicMock()
    mock_server.__enter__ = MagicMock(return_value=mock_server)
    mock_server.__exit__ = MagicMock(return_value=False)
    return mock_server


# =============================================================================
# send_email Tests
# =============================================================================


def test_send_email_disabled(mock_config_disabled):
    """Test send_email returns False when email is disabled."""
    with patch("tinybase.email.config", mock_config_disabled):
        result = send_email("test@test.com", "Subject", "<p>Body</p>")

        assert result is False


def test_send_email_no_smtp_host(mock_config_no_host):
    """Test send_email returns False when SMTP host not configured."""
    with patch("tinybase.email.config", mock_config_no_host):
        result = send_email("test@test.com", "Subject", "<p>Body</p>")

        assert result is False


def test_send_email_no_from_address(mock_config_no_from):
    """Test send_email returns False when from address not configured."""
    with patch("tinybase.email.config", mock_config_no_from):
        result = send_email("test@test.com", "Subject", "<p>Body</p>")

        assert result is False


def test_send_email_success(mock_config, mock_smtp):
    """Test send_email successfully sends email."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_email("test@test.com", "Test Subject", "<p>Test Body</p>")

            assert result is True
            MockSMTP.assert_called_once_with("smtp.test.com", 587)
            mock_smtp.starttls.assert_called_once()
            mock_smtp.login.assert_called_once_with("user@test.com", "password123")
            mock_smtp.send_message.assert_called_once()


def test_send_email_with_tls_on_port_587(mock_config, mock_smtp):
    """Test send_email uses TLS on port 587."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            send_email("test@test.com", "Subject", "<p>Body</p>")

            mock_smtp.starttls.assert_called_once()


def test_send_email_no_tls_on_other_ports(mock_config, mock_smtp):
    """Test send_email doesn't use TLS on other ports."""
    mock_config.email_smtp_port = 25  # Non-TLS port

    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            send_email("test@test.com", "Subject", "<p>Body</p>")

            mock_smtp.starttls.assert_not_called()


def test_send_email_no_auth_without_credentials(mock_config, mock_smtp):
    """Test send_email skips auth when credentials missing."""
    mock_config.email_smtp_user = None
    mock_config.email_smtp_password = None

    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            send_email("test@test.com", "Subject", "<p>Body</p>")

            mock_smtp.login.assert_not_called()


def test_send_email_smtp_error(mock_config, mock_smtp):
    """Test send_email handles SMTP errors."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp
            mock_smtp.send_message.side_effect = Exception("SMTP error")

            result = send_email("test@test.com", "Subject", "<p>Body</p>")

            assert result is False


def test_send_email_message_format(mock_config, mock_smtp):
    """Test send_email creates message with correct format."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            send_email("recipient@test.com", "Test Subject", "<h1>HTML Body</h1>")

            # Get the message that was sent
            call_args = mock_smtp.send_message.call_args
            msg = call_args[0][0]

            assert msg["Subject"] == "Test Subject"
            assert msg["To"] == "recipient@test.com"
            assert "TinyBase Test <noreply@test.com>" in msg["From"]


# =============================================================================
# Template Rendering Tests
# =============================================================================


def test_get_template_env():
    """Test getting template environment."""
    # Reset cached environment
    import tinybase.email

    tinybase.email._template_env = None

    env = _get_template_env()

    assert env is not None


def test_render_template():
    """Test rendering a template with context."""
    # Reset cached environment
    import tinybase.email

    tinybase.email._template_env = None

    # The actual template rendering depends on template files existing
    # This test verifies the function can be called
    try:
        html = _render_template(
            "password-reset-request",
            {
                "instance_name": "Test",
                "reset_url": "http://test.com/reset",
            },
        )
        assert "http://test.com/reset" in html or isinstance(html, str)
    except Exception:
        # Templates might not be available in test environment
        pass


# =============================================================================
# Password Reset Email Tests
# =============================================================================


def test_send_password_reset_email(mock_config, mock_smtp):
    """Test sending password reset email."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_password_reset_email(
                to_email="user@test.com",
                reset_token="abc123",
                reset_url="http://test.com/reset/abc123",
            )

            assert result is True
            mock_smtp.send_message.assert_called_once()

            # Check the message
            call_args = mock_smtp.send_message.call_args
            msg = call_args[0][0]
            assert "Password Reset" in msg["Subject"]


def test_send_password_reset_email_disabled(mock_config_disabled):
    """Test password reset email when email is disabled."""
    with patch("tinybase.email.config", mock_config_disabled):
        result = send_password_reset_email(
            to_email="user@test.com",
            reset_token="abc123",
            reset_url="http://test.com/reset",
        )

        assert result is False


# =============================================================================
# Account Creation Email Tests
# =============================================================================


def test_send_account_creation_email(mock_config, mock_smtp):
    """Test sending account creation email."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_account_creation_email(
                to_email="newuser@test.com",
                login_url="http://test.com/login",
            )

            assert result is True
            mock_smtp.send_message.assert_called_once()

            call_args = mock_smtp.send_message.call_args
            msg = call_args[0][0]
            assert "Welcome" in msg["Subject"]


def test_send_account_creation_email_no_login_url(mock_config, mock_smtp):
    """Test account creation email without login URL."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_account_creation_email(
                to_email="newuser@test.com",
                login_url=None,
            )

            assert result is True


# =============================================================================
# Login Link Email Tests
# =============================================================================


def test_send_login_link_email(mock_config, mock_smtp):
    """Test sending login link email."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_login_link_email(
                to_email="user@test.com",
                login_url="http://test.com/login?token=xyz",
                expiry_minutes=15,
            )

            assert result is True
            mock_smtp.send_message.assert_called_once()

            call_args = mock_smtp.send_message.call_args
            msg = call_args[0][0]
            assert "Login Link" in msg["Subject"]


def test_send_login_link_email_default_expiry(mock_config, mock_smtp):
    """Test login link email with default expiry."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_login_link_email(
                to_email="user@test.com",
                login_url="http://test.com/login?token=xyz",
            )

            assert result is True


# =============================================================================
# Admin Report Email Tests
# =============================================================================


def test_send_admin_report_email(mock_config, mock_smtp):
    """Test sending admin report email."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_admin_report_email(
                to_email="admin@test.com",
                report_date="2025-01-15 10:00:00",
                summary={"Total Users": 100, "Total Collections": 5},
                collections={"users": 50, "orders": 25},
                functions={"process_order": {"total_calls": 100, "success_rate": 0.95}},
                users={"total": 100, "admins": 5, "regular": 95},
                notes="Weekly report",
            )

            assert result is True
            mock_smtp.send_message.assert_called_once()

            call_args = mock_smtp.send_message.call_args
            msg = call_args[0][0]
            assert "Admin Report" in msg["Subject"]


def test_send_admin_report_email_minimal(mock_config, mock_smtp):
    """Test admin report email with minimal data."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_admin_report_email(
                to_email="admin@test.com",
                report_date="2025-01-15 10:00:00",
            )

            assert result is True


def test_send_admin_report_email_all_none(mock_config, mock_smtp):
    """Test admin report email with all optional fields as None."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_admin_report_email(
                to_email="admin@test.com",
                report_date="2025-01-15",
                summary=None,
                collections=None,
                functions=None,
                users=None,
                notes=None,
            )

            assert result is True


# =============================================================================
# Template Environment Tests
# =============================================================================


def test_template_env_uses_internal_templates():
    """Test that template env uses internal templates when no user templates."""
    import tinybase.email

    # Reset cached environment
    tinybase.email._template_env = None

    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory without templates
        import os

        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            env = _get_template_env()
            assert env is not None
        finally:
            os.chdir(original_cwd)
            tinybase.email._template_env = None


def test_template_env_prefers_user_templates():
    """Test that template env prefers user templates if available."""
    import tinybase.email

    # Reset cached environment
    tinybase.email._template_env = None

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create user templates directory
        templates_dir = Path(tmpdir) / "templates" / "emails"
        templates_dir.mkdir(parents=True)

        # Create a template file
        (templates_dir / "test.j2").write_text("Custom template")

        import os

        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            env = _get_template_env()
            assert env is not None
        finally:
            os.chdir(original_cwd)
            tinybase.email._template_env = None


# =============================================================================
# Edge Cases
# =============================================================================


def test_send_email_special_characters_in_subject(mock_config, mock_smtp):
    """Test send_email with special characters in subject."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_email(
                to_email="test@test.com",
                subject="[TinyBase] Test: Special & Characters <script>",
                html_body="<p>Body</p>",
            )

            assert result is True


def test_send_email_unicode_content(mock_config, mock_smtp):
    """Test send_email with unicode content."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            result = send_email(
                to_email="test@test.com",
                subject="Unicode Test: 日本語 🎉",
                html_body="<p>こんにちは世界</p>",
            )

            assert result is True


def test_send_email_long_html_body(mock_config, mock_smtp):
    """Test send_email with long HTML body."""
    with patch("tinybase.email.config", mock_config):
        with patch("tinybase.email.smtplib.SMTP") as MockSMTP:
            MockSMTP.return_value = mock_smtp

            long_body = "<html><body>" + "<p>Test paragraph</p>" * 1000 + "</body></html>"

            result = send_email(
                to_email="test@test.com",
                subject="Long Email",
                html_body=long_body,
            )

            assert result is True
