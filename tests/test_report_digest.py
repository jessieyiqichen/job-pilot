"""Tests for daily-report digest helpers: new high-score jobs + follow-up reminders."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from jobpilot.models import Application, Job, JobScore
from jobpilot.report import find_new_high_score_jobs, find_stale_applications


def _dt(days_ago: float) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------------------------------------------------
# find_new_high_score_jobs
# ----------------------------------------------------------------------


def test_find_new_high_score_jobs_filters_by_recency():
    fresh = (JobScore(job_id="a", overall_score=8.0), Job(job_id="a", discovered_at=_dt(0.5)))
    stale = (JobScore(job_id="b", overall_score=9.0), Job(job_id="b", discovered_at=_dt(10)))
    db = MagicMock()
    db.list_top_scored_jobs.return_value = [stale, fresh]  # stale first (higher score)

    result = find_new_high_score_jobs(db, profile_id=10, min_score=7.0, lookback_days=1)

    job_ids = [j.job_id for _, j in result]
    assert job_ids == ["a"]  # only the job discovered within 1 day


def test_find_new_high_score_jobs_empty_when_none_recent():
    old = (JobScore(job_id="b", overall_score=9.0), Job(job_id="b", discovered_at=_dt(30)))
    db = MagicMock()
    db.list_top_scored_jobs.return_value = [old]

    result = find_new_high_score_jobs(db, profile_id=10, min_score=7.0, lookback_days=1)
    assert result == []


def test_find_new_high_score_jobs_passes_min_score_to_db():
    db = MagicMock()
    db.list_top_scored_jobs.return_value = []
    find_new_high_score_jobs(db, profile_id=10, min_score=8.5, lookback_days=2)
    assert db.list_top_scored_jobs.call_args.kwargs["min_score"] == 8.5
    assert db.list_top_scored_jobs.call_args.kwargs["profile_id"] == 10


# ----------------------------------------------------------------------
# find_stale_applications
# ----------------------------------------------------------------------


def test_find_stale_applications_flags_old_applied():
    recent = Application(job_id="a", status="applied", updated_at=_dt(2))
    stale = Application(job_id="b", status="applied", updated_at=_dt(10))
    db = MagicMock()
    db.list_applications.return_value = [recent, stale]

    result = find_stale_applications(db, stale_days=7)

    assert [a.job_id for a in result] == ["b"]
    db.list_applications.assert_called_once_with(status="applied")


def test_find_stale_applications_ignores_blank_timestamp():
    blank = Application(job_id="a", status="applied", updated_at="")
    db = MagicMock()
    db.list_applications.return_value = [blank]
    assert find_stale_applications(db, stale_days=7) == []


def test_find_stale_applications_empty():
    db = MagicMock()
    db.list_applications.return_value = []
    assert find_stale_applications(db, stale_days=7) == []
