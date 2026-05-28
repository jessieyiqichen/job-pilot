"""
Daily report generator — summarize job hunting progress as Markdown.

Outputs:
  - New jobs discovered today
  - High-match jobs (score >= threshold)
  - Application status changes
  - Recommended actions
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from jobpilot import config
from jobpilot.db import JobPilotDB
from jobpilot.models import Application, Job, JobScore
from jobpilot.tracker import get_pipeline_summary

logger = logging.getLogger(__name__)


def _cutoff(days: float) -> str:
    """ISO timestamp `days` ago (matches models.now_iso format for string compare)."""
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def find_new_high_score_jobs(
    db: JobPilotDB,
    profile_id: int,
    min_score: float,
    lookback_days: int,
) -> list[tuple[JobScore, Job]]:
    """High-score jobs discovered within the last `lookback_days`.

    Used for the daily digest so re-running the pipeline surfaces only what is
    genuinely new, not the full backlog.
    """
    cutoff = _cutoff(lookback_days)
    pairs = db.list_top_scored_jobs(
        profile_id=profile_id,
        min_score=min_score,
        statuses=("scored", "tailored"),
        limit=200,
    )
    return [(s, j) for s, j in pairs if j.discovered_at and j.discovered_at >= cutoff]


def find_stale_applications(db: JobPilotDB, stale_days: int) -> list[Application]:
    """Applications still in 'applied' with no update for >= `stale_days`.

    These are the ones that need a follow-up nudge — replied/interview/offer/
    rejected are already resolved and intentionally excluded.
    """
    cutoff = _cutoff(stale_days)
    apps = db.list_applications(status="applied")
    return [a for a in apps if a.updated_at and a.updated_at < cutoff]


def generate_daily_report(db: JobPilotDB, profile_id: int = config.DEFAULT_PROFILE_ID) -> str:
    """Generate a Markdown daily report.

    Args:
        db: Database instance
        profile_id: Profile to use for score lookup

    Returns:
        Markdown string
    """
    today = datetime.now().strftime("%Y-%m-%d")
    stats = db.get_stats()
    pipeline = get_pipeline_summary(db)

    sections: list[str] = []

    # Header
    sections.append(f"# JobPilot 日报 — {today}\n")

    # Overview
    sections.append("## 概览\n")
    sections.append(f"| 指标 | 数量 |")
    sections.append(f"|------|------|")
    sections.append(f"| 岗位总数 | {stats['jobs_total']} |")
    sections.append(f"| 已评分 | {stats['jobs_scored']} |")
    sections.append(f"| 平均匹配分 | {stats['avg_score']} |")
    sections.append(f"| 投递记录 | {stats['applications']} |")
    sections.append("")

    # Pipeline
    sections.append("## 投递管道\n")
    sections.append("```")
    status_labels = {
        "new": "新发现",
        "scored": "已评分",
        "tailored": "已定制简历",
        "applied": "已投递",
        "replied": "有回复",
        "interview": "面试中",
        "offer": "Offer",
        "rejected": "已拒绝",
    }
    for status, label in status_labels.items():
        count = pipeline.get(status, 0)
        bar = "█" * count
        sections.append(f"  {label:8s} | {bar} {count}")
    sections.append("```\n")

    # New high-score jobs since last run (digest)
    new_high = find_new_high_score_jobs(
        db,
        profile_id=profile_id,
        min_score=config.MIN_RECOMMEND_SCORE,
        lookback_days=config.NEW_JOB_LOOKBACK_DAYS,
    )
    if new_high:
        sections.append(
            f"## 🆕 新增高分岗位（近 {config.NEW_JOB_LOOKBACK_DAYS} 天，{len(new_high)} 个）\n"
        )
        sections.append("| 评分 | 职位 | 公司 | 城市 |")
        sections.append("|------|------|------|------|")
        for score, job in new_high:
            sections.append(
                f"| {score.overall_score:.1f} | {job.title} | {job.company} | {job.city} |"
            )
        sections.append("")

    # Top matches
    top_scores = db.list_scores_with_jobs(
        profile_id=profile_id,
        min_score=config.MIN_RECOMMEND_SCORE,
        limit=10,
    )
    if top_scores:
        sections.append("## 推荐投递（匹配度 >= {:.0f}）\n".format(config.MIN_RECOMMEND_SCORE))
        sections.append("| 评分 | 职位 | 公司 | 城市 | 薪资 |")
        sections.append("|------|------|------|------|------|")
        for score, job in top_scores:
            salary = f"{job.salary_min // 1000}-{job.salary_max // 1000}K" if job.salary_max else "面议"
            sections.append(
                f"| {score.overall_score:.1f} | {job.title} | {job.company} | {job.city} | {salary} |"
            )
        sections.append("")

    # Recent applications
    recent_apps = db.list_applications()[:10]
    if recent_apps:
        sections.append("## 最近投递\n")
        sections.append("| 岗位ID | 状态 | 更新时间 |")
        sections.append("|--------|------|----------|")
        for app in recent_apps:
            job = db.get_job(app.job_id)
            title = job.title if job else app.job_id
            sections.append(
                f"| {title} | {status_labels.get(app.status, app.status)} | {app.updated_at} |"
            )
        sections.append("")

    # Follow-up reminders: applications gone quiet
    stale_apps = find_stale_applications(db, stale_days=config.FOLLOWUP_STALE_DAYS)
    if stale_apps:
        sections.append(
            f"## ⏰ 待跟进投递（投递 >= {config.FOLLOWUP_STALE_DAYS} 天无回复，{len(stale_apps)} 个）\n"
        )
        sections.append("| 岗位 | 投递时间 | 建议 |")
        sections.append("|------|----------|------|")
        for app in stale_apps:
            job = db.get_job(app.job_id)
            title = job.title if job else app.job_id
            applied = app.applied_at or app.updated_at
            sections.append(f"| {title} | {applied} | 主动跟进或转入下一个 |")
        sections.append("")

    # New unscored jobs
    new_jobs = db.list_jobs(status="new", limit=20)
    if new_jobs:
        sections.append(f"## 待评分岗位（{len(new_jobs)} 个）\n")
        for job in new_jobs[:10]:
            salary = f"{job.salary_min // 1000}-{job.salary_max // 1000}K" if job.salary_max else "面议"
            sections.append(f"- **{job.title}** @ {job.company} ({job.city}, {salary})")
        if len(new_jobs) > 10:
            sections.append(f"- ... 还有 {len(new_jobs) - 10} 个")
        sections.append("")

    # Footer
    sections.append("---")
    sections.append(f"*Generated by JobPilot v0.1.0 at {datetime.now().strftime('%H:%M:%S')}*")

    return "\n".join(sections)


def generate_digest(
    db: JobPilotDB, profile_id: int = config.DEFAULT_PROFILE_ID
) -> tuple[str, str]:
    """Build a concise daily digest for email: new high-score jobs + follow-ups.

    Returns (subject, body). Designed for the scheduled run — short and
    actionable, unlike the full Markdown report.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    new_high = find_new_high_score_jobs(
        db,
        profile_id=profile_id,
        min_score=config.MIN_RECOMMEND_SCORE,
        lookback_days=config.NEW_JOB_LOOKBACK_DAYS,
    )
    stale = find_stale_applications(db, stale_days=config.FOLLOWUP_STALE_DAYS)

    subject = f"JobPilot 日报 {today} — {len(new_high)} 个新高分岗"

    lines: list[str] = [f"JobPilot 日报 — {today}", ""]

    if new_high:
        lines.append(f"🆕 新增高分岗位（近 {config.NEW_JOB_LOOKBACK_DAYS} 天，{len(new_high)} 个）")
        for score, job in new_high:
            salary = (
                f"{job.salary_min // 1000}-{job.salary_max // 1000}K"
                if job.salary_max
                else "面议"
            )
            lines.append(
                f"  [{score.overall_score:.1f}] {job.title} @ {job.company} "
                f"（{job.city}, {salary}）"
            )
    else:
        lines.append("🆕 近期无新增高分岗位。")
    lines.append("")

    if stale:
        lines.append(f"⏰ 待跟进投递（>= {config.FOLLOWUP_STALE_DAYS} 天无回复，{len(stale)} 个）")
        for app in stale:
            job = db.get_job(app.job_id)
            title = job.title if job else app.job_id
            lines.append(f"  {title}（投于 {app.applied_at or app.updated_at}）")
        lines.append("")

    lines.append("—— 下一步：jobpilot list --min-score 7 查看，jobpilot apply 投递")
    return subject, "\n".join(lines)


def save_report(
    db: JobPilotDB,
    output_path: str | None = None,
    profile_id: int = config.DEFAULT_PROFILE_ID,
) -> str:
    """Generate and save daily report.

    Args:
        db: Database instance
        output_path: Where to save. Default: data/report_YYYY-MM-DD.md
        profile_id: Profile to use for score lookup

    Returns:
        Path to the saved report
    """
    report = generate_daily_report(db, profile_id)
    if not output_path:
        today = datetime.now().strftime("%Y-%m-%d")
        output_path = str(config.DATA_DIR / f"report_{today}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("Report saved to %s", output_path)
    return output_path
