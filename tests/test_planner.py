"""Tests for the weekly application planner (jobpilot plan).

Fully deterministic — no LLM. The plan is computed from the user's data so
every item ("invest in this job, in this order, because X") is defensible.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from jobpilot import config
from jobpilot.models import Application, Job, JobScore
from jobpilot.planner import (
    WeeklyPlan,
    build_weekly_plan,
    format_plan_markdown,
)


def _dt(days_ago: float) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _pair(job_id: str, score: float, status: str):
    return (
        JobScore(job_id=job_id, overall_score=score),
        Job(job_id=job_id, title=f"岗位{job_id}", company=f"公司{job_id}", status=status),
    )


def _mock_db(*, to_apply=None, applications=None):
    db = MagicMock()
    db.list_top_scored_jobs.return_value = to_apply or []
    db.list_applications.return_value = applications or []
    return db


# ----------------------------------------------------------------------
# build_weekly_plan — to-apply list
# ----------------------------------------------------------------------


def test_plan_lists_unapplied_high_score_jobs_sorted():
    # list_top_scored_jobs already sorts by score desc; planner preserves order
    db = _mock_db(to_apply=[_pair("a", 8.5, "tailored"), _pair("b", 7.5, "scored")])
    plan = build_weekly_plan(db, profile_id=10)

    assert [i.job_id for i in plan.to_apply] == ["a", "b"]
    assert plan.to_apply[0].ready is True   # tailored → resume ready
    assert plan.to_apply[1].ready is False  # scored only


def test_plan_caps_at_weekly_target(monkeypatch):
    monkeypatch.setattr(config, "PLAN_WEEKLY_TARGET", 2)
    db = _mock_db(
        to_apply=[_pair("a", 9.0, "scored"), _pair("b", 8.0, "scored"), _pair("c", 7.0, "scored")]
    )
    plan = build_weekly_plan(db, profile_id=10)
    assert len(plan.to_apply) == 2  # capped


def test_plan_queries_unapplied_statuses_only():
    db = _mock_db()
    build_weekly_plan(db, profile_id=10)
    kwargs = db.list_top_scored_jobs.call_args.kwargs
    assert set(kwargs["statuses"]) == {"scored", "tailored"}
    assert kwargs["min_score"] == config.MIN_RECOMMEND_SCORE


def test_plan_item_has_reason():
    db = _mock_db(to_apply=[_pair("a", 8.5, "tailored")])
    plan = build_weekly_plan(db, profile_id=10)
    assert plan.to_apply[0].reason  # non-empty rationale


# ----------------------------------------------------------------------
# build_weekly_plan — follow-ups
# ----------------------------------------------------------------------


def test_plan_follow_ups_from_stale_applications():
    apps = [
        Application(job_id="x", status="applied", applied_at=_dt(10), updated_at=_dt(10)),  # stale
        Application(job_id="y", status="applied", applied_at=_dt(1), updated_at=_dt(1)),    # fresh
    ]
    db = _mock_db(applications=apps)
    db.get_job.return_value = Job(job_id="x", title="老岗位", company="某公司")

    plan = build_weekly_plan(db, profile_id=10)

    assert [f.job_id for f in plan.follow_ups] == ["x"]
    assert plan.follow_ups[0].days_since >= config.FOLLOWUP_STALE_DAYS


# ----------------------------------------------------------------------
# build_weekly_plan — empty / note
# ----------------------------------------------------------------------


def test_plan_empty_to_apply_sets_note():
    db = _mock_db(to_apply=[], applications=[])
    plan = build_weekly_plan(db, profile_id=10)
    assert plan.to_apply == ()
    assert plan.note  # should nudge to search/score more


def test_plan_recent_applied_counted(monkeypatch):
    monkeypatch.setattr(config, "ADVISOR_PACE_DAYS", 7)
    apps = [
        Application(job_id="x", status="applied", applied_at=_dt(2), updated_at=_dt(2)),
        Application(job_id="y", status="applied", applied_at=_dt(20), updated_at=_dt(20)),
    ]
    db = _mock_db(applications=apps)
    db.get_job.return_value = Job(job_id="x", title="t", company="c")
    plan = build_weekly_plan(db, profile_id=10)
    assert plan.recent_applied == 1


# ----------------------------------------------------------------------
# format_plan_markdown
# ----------------------------------------------------------------------


def test_format_markdown_contains_jobs_and_follow_ups():
    db = _mock_db(
        to_apply=[_pair("a", 8.5, "tailored")],
        applications=[Application(job_id="x", status="applied", applied_at=_dt(10), updated_at=_dt(10))],
    )
    db.get_job.return_value = Job(job_id="x", title="老岗位", company="某公司")
    plan = build_weekly_plan(db, profile_id=10)
    md = format_plan_markdown(plan)

    assert "本周投递清单" in md
    assert "岗位a" in md
    assert "跟进" in md
    assert "老岗位" in md


def test_format_markdown_empty_plan_shows_note():
    plan = WeeklyPlan(to_apply=(), follow_ups=(), weekly_target=5, recent_applied=0, note="先去搜索")
    md = format_plan_markdown(plan)
    assert "先去搜索" in md
