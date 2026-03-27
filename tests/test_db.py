"""Tests for database layer."""

import tempfile
from pathlib import Path

import pytest

from jobpilot.db import JobPilotDB
from jobpilot.models import Application, Job, JobScore, Profile, now_iso


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return JobPilotDB(db_path=db_path)


class TestProfiles:
    def test_upsert_and_get(self, db):
        p = Profile(name="张三", raw_text="内容", structured={"name": "张三"}, updated_at=now_iso())
        pid = db.upsert_profile(p)
        assert pid == 1

        result = db.get_profile(pid)
        assert result is not None
        assert result.name == "张三"
        assert result.structured["name"] == "张三"

    def test_update_existing(self, db):
        p1 = Profile(name="张三", raw_text="v1", structured={}, updated_at=now_iso())
        pid = db.upsert_profile(p1)

        p2 = Profile(id=pid, name="张三改", raw_text="v2", structured={"v": 2}, updated_at=now_iso())
        db.upsert_profile(p2)

        result = db.get_profile(pid)
        assert result.name == "张三改"
        assert result.structured == {"v": 2}

    def test_list_profiles(self, db):
        db.upsert_profile(Profile(name="A", raw_text="", structured={}, updated_at=now_iso()))
        db.upsert_profile(Profile(name="B", raw_text="", structured={}, updated_at=now_iso()))
        assert len(db.list_profiles()) == 2

    def test_get_nonexistent(self, db):
        assert db.get_profile(999) is None


class TestJobs:
    def _make_job(self, job_id="j1", title="Python开发", company="Test"):
        return Job(
            platform="boss", job_id=job_id, title=title, company=company,
            salary_min=15000, salary_max=25000, city="上海",
            experience="3-5年", education="本科", jd_text="JD内容",
            raw_data={}, discovered_at=now_iso(),
        )

    def test_upsert_and_get(self, db):
        job = self._make_job()
        db.upsert_job(job)

        result = db.get_job("j1")
        assert result is not None
        assert result.title == "Python开发"
        assert result.salary_min == 15000

    def test_upsert_updates(self, db):
        db.upsert_job(self._make_job(title="v1"))
        db.upsert_job(self._make_job(title="v2"))

        result = db.get_job("j1")
        assert result.title == "v2"

    def test_batch_upsert(self, db):
        jobs = [self._make_job(f"j{i}") for i in range(5)]
        count = db.upsert_jobs(jobs)
        assert count == 5
        assert db.count_jobs() == 5

    def test_list_with_filters(self, db):
        db.upsert_job(self._make_job("j1"))
        db.upsert_job(self._make_job("j2"))
        db.update_job_status("j1", "scored")

        assert len(db.list_jobs(status="new")) == 1
        assert len(db.list_jobs(status="scored")) == 1
        assert len(db.list_jobs()) == 2

    def test_count_jobs(self, db):
        db.upsert_job(self._make_job("j1"))
        db.upsert_job(self._make_job("j2"))
        assert db.count_jobs() == 2
        assert db.count_jobs(status="new") == 2


class TestScores:
    def _setup(self, db):
        db.upsert_profile(Profile(name="Test", raw_text="", structured={}, updated_at=now_iso()))
        db.upsert_job(Job(
            platform="boss", job_id="j1", title="Test", company="C",
            discovered_at=now_iso(), raw_data={},
        ))

    def test_upsert_and_get(self, db):
        self._setup(db)
        s = JobScore(
            job_id="j1", profile_id=1, overall_score=8.5,
            skill_match=9.0, experience_match=7.5, salary_match=8.0,
            highlights=["good"], concerns=["meh"], suggestion="apply",
            scored_at=now_iso(),
        )
        db.upsert_score(s)

        result = db.get_score("j1")
        assert result is not None
        assert result.overall_score == 8.5
        assert result.highlights == ["good"]

    def test_list_scores(self, db):
        self._setup(db)
        for jid in ["j2", "j3"]:
            db.upsert_job(Job(platform="boss", job_id=jid, title="T", company="C",
                              discovered_at=now_iso(), raw_data={}))

        db.upsert_score(JobScore(job_id="j1", profile_id=1, overall_score=9.0, scored_at=now_iso()))
        db.upsert_score(JobScore(job_id="j2", profile_id=1, overall_score=6.0, scored_at=now_iso()))
        db.upsert_score(JobScore(job_id="j3", profile_id=1, overall_score=3.0, scored_at=now_iso()))

        high = db.list_scores(min_score=7.0)
        assert len(high) == 1
        assert high[0].overall_score == 9.0


class TestApplications:
    def _setup(self, db):
        db.upsert_job(Job(
            platform="boss", job_id="j1", title="Test", company="C",
            discovered_at=now_iso(), raw_data={},
        ))

    def test_upsert_and_get(self, db):
        self._setup(db)
        app = Application(
            job_id="j1", status="applied",
            applied_at=now_iso(), updated_at=now_iso(),
        )
        db.upsert_application(app)

        result = db.get_application("j1")
        assert result is not None
        assert result.status == "applied"

    def test_list_applications(self, db):
        self._setup(db)
        db.upsert_job(Job(platform="boss", job_id="j2", title="T", company="C",
                          discovered_at=now_iso(), raw_data={}))

        db.upsert_application(Application(job_id="j1", status="applied",
                                          applied_at=now_iso(), updated_at=now_iso()))
        db.upsert_application(Application(job_id="j2", status="interview",
                                          applied_at=now_iso(), updated_at=now_iso()))

        all_apps = db.list_applications()
        assert len(all_apps) == 2

        interview_apps = db.list_applications(status="interview")
        assert len(interview_apps) == 1


class TestStats:
    def test_empty_stats(self, db):
        s = db.get_stats()
        assert s["profiles"] == 0
        assert s["jobs_total"] == 0
        assert s["avg_score"] == 0.0
