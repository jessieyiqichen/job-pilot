"""Tests for the advisor demo snapshot serializer (baked into the web demo)."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from jobpilot.demo_export import advisor_snapshot
from jobpilot.models import Application, Job, JobScore


def _dt(days_ago: float) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _pair(job_id: str, score: float, status: str):
    return (
        JobScore(job_id=job_id, overall_score=score),
        Job(job_id=job_id, title=f"岗位{job_id}", company=f"公司{job_id}", status=status),
    )


def _mock_db(*, status_counts=None, high_pairs=None, applications=None):
    db = MagicMock()
    db.count_jobs_by_status.return_value = status_counts or {"scored": 30}
    db.list_top_scored_jobs.return_value = high_pairs or []
    db.list_applications.return_value = applications or []
    db.get_job.return_value = Job(job_id="x", title="老岗位", company="某公司")
    return db


def test_snapshot_has_expected_top_level_keys():
    db = _mock_db(high_pairs=[_pair("a", 8.0, "tailored")])
    snap = advisor_snapshot(db, profile_id=10)

    for key in ("headline", "funnel", "signals", "plan", "advice", "generated_at"):
        assert key in snap


def test_snapshot_funnel_is_label_count_list():
    db = _mock_db(status_counts={"scored": 30, "applied": 2})
    snap = advisor_snapshot(db, profile_id=10)
    assert isinstance(snap["funnel"], list)
    assert all("label" in s and "count" in s for s in snap["funnel"])


def test_snapshot_signals_reflect_data():
    db = _mock_db(high_pairs=[_pair("a", 8.5, "scored"), _pair("b", 7.5, "applied")])
    snap = advisor_snapshot(db, profile_id=10)
    assert snap["signals"]["high_score_total"] == 2
    assert snap["signals"]["high_score_applied"] == 1


def test_snapshot_plan_serialized():
    db = _mock_db(high_pairs=[_pair("a", 8.5, "tailored")])
    snap = advisor_snapshot(db, profile_id=10)
    plan = snap["plan"]
    assert plan["to_apply"][0]["title"] == "岗位a"
    assert plan["to_apply"][0]["ready"] is True
    assert "weekly_target" in plan


def test_snapshot_includes_advice_when_given():
    db = _mock_db()
    snap = advisor_snapshot(db, profile_id=10, advice="本周先投 5 个")
    assert snap["advice"] == "本周先投 5 个"


def test_snapshot_is_json_serializable():
    import json

    db = _mock_db(
        high_pairs=[_pair("a", 8.0, "tailored")],
        applications=[Application(job_id="x", status="applied", applied_at=_dt(10), updated_at=_dt(10))],
    )
    snap = advisor_snapshot(db, profile_id=10)
    # must round-trip cleanly — it gets written to web/demo-data/advisor.json
    assert json.loads(json.dumps(snap, ensure_ascii=False))
