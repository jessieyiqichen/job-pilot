"""Integration tests for the `plan` CLI command."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.models import Application, Job, JobScore

runner = CliRunner()


def _dt(days_ago: float) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _db():
    db = MagicMock()
    db.list_top_scored_jobs.return_value = [
        (JobScore(job_id="a", overall_score=8.5), Job(job_id="a", title="AI产品实习", company="字节", status="tailored")),
    ]
    db.list_applications.return_value = [
        Application(job_id="x", status="applied", applied_at=_dt(10), updated_at=_dt(10)),
    ]
    db.get_job.return_value = Job(job_id="x", title="老岗位", company="某公司")
    return db


@patch("jobpilot.cli._get_db")
def test_plan_renders_weekly_plan(mock_get_db):
    mock_get_db.return_value = _db()
    result = runner.invoke(app, ["plan"])

    assert result.exit_code == 0
    assert "本周投递计划" in result.output
    assert "AI产品实习" in result.output     # to-apply item
    assert "老岗位" in result.output          # follow-up item


@patch("jobpilot.cli._get_db")
def test_plan_respects_target_option(mock_get_db):
    db = MagicMock()
    db.list_top_scored_jobs.return_value = [
        (JobScore(job_id=f"j{i}", overall_score=9.0 - i),
         Job(job_id=f"j{i}", title=f"岗位{i}", company="C", status="scored"))
        for i in range(5)
    ]
    db.list_applications.return_value = []
    mock_get_db.return_value = db

    result = runner.invoke(app, ["plan", "--target", "2"])
    assert result.exit_code == 0
    # target passed through to the planner
    assert db.list_top_scored_jobs.call_args.kwargs["limit"] == 2
