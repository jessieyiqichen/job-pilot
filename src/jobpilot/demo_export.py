"""
Serialize the strategy advisor + weekly plan into a static JSON snapshot for
the web demo.

The web dashboard is a Next.js static site and cannot call the Python advisor.
So at demo-refresh time we run the (deterministic) diagnosis + plan here and
dump them to web/demo-data/advisor.json, which the demo renders read-only. The
single source of truth stays in advisor.py / planner.py.
"""

from __future__ import annotations

from typing import Any

from jobpilot import config
from jobpilot.advisor import diagnose
from jobpilot.db import JobPilotDB
from jobpilot.models import now_iso
from jobpilot.planner import build_weekly_plan


def advisor_snapshot(
    db: JobPilotDB,
    profile_id: int = config.DEFAULT_PROFILE_ID,
    advice: str = "",
) -> dict[str, Any]:
    """Build a JSON-serializable snapshot of the advisor diagnosis + weekly plan.

    `advice` (the LLM narrative) is optional — generated upstream only when an
    API key is available; the diagnosis and plan are always present.
    """
    d = diagnose(db, profile_id)
    plan = build_weekly_plan(db, profile_id)

    return {
        "headline": d.headline,
        "funnel": [{"label": s.label, "count": s.count} for s in d.funnel],
        "signals": {
            "high_score_total": d.high_score_total,
            "high_score_applied": d.high_score_applied,
            "high_score_tailored": d.high_score_tailored,
            "total_applications": d.total_applications,
            "replied": d.replied_count,
            "interview": d.interview_count,
            "offer": d.offer_count,
            "rejected": d.rejected_count,
            "recent_applied": d.recent_applied,
            "stale": d.stale_count,
        },
        "plan": {
            "weekly_target": plan.weekly_target,
            "recent_applied": plan.recent_applied,
            "note": plan.note,
            "to_apply": [
                {
                    "title": i.title,
                    "company": i.company,
                    "score": i.score,
                    "ready": i.ready,
                    "reason": i.reason,
                }
                for i in plan.to_apply
            ],
            "follow_ups": [
                {"title": f.title, "days_since": f.days_since} for f in plan.follow_ups
            ],
        },
        "advice": advice or "",
        "generated_at": now_iso(),
    }
