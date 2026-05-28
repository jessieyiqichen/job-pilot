"""Integration tests for the `ask` CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.models import Job, JobScore, Profile

runner = CliRunner()


def _db():
    db = MagicMock()
    db.get_profile.return_value = Profile(
        id=10, structured={"preferences": {"career_track": "AI产品经理"}}
    )
    db.count_jobs_by_status.return_value = {"scored": 10}
    db.list_top_scored_jobs.return_value = [
        (JobScore(job_id="a", overall_score=8.0), Job(job_id="a", title="AI产品实习", company="字节")),
    ]
    db.list_applications.return_value = []
    db.get_job.return_value = None
    db.get_score.return_value = None
    return db


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_ask_exports_prompt_without_key(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = ""
    mock_config.DEFAULT_PROFILE_ID = 10
    mock_get_db.return_value = _db()

    result = runner.invoke(app, ["ask", "这个 offer 接不接？"])

    assert result.exit_code == 0
    assert "未配置 API key" in result.output
    assert "这个 offer 接不接？" in result.output  # question in exported prompt


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_ask_answers_with_key(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_config.DEFAULT_PROFILE_ID = 10
    mock_get_db.return_value = _db()

    with patch("jobpilot.ask.answer_question", return_value="先看 deal-breaker，再谈薪资"):
        result = runner.invoke(app, ["ask", "怎么谈薪资？"])

    assert result.exit_code == 0
    assert "先看 deal-breaker，再谈薪资" in result.output


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_ask_no_profile_exits(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_config.DEFAULT_PROFILE_ID = 10
    db = MagicMock()
    db.get_profile.return_value = None
    mock_get_db.return_value = db

    result = runner.invoke(app, ["ask", "随便问"])
    assert result.exit_code == 1
    assert "No profile found" in result.output
