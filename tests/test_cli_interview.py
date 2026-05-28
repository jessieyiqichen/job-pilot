"""Integration tests for the `interview` CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.ai.interview import InterviewPrep, InterviewQuestion
from jobpilot.cli import app
from jobpilot.models import Job, Profile

runner = CliRunner()


def _db_with_job():
    db = MagicMock()
    db.get_profile.return_value = Profile(id=10, name="J", raw_text="经历")
    db.get_job.return_value = Job(job_id="x", title="AI产品实习", company="字节")
    db.get_score.return_value = None
    return db


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_interview_exports_prompt_without_api_key(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = ""
    mock_get_db.return_value = _db_with_job()

    result = runner.invoke(app, ["interview", "x"])

    assert result.exit_code == 0
    assert "未配置 API key" in result.output
    assert "AI产品实习" in result.output  # prompt contains job title


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_interview_generates_with_api_key(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_get_db.return_value = _db_with_job()
    prep = InterviewPrep(
        job_title="AI产品实习",
        company="字节",
        questions=(InterviewQuestion("行为面", "讲个项目", "用XX经历"),),
        prep_notes="突出技术",
    )

    with patch("jobpilot.ai.interview.generate_interview_prep", return_value=prep):
        result = runner.invoke(app, ["interview", "x"])

    assert result.exit_code == 0
    assert "讲个项目" in result.output
    assert "突出技术" in result.output


@patch("jobpilot.cli._get_db")
@patch("jobpilot.cli.config")
def test_interview_job_not_found(mock_config, mock_get_db):
    mock_config.ANTHROPIC_API_KEY = "key"
    db = MagicMock()
    db.get_profile.return_value = Profile(id=10)
    db.get_job.return_value = None
    mock_get_db.return_value = db

    result = runner.invoke(app, ["interview", "missing"])
    assert result.exit_code == 1
    assert "Job not found" in result.output
