"""Tests for the strategy advisor (军师).

Two layers:
  - diagnose():  deterministic data crunching — the bulk of the tests, mocked db
  - generate_advice(): LLM layer — only assert the degrade-without-key contract
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from jobpilot import config
from jobpilot.advisor import (
    AdvisorError,
    StrategyDiagnosis,
    _format_preferences,
    build_advisor_prompt,
    diagnose,
    format_diagnosis_markdown,
    generate_advice,
)
from jobpilot.models import Application, Job, JobScore, Profile


def _dt(days_ago: float) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _pair(job_id: str, score: float, status: str):
    """A (JobScore, Job) tuple as returned by list_top_scored_jobs."""
    return (
        JobScore(job_id=job_id, overall_score=score),
        Job(job_id=job_id, title=f"岗位{job_id}", company=f"公司{job_id}", status=status),
    )


def _mock_db(
    *,
    status_counts: dict[str, int] | None = None,
    high_pairs: list | None = None,
    applications: list[Application] | None = None,
) -> MagicMock:
    db = MagicMock()
    db.count_jobs_by_status.return_value = status_counts or {}
    db.list_top_scored_jobs.return_value = high_pairs or []
    db.list_applications.return_value = applications or []
    return db


# ----------------------------------------------------------------------
# diagnose — data threshold / honesty guard
# ----------------------------------------------------------------------


def test_diagnose_zero_applications_says_start_applying():
    db = _mock_db(
        status_counts={"scored": 30, "tailored": 2},
        high_pairs=[_pair("a", 8.0, "scored"), _pair("b", 7.5, "tailored")],
        applications=[],
    )
    d = diagnose(db, profile_id=10)

    assert d.total_applications == 0
    assert d.enough_data is False
    assert d.high_score_total == 2
    assert d.high_score_applied == 0
    # headline must push to start, not invent funnel analysis
    assert "投" in d.headline


def test_diagnose_below_threshold_is_not_enough_data():
    apps = [Application(job_id="a", status="applied", applied_at=_dt(1), updated_at=_dt(1))]
    db = _mock_db(status_counts={"applied": 1}, applications=apps)
    d = diagnose(db, profile_id=10)
    assert d.total_applications == 1
    assert d.enough_data is False  # 1 < ADVISOR_MIN_APPLICATIONS (5)


def test_diagnose_enough_data_when_threshold_met(monkeypatch):
    monkeypatch.setattr(config, "ADVISOR_MIN_APPLICATIONS", 3)
    apps = [
        Application(job_id=f"j{i}", status="applied", applied_at=_dt(1), updated_at=_dt(1))
        for i in range(3)
    ]
    db = _mock_db(status_counts={"applied": 3}, applications=apps)
    d = diagnose(db, profile_id=10)
    assert d.enough_data is True


# ----------------------------------------------------------------------
# diagnose — high-score gap
# ----------------------------------------------------------------------


def test_diagnose_counts_high_score_gap():
    high_pairs = [
        _pair("a", 8.5, "scored"),     # not applied
        _pair("b", 8.0, "tailored"),   # tailored, not applied
        _pair("c", 7.5, "applied"),    # applied
        _pair("d", 7.2, "rejected"),   # applied then rejected — still counts as applied
    ]
    db = _mock_db(high_pairs=high_pairs)
    d = diagnose(db, profile_id=10)

    assert d.high_score_total == 4
    assert d.high_score_applied == 2  # c + d
    assert d.high_score_tailored == 1  # b only (a is still scored)


def test_diagnose_passes_min_recommend_score_to_db():
    db = _mock_db()
    diagnose(db, profile_id=10)
    kwargs = db.list_top_scored_jobs.call_args.kwargs
    assert kwargs["min_score"] == config.MIN_RECOMMEND_SCORE
    assert kwargs["profile_id"] == 10


# ----------------------------------------------------------------------
# diagnose — reply / outcome counts
# ----------------------------------------------------------------------


def test_diagnose_no_replies_headline(monkeypatch):
    monkeypatch.setattr(config, "ADVISOR_MIN_APPLICATIONS", 3)
    apps = [
        Application(job_id=f"j{i}", status="applied", applied_at=_dt(3), updated_at=_dt(3))
        for i in range(6)
    ]
    db = _mock_db(status_counts={"applied": 6}, applications=apps)
    d = diagnose(db, profile_id=10)

    assert d.total_applications == 6
    assert d.replied_count == 0
    assert d.interview_count == 0
    # 6 applied, 0 reply → bottleneck is resume/positioning
    assert "回" in d.headline or "简历" in d.headline


def test_diagnose_counts_outcomes():
    apps = [
        Application(job_id="a", status="applied", applied_at=_dt(1), updated_at=_dt(1)),
        Application(job_id="b", status="replied", applied_at=_dt(2), updated_at=_dt(1)),
        Application(job_id="c", status="interview", applied_at=_dt(3), updated_at=_dt(1)),
        Application(job_id="d", status="offer", applied_at=_dt(4), updated_at=_dt(1)),
        Application(job_id="e", status="rejected", applied_at=_dt(5), updated_at=_dt(1)),
    ]
    db = _mock_db(applications=apps)
    d = diagnose(db, profile_id=10)

    assert d.total_applications == 5
    assert d.replied_count == 1
    assert d.interview_count == 1
    assert d.offer_count == 1
    assert d.rejected_count == 1


# ----------------------------------------------------------------------
# diagnose — stale + recent pace
# ----------------------------------------------------------------------


def test_diagnose_counts_stale_applications():
    apps = [
        Application(job_id="a", status="applied", applied_at=_dt(20), updated_at=_dt(20)),  # stale
        Application(job_id="b", status="applied", applied_at=_dt(1), updated_at=_dt(1)),    # fresh
        Application(job_id="c", status="replied", applied_at=_dt(30), updated_at=_dt(30)),  # replied, excluded
    ]
    db = _mock_db(applications=apps)
    d = diagnose(db, profile_id=10)
    assert d.stale_count == 1  # only the old 'applied' one


def test_diagnose_counts_recent_pace(monkeypatch):
    monkeypatch.setattr(config, "ADVISOR_PACE_DAYS", 7)
    apps = [
        Application(job_id="a", status="applied", applied_at=_dt(2), updated_at=_dt(2)),
        Application(job_id="b", status="applied", applied_at=_dt(3), updated_at=_dt(3)),
        Application(job_id="c", status="applied", applied_at=_dt(20), updated_at=_dt(20)),
    ]
    db = _mock_db(applications=apps)
    d = diagnose(db, profile_id=10)
    assert d.recent_applied == 2  # a + b within 7 days


# ----------------------------------------------------------------------
# funnel
# ----------------------------------------------------------------------


def test_diagnose_builds_funnel_from_status_counts():
    counts = {"new": 100, "scored": 30, "tailored": 5, "applied": 3, "rejected": 1}
    db = _mock_db(status_counts=counts)
    d = diagnose(db, profile_id=10)

    funnel = {s.status: s.count for s in d.funnel}
    assert funnel["scored"] == 30
    assert funnel["applied"] == 3
    # every stage has a human label
    assert all(s.label for s in d.funnel)


# ----------------------------------------------------------------------
# format_diagnosis_markdown — rule-based, no API
# ----------------------------------------------------------------------


def test_format_markdown_contains_key_numbers():
    db = _mock_db(
        status_counts={"scored": 30, "applied": 2},
        high_pairs=[_pair("a", 8.0, "scored"), _pair("b", 7.5, "applied")],
        applications=[Application(job_id="b", status="applied", applied_at=_dt(1), updated_at=_dt(1))],
    )
    d = diagnose(db, profile_id=10)
    md = format_diagnosis_markdown(d)

    assert d.headline in md
    assert "高分岗" in md
    assert "漏斗" in md


# ----------------------------------------------------------------------
# build_advisor_prompt — feeds diagnosis + preferences to LLM
# ----------------------------------------------------------------------


def test_build_prompt_includes_diagnosis_and_prefs():
    d = StrategyDiagnosis(
        funnel=(),
        high_score_total=37,
        high_score_applied=0,
        high_score_tailored=2,
        total_applications=0,
        stale_count=0,
        recent_applied=0,
        replied_count=0,
        interview_count=0,
        offer_count=0,
        rejected_count=0,
        enough_data=False,
        headline="还没开始投",
    )
    profile = Profile(
        id=10,
        structured={"preferences": {"career_track": "AI产品经理", "cities": ["上海"]}},
    )
    prompt = build_advisor_prompt(d, profile)

    assert "37" in prompt          # high-score total
    assert "还没开始投" in prompt   # headline
    assert "AI产品经理" in prompt or "上海" in prompt  # prefs fed in


# ----------------------------------------------------------------------
# _format_preferences — source precedence
# ----------------------------------------------------------------------


def test_format_preferences_uses_profile_structured_first():
    profile = Profile(
        id=10, structured={"preferences": {"career_track": "AI产品经理", "deal_breakers": ["996"]}}
    )
    out = _format_preferences(profile)
    assert "AI产品经理" in out
    assert "996" in out


def test_format_preferences_falls_back_to_config(monkeypatch):
    # Empty profile → must fall back to resume_config.yaml loader
    monkeypatch.setattr(
        "jobpilot.ai.scorer._load_preferences",
        lambda: {"career_track": ["AI产品经理"], "preferred_cities": ["上海"]},
    )
    out = _format_preferences(Profile(id=10, structured={}))
    assert "AI产品经理" in out
    assert "上海" in out


# ----------------------------------------------------------------------
# generate_advice — degrade-without-key contract
# ----------------------------------------------------------------------


def test_generate_advice_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    d = StrategyDiagnosis(
        funnel=(),
        high_score_total=0,
        high_score_applied=0,
        high_score_tailored=0,
        total_applications=0,
        stale_count=0,
        recent_applied=0,
        replied_count=0,
        interview_count=0,
        offer_count=0,
        rejected_count=0,
        enough_data=False,
        headline="x",
    )
    with pytest.raises(AdvisorError):
        generate_advice(d, Profile(id=10))
