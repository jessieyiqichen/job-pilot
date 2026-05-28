"""
Post-scoring filters: company blacklist + headhunter down-ranking.

Pure, immutable helpers — `apply_company_filters` returns a NEW JobScore with a
capped overall_score and an explanatory concern, never mutating the input.
Borrowed from get_jobs' "blacklist / filter headhunter" idea, kept low-risk:
we down-rank rather than delete, so nothing silently disappears.
"""

from __future__ import annotations

from dataclasses import replace

from jobpilot.models import Job, JobScore

# Markers that suggest a headhunter / agency repost rather than a direct employer
HEADHUNTER_MARKERS: tuple[str, ...] = (
    "猎头",
    "headhunter",
    "head hunter",
    "人才顾问",
    "招聘顾问",
    "代招",
)

BLACKLIST_CAP = 2.0   # hard down-rank: user explicitly doesn't want this company
HEADHUNTER_CAP = 4.0  # soft down-rank: keep visible but below the recommend line


def is_blacklisted(job: Job, blacklist: list[str]) -> bool:
    """True if the job's company matches any blacklist keyword (case-insensitive substring)."""
    if not blacklist:
        return False
    name = (job.company or "").lower()
    return any(kw.strip().lower() in name for kw in blacklist if kw and kw.strip())


def is_headhunter(job: Job) -> bool:
    """True if company/title/JD looks like a headhunter or agency repost."""
    text = f"{job.company or ''} {job.title or ''} {job.jd_text or ''}".lower()
    return any(m in text for m in HEADHUNTER_MARKERS)


def apply_company_filters(
    score: JobScore,
    job: Job,
    blacklist: list[str] | None = None,
    *,
    filter_headhunter: bool = True,
) -> JobScore:
    """Return a (possibly down-ranked) copy of `score` based on blacklist/headhunter.

    Blacklist takes precedence over headhunter. No-op if nothing matches.
    """
    blacklist = blacklist or []
    if is_blacklisted(job, blacklist):
        return replace(
            score,
            overall_score=min(score.overall_score, BLACKLIST_CAP),
            concerns=[*score.concerns, f"黑名单公司: {job.company}"],
        )
    if filter_headhunter and is_headhunter(job):
        return replace(
            score,
            overall_score=min(score.overall_score, HEADHUNTER_CAP),
            concerns=[*score.concerns, "疑似猎头/代招岗位（已降权）"],
        )
    return score
