"""Integration tests for the `followup` CLI command."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from jobpilot import config
from jobpilot.cli import app
from jobpilot.followup import Commitment
from jobpilot.followup_store import load_commitments, save_commitments
from jobpilot.models import Application

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHATS_DIR", tmp_path / "chats")


@patch("jobpilot.cli._get_db")
def test_followup_empty(mock_get_db):
    mock_get_db.return_value = MagicMock()
    result = runner.invoke(app, ["followup"])
    assert result.exit_code == 0
    assert "没有待跟进" in result.output


@patch("jobpilot.cli._get_db")
def test_followup_lists_open(mock_get_db):
    save_commitments(10, [Commitment.new("本周投字节", due_hint="本周")])
    db = MagicMock()
    db.get_application.return_value = None  # not applied → stays open
    mock_get_db.return_value = db

    result = runner.invoke(app, ["followup"])
    assert result.exit_code == 0
    assert "本周投字节" in result.output
    assert "待跟进" in result.output


@patch("jobpilot.cli._get_db")
def test_followup_auto_closes_applied(mock_get_db):
    save_commitments(10, [Commitment.new("投字节", job_id="j1")])
    db = MagicMock()
    db.get_application.return_value = Application(job_id="j1", status="applied")
    mock_get_db.return_value = db

    result = runner.invoke(app, ["followup"])
    assert result.exit_code == 0
    assert "没有待跟进" in result.output  # the only item auto-closed
    assert load_commitments(10)[0].status == "done"


@patch("jobpilot.cli._get_db")
def test_followup_done_marks_status(mock_get_db):
    c = Commitment.new("投字节")
    save_commitments(10, [c])
    mock_get_db.return_value = MagicMock()

    result = runner.invoke(app, ["followup", "--done", c.id])
    assert result.exit_code == 0
    assert load_commitments(10)[0].status == "done"
