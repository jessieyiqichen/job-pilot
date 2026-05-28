"""Tests for generate_digest (email body builder)."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from jobpilot.models import Application, Job, JobScore
from jobpilot.report import generate_digest


def _dt(days_ago: float) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


@patch("jobpilot.report.find_stale_applications")
@patch("jobpilot.report.find_new_high_score_jobs")
def test_digest_lists_new_jobs(mock_new, mock_stale):
    mock_new.return_value = [
        (JobScore(job_id="a", overall_score=8.5), Job(job_id="a", title="AI产品实习", company="字节", city="上海")),
    ]
    mock_stale.return_value = []
    db = MagicMock()

    subject, body = generate_digest(db, profile_id=10)

    assert "1 个新高分岗" in subject
    assert "AI产品实习" in body
    assert "字节" in body
    assert "8.5" in body


@patch("jobpilot.report.find_stale_applications")
@patch("jobpilot.report.find_new_high_score_jobs")
def test_digest_handles_no_new_jobs(mock_new, mock_stale):
    mock_new.return_value = []
    mock_stale.return_value = []
    db = MagicMock()

    subject, body = generate_digest(db, profile_id=10)

    assert "0 个新高分岗" in subject
    assert "无新增高分岗位" in body


@patch("jobpilot.report.find_stale_applications")
@patch("jobpilot.report.find_new_high_score_jobs")
def test_digest_includes_followups(mock_new, mock_stale):
    mock_new.return_value = []
    mock_stale.return_value = [Application(job_id="b", status="applied", applied_at=_dt(10))]
    db = MagicMock()
    db.get_job.return_value = Job(job_id="b", title="产品经理", company="腾讯")

    subject, body = generate_digest(db, profile_id=10)

    assert "待跟进投递" in body
    assert "产品经理" in body
