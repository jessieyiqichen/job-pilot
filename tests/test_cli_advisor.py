"""Integration tests for the `advisor` CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.models import Application, Job, JobScore, Profile

runner = CliRunner()


def _db():
    """A mock db wired so diagnose() runs end to end."""
    db = MagicMock()
    db.get_profile.return_value = Profile(
        id=10, structured={"preferences": {"career_track": "AI产品经理"}}
    )
    db.count_jobs_by_status.return_value = {"scored": 30, "applied": 1}
    db.list_top_scored_jobs.return_value = [
        (JobScore(job_id="a", overall_score=8.0), Job(job_id="a", status="scored")),
    ]
    db.list_applications.return_value = [
        Application(job_id="b", status="applied", applied_at="2026-05-27 10:00:00",
                    updated_at="2026-05-27 10:00:00"),
    ]
    return db


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_advisor_shows_diagnosis_and_exports_prompt_without_key(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = ""
    mock_config.DEFAULT_PROFILE_ID = 10
    mock_get_db.return_value = _db()

    result = runner.invoke(app, ["advisor"])

    assert result.exit_code == 0
    assert "求职策略诊断" in result.output   # diagnosis always shown
    assert "未配置 API key" in result.output  # degrade path
    assert "军师" in result.output            # exported prompt


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_advisor_generates_advice_with_key(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_config.DEFAULT_PROFILE_ID = 10
    mock_get_db.return_value = _db()

    with patch("jobpilot.advisor.generate_advice", return_value="本周先把 5 个高分岗投掉"):
        result = runner.invoke(app, ["advisor"])

    assert result.exit_code == 0
    assert "本周先把 5 个高分岗投掉" in result.output


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_advisor_no_profile_exits(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_config.DEFAULT_PROFILE_ID = 10
    db = MagicMock()
    db.get_profile.return_value = None
    mock_get_db.return_value = db

    result = runner.invoke(app, ["advisor"])
    assert result.exit_code == 1
    assert "No profile found" in result.output
