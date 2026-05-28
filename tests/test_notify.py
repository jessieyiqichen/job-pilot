"""Tests for SMTP email delivery (notify.py)."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot import notify


@patch("jobpilot.notify.config")
def test_is_configured_true_when_creds_present(mock_config):
    mock_config.SMTP_USER = "me@gmail.com"
    mock_config.SMTP_PASSWORD = "app-password"
    assert notify.is_configured() is True


@patch("jobpilot.notify.config")
def test_is_configured_false_when_missing(mock_config):
    mock_config.SMTP_USER = "me@gmail.com"
    mock_config.SMTP_PASSWORD = ""
    assert notify.is_configured() is False


@patch("jobpilot.notify.config")
def test_send_email_raises_when_not_configured(mock_config):
    mock_config.SMTP_USER = ""
    mock_config.SMTP_PASSWORD = ""
    with pytest.raises(notify.EmailNotConfigured):
        notify.send_email("subj", "body")


@patch("jobpilot.notify.smtplib.SMTP")
@patch("jobpilot.notify.config")
def test_send_email_uses_starttls_and_login(mock_config, mock_smtp):
    mock_config.SMTP_USER = "me@gmail.com"
    mock_config.SMTP_PASSWORD = "app-password"
    mock_config.SMTP_TO = ""
    mock_config.SMTP_HOST = "smtp.gmail.com"
    mock_config.SMTP_PORT = 587
    server = mock_smtp.return_value.__enter__.return_value

    recipient = notify.send_email("Hello", "Body text")

    assert recipient == "me@gmail.com"  # defaults to SMTP_USER
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("me@gmail.com", "app-password")
    server.sendmail.assert_called_once()
    args = server.sendmail.call_args[0]
    assert args[0] == "me@gmail.com"
    assert args[1] == ["me@gmail.com"]


@patch("jobpilot.notify.smtplib.SMTP")
@patch("jobpilot.notify.config")
def test_send_email_explicit_recipient_and_to_config(mock_config, mock_smtp):
    mock_config.SMTP_USER = "me@gmail.com"
    mock_config.SMTP_PASSWORD = "pw"
    mock_config.SMTP_TO = "fallback@x.com"
    mock_config.SMTP_HOST = "smtp.gmail.com"
    mock_config.SMTP_PORT = 587

    # explicit `to` wins over SMTP_TO
    recipient = notify.send_email("s", "b", to="boss@x.com")
    assert recipient == "boss@x.com"
