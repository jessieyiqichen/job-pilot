"""Tests for data models."""

import json

from jobpilot.models import Application, Job, JobScore, Profile, now_iso


def test_profile_round_trip():
    p = Profile(
        name="张三",
        raw_text="简历内容",
        structured={"skills": {"languages": ["Python"]}},
        updated_at="2026-01-01",
    )
    d = p.to_dict()
    assert d["name"] == "张三"
    assert json.loads(d["structured"])["skills"]["languages"] == ["Python"]

    restored = Profile.from_row(d)
    assert restored.structured["skills"]["languages"] == ["Python"]


def test_job_round_trip():
    j = Job(
        platform="boss",
        job_id="123",
        title="Python开发",
        company="Test Co",
        salary_min=15000,
        salary_max=25000,
        raw_data={"source": "test"},
    )
    d = j.to_dict()
    assert d["job_id"] == "123"
    assert json.loads(d["raw_data"])["source"] == "test"

    restored = Job.from_row(d)
    assert restored.raw_data["source"] == "test"


def test_job_score_round_trip():
    s = JobScore(
        job_id="123",
        profile_id=1,
        overall_score=8.5,
        highlights=["skill match", "experience match"],
        concerns=["salary low"],
    )
    d = s.to_dict()
    assert json.loads(d["highlights"]) == ["skill match", "experience match"]

    restored = JobScore.from_row(d)
    assert restored.highlights == ["skill match", "experience match"]
    assert restored.overall_score == 8.5


def test_application_round_trip():
    a = Application(
        job_id="123",
        status="applied",
        applied_at="2026-01-01",
        notes="test note",
    )
    d = a.to_dict()
    restored = Application.from_row(d)
    assert restored.status == "applied"
    assert restored.notes == "test note"


def test_now_iso():
    result = now_iso()
    assert len(result) == 19  # "YYYY-MM-DD HH:MM:SS"
    assert "-" in result
    assert ":" in result
