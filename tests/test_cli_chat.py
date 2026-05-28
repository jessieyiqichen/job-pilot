"""Integration test for the `chat` CLI command (thin wrapper over run_chat)."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.chat import ChatError
from jobpilot.cli import app

runner = CliRunner()


@patch("jobpilot.cli._get_db")
@patch("jobpilot.chat.run_chat")
def test_chat_invokes_run_chat(mock_run_chat, mock_get_db):
    mock_get_db.return_value = MagicMock()
    result = runner.invoke(app, ["chat"])
    assert result.exit_code == 0
    mock_run_chat.assert_called_once()


@patch("jobpilot.cli._get_db")
@patch("jobpilot.chat.run_chat", side_effect=ChatError("未配置 ANTHROPIC_API_KEY"))
def test_chat_reports_missing_key(mock_run_chat, mock_get_db):
    mock_get_db.return_value = MagicMock()
    result = runner.invoke(app, ["chat"])
    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output
