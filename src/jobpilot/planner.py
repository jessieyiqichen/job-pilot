"""
Weekly application planner (jobpilot plan).

Turns the user's data into a concrete, ordered to-do list: which jobs to apply
to this week (highest-score unapplied first, resume-ready ones flagged) and
which stale applications need a follow-up. Fully deterministic — no LLM — so
every item traces back to the data and survives a "why this one" question.

Complements the advisor: advisor diagnoses *what's wrong*, the plan says
*exactly what to do this week*.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from jobpilot import config
from jobpilot.db import JobPilotDB
from jobpilot.models import now_iso

logger = logging.getLogger(__name__)

_DATE_FMT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class PlanItem:
    """One job to apply to this week."""

    job_id: str
    title: str
    company: str
    score: float
    ready: bool       # resume already tailored?
    reason: str


@dataclass(frozen=True)
class FollowUpItem:
    """A stale application that needs a nudge."""

    job_id: str
    title: str
    days_since: int


@dataclass(frozen=True)
class WeeklyPlan:
    """A deterministic weekly action list."""

    to_apply: tuple[PlanItem, ...] = field(default_factory=tuple)
    follow_ups: tuple[FollowUpItem, ...] = field(default_factory=tuple)
    weekly_target: int = 0
    recent_applied: int = 0
    note: str = ""


def _days_since(iso_str: str) -> int:
    """Whole days between `iso_str` and now (0 if unparseable/blank)."""
    if not iso_str:
        return 0
    try:
        then = datetime.strptime(iso_str, _DATE_FMT)
    except ValueError:
        return 0
    return max(0, (datetime.now() - then).days)


def _reason_for(score: float, ready: bool) -> str:
    """Why this job is on the list / ranked here — defensible from the data."""
    bits = []
    if score >= 8.0:
        bits.append("高分优先")
    if ready:
        bits.append("简历已就绪，今天就能投")
    else:
        bits.append("先 jobpilot tailor 定制简历再投")
    return "，".join(bits)


def build_weekly_plan(
    db: JobPilotDB,
    profile_id: int = config.DEFAULT_PROFILE_ID,
    target: int | None = None,
) -> WeeklyPlan:
    """Compute this week's application plan (pure data, no LLM)."""
    weekly_target = target if target is not None else config.PLAN_WEEKLY_TARGET

    # Unapplied high-score jobs (scored/tailored = not yet sent), score desc.
    pairs = db.list_top_scored_jobs(
        profile_id=profile_id,
        min_score=config.MIN_RECOMMEND_SCORE,
        statuses=("scored", "tailored"),
        limit=max(weekly_target, 1),
    )
    to_apply = tuple(
        PlanItem(
            job_id=j.job_id,
            title=j.title,
            company=j.company,
            score=s.overall_score,
            ready=(j.status == "tailored"),
            reason=_reason_for(s.overall_score, j.status == "tailored"),
        )
        for s, j in pairs[:weekly_target]
    )

    # Follow-ups: 'applied' gone quiet past the stale threshold.
    apps = db.list_applications()
    pace_cutoff_days = config.ADVISOR_PACE_DAYS
    recent_applied = sum(
        1 for a in apps if a.applied_at and _days_since(a.applied_at) <= pace_cutoff_days
    )

    follow_ups_list: list[FollowUpItem] = []
    for a in apps:
        if a.status != "applied":
            continue
        days = _days_since(a.updated_at)
        if days >= config.FOLLOWUP_STALE_DAYS:
            job = db.get_job(a.job_id)
            follow_ups_list.append(
                FollowUpItem(
                    job_id=a.job_id,
                    title=job.title if job else a.job_id,
                    days_since=days,
                )
            )
    follow_ups = tuple(sorted(follow_ups_list, key=lambda f: f.days_since, reverse=True))

    note = ""
    if not to_apply:
        note = (
            "本周没有待投的高分岗了。去 jobpilot search 搜新岗位，"
            "或 jobpilot score 把待评分的岗位评出来。"
        )
    elif recent_applied >= weekly_target:
        note = f"本周已投 {recent_applied} 个，达标了，按下面清单继续保持。"

    return WeeklyPlan(
        to_apply=to_apply,
        follow_ups=follow_ups,
        weekly_target=weekly_target,
        recent_applied=recent_applied,
        note=note,
    )


def format_plan_markdown(plan: WeeklyPlan) -> str:
    """Render the weekly plan as Markdown."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 本周投递计划 — {today}", ""]
    lines.append(
        f"目标：本周投 {plan.weekly_target} 个；近 {config.ADVISOR_PACE_DAYS} 天已投 {plan.recent_applied} 个。"
    )
    lines.append("")

    if plan.note:
        lines.append(f"> {plan.note}")
        lines.append("")

    if plan.to_apply:
        lines.append("## 本周投递清单")
        lines.append("| 评分 | 岗位 | 公司 | 简历 | 怎么做 |")
        lines.append("|------|------|------|------|--------|")
        for it in plan.to_apply:
            ready = "✅ 就绪" if it.ready else "✍️ 待定制"
            lines.append(
                f"| {it.score:.1f} | {it.title} | {it.company} | {ready} | {it.reason} |"
            )
        lines.append("")

    if plan.follow_ups:
        lines.append("## ⏰ 该跟进的投递")
        lines.append("| 岗位 | 投出去几天了 | 建议 |")
        lines.append("|------|--------------|------|")
        for f in plan.follow_ups:
            lines.append(f"| {f.title} | {f.days_since} 天 | 主动问进度，或转下一个别干等 |")
        lines.append("")

    lines.append("---")
    lines.append(f"*生成于 {now_iso()}*")
    return "\n".join(lines).rstrip() + "\n"
