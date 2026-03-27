"""Tests for application tracker."""

import pytest

from jobpilot.db import JobPilotDB
from jobpilot.models import Application, Job, now_iso
from jobpilot.tracker import TrackerError, get_pipeline_summary, update_status, validate_transition


@pytest.fixture
def db(tmp_path):
    d = JobPilotDB(db_path=tmp_path / "test.db")
    d.upsert_job(Job(
        platform="boss", job_id="j1", title="Test Job", company="C",
        discovered_at=now_iso(), raw_data={},
    ))
    return d


class TestTransitions:
    def test_valid_transitions(self):
        assert validate_transition("new", "scored")
        assert validate_transition("scored", "applied")
        assert validate_transition("applied", "interview")
        assert validate_transition("interview", "offer")
        assert validate_transition("applied", "rejected")

    def test_invalid_transitions(self):
        assert not validate_transition("new", "offer")
        assert not validate_transition("offer", "applied")
        assert not validate_transition("rejected", "applied")

    def test_any_to_rejected(self):
        for status in ["new", "scored", "tailored", "applied", "replied", "interview"]:
            assert validate_transition(status, "rejected")


class TestUpdateStatus:
    def test_first_update(self, db):
        app = update_status(db, "j1", "applied")
        assert app.status == "applied"
        assert db.get_application("j1") is not None

    def test_valid_sequence(self, db):
        update_status(db, "j1", "applied")
        update_status(db, "j1", "interview")
        app = update_status(db, "j1", "offer")
        assert app.status == "offer"

    def test_invalid_transition_raises(self, db):
        update_status(db, "j1", "applied")
        with pytest.raises(TrackerError, match="Cannot transition"):
            update_status(db, "j1", "offer")

    def test_unknown_job_raises(self, db):
        with pytest.raises(TrackerError, match="not found"):
            update_status(db, "nonexistent", "applied")


class TestPipelineSummary:
    def test_empty_pipeline(self, db):
        summary = get_pipeline_summary(db)
        assert all(v == 0 for v in summary.values())
