"""
Strategy advisor (军师).

Two layers, deliberately split:

  1. diagnose():  pure, deterministic crunching of the user's own data into a
     StrategyDiagnosis. Every number traces back to the DB — no LLM, fully
     testable. This is what makes the advice survive a "凭什么这么说" follow-up.

  2. generate_advice(): feeds the diagnosis + the user's preferences to Claude
     to turn the numbers into plain-language advice. Degrades without an API
     key (export the prompt for a manual Claude.ai workflow), mirroring tailor
     / interview.

Honesty guard: when the user has barely applied (< ADVISOR_MIN_APPLICATIONS),
the diagnosis refuses to invent funnel analysis and instead says "先投起来".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from jobpilot import config
from jobpilot.db import JobPilotDB
from jobpilot.models import Profile

logger = logging.getLogger(__name__)

# Job statuses that mean "this job has been applied to" (sent out the door).
_APPLIED_STATUSES = frozenset({"applied", "replied", "interview", "offer", "rejected"})

# Funnel display order + human labels (mirrors tracker state machine).
_FUNNEL: tuple[tuple[str, str], ...] = (
    ("new", "新发现"),
    ("scored", "已评分"),
    ("tailored", "已定制简历"),
    ("applied", "已投递"),
    ("replied", "有回复"),
    ("interview", "面试中"),
    ("offer", "Offer"),
    ("rejected", "已拒绝"),
)

# Statuses to scan when measuring the high-score gap (everything past 'new').
_SCORED_STATUSES: tuple[str, ...] = (
    "scored", "tailored", "applied", "replied", "interview", "offer", "rejected",
)


class AdvisorError(RuntimeError):
    """Raised when advice cannot be generated (e.g. no API key)."""


@dataclass(frozen=True)
class FunnelStage:
    """One stage of the application funnel."""

    status: str
    label: str
    count: int


@dataclass(frozen=True)
class StrategyDiagnosis:
    """Deterministic snapshot of the user's job-hunt state."""

    funnel: tuple[FunnelStage, ...] = field(default_factory=tuple)
    high_score_total: int = 0
    high_score_applied: int = 0
    high_score_tailored: int = 0
    total_applications: int = 0
    stale_count: int = 0
    recent_applied: int = 0
    replied_count: int = 0
    interview_count: int = 0
    offer_count: int = 0
    rejected_count: int = 0
    enough_data: bool = False
    headline: str = ""


def _cutoff(days: float) -> str:
    """ISO timestamp `days` ago (string-comparable with models.now_iso)."""
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _build_headline(d: StrategyDiagnosis) -> str:
    """Rule-based one-line verdict. No LLM — must be defensible from the numbers.

    Priority: honesty guard first (too little data), then the single biggest
    bottleneck. We never invent a funnel story when there's nothing to analyze.
    """
    if d.total_applications == 0:
        if d.high_score_total > 0:
            return (
                f"你还没投任何岗位，但已有 {d.high_score_total} 个高分岗在等。"
                f"先投起来，再谈策略。"
            )
        return "还没有可投的高分岗，也还没开始投。先把搜索+评分跑起来。"

    if not d.enough_data:
        return (
            f"目前只投了 {d.total_applications} 个，样本太少，复盘容易瞎猜。"
            f"本周先把投递做到 {config.ADVISOR_MIN_APPLICATIONS}+ 再看转化。"
        )

    # Enough data — diagnose the single biggest bottleneck.
    positive_replies = d.replied_count + d.interview_count + d.offer_count
    if positive_replies == 0:
        return (
            f"投了 {d.total_applications} 个，0 回复。瓶颈大概率在简历/定位，"
            f"不在投递量——先打磨简历和岗位匹配，别只堆数量。"
        )
    if d.high_score_total and d.high_score_applied < d.high_score_total / 2:
        return (
            f"{d.high_score_total} 个高分岗只投了 {d.high_score_applied} 个，"
            f"高质量机会在漏。优先把高分岗投完，再去够低分岗。"
        )
    if d.stale_count > 0:
        return (
            f"有 {d.stale_count} 个投递停滞超过 {config.FOLLOWUP_STALE_DAYS} 天没动静，"
            f"该主动跟进或转下一个，别干等。"
        )
    return (
        f"节奏正常：投了 {d.total_applications} 个，{positive_replies} 个有正向回音。"
        f"保持节奏，重点提升回复→面试的转化。"
    )


def diagnose(db: JobPilotDB, profile_id: int = config.DEFAULT_PROFILE_ID) -> StrategyDiagnosis:
    """Crunch the user's data into a deterministic StrategyDiagnosis.

    Pure data — no LLM, no network. Every field traces to a DB query so the
    advice built on top can survive a follow-up question.
    """
    # --- Funnel from job-status counts ---
    status_counts = db.count_jobs_by_status()
    funnel = tuple(
        FunnelStage(status=s, label=label, count=status_counts.get(s, 0))
        for s, label in _FUNNEL
    )

    # --- High-score gap ---
    high_pairs = db.list_top_scored_jobs(
        profile_id=profile_id,
        min_score=config.MIN_RECOMMEND_SCORE,
        statuses=_SCORED_STATUSES,
        limit=500,
    )
    high_score_total = len(high_pairs)
    high_score_applied = sum(1 for _, j in high_pairs if j.status in _APPLIED_STATUSES)
    high_score_tailored = sum(1 for _, j in high_pairs if j.status == "tailored")

    # --- Application outcomes / pace / stale (one full scan) ---
    apps = db.list_applications()
    total_applications = len(apps)
    replied_count = sum(1 for a in apps if a.status == "replied")
    interview_count = sum(1 for a in apps if a.status == "interview")
    offer_count = sum(1 for a in apps if a.status == "offer")
    rejected_count = sum(1 for a in apps if a.status == "rejected")

    pace_cutoff = _cutoff(config.ADVISOR_PACE_DAYS)
    recent_applied = sum(1 for a in apps if a.applied_at and a.applied_at >= pace_cutoff)

    stale_cutoff = _cutoff(config.FOLLOWUP_STALE_DAYS)
    stale_count = sum(
        1 for a in apps if a.status == "applied" and a.updated_at and a.updated_at < stale_cutoff
    )

    enough_data = total_applications >= config.ADVISOR_MIN_APPLICATIONS

    d = StrategyDiagnosis(
        funnel=funnel,
        high_score_total=high_score_total,
        high_score_applied=high_score_applied,
        high_score_tailored=high_score_tailored,
        total_applications=total_applications,
        stale_count=stale_count,
        recent_applied=recent_applied,
        replied_count=replied_count,
        interview_count=interview_count,
        offer_count=offer_count,
        rejected_count=rejected_count,
        enough_data=enough_data,
        headline="",
    )
    # headline depends on the rest, so build it last and rebuild the frozen obj
    from dataclasses import replace

    return replace(d, headline=_build_headline(d))


def format_diagnosis_markdown(d: StrategyDiagnosis) -> str:
    """Render the diagnosis as Markdown — works with zero API access."""
    lines = ["# 求职策略诊断", "", f"**{d.headline}**", ""]

    lines.append("## 漏斗")
    lines.append("```")
    for s in d.funnel:
        bar = "█" * min(s.count, 40)
        lines.append(f"  {s.label:10s} | {bar} {s.count}")
    lines.append("```")
    lines.append("")

    lines.append("## 关键信号")
    lines.append("| 信号 | 数值 |")
    lines.append("|------|------|")
    lines.append(
        f"| 高分岗（>= {config.MIN_RECOMMEND_SCORE:.0f}） | "
        f"{d.high_score_total} 个，已投 {d.high_score_applied}，已定制简历 {d.high_score_tailored} |"
    )
    lines.append(f"| 投递总数 | {d.total_applications} |")
    lines.append(
        f"| 回音 | 回复 {d.replied_count} / 面试 {d.interview_count} / "
        f"Offer {d.offer_count} / 被拒 {d.rejected_count} |"
    )
    lines.append(f"| 近 {config.ADVISOR_PACE_DAYS} 天投递 | {d.recent_applied} |")
    lines.append(f"| 停滞待跟进 | {d.stale_count} |")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# Preference keys worth feeding the advisor, with human labels. Key names match
# resume_config.yaml's `preferences` block (the single source of truth).
_PREF_LABELS: tuple[tuple[str, str], ...] = (
    ("career_track", "目标方向"),
    ("job_type", "类型"),
    ("career_stage", "阶段"),
    ("preferred_cities", "城市"),
    ("preferred_industries", "偏好行业"),
    ("priorities", "看重"),
    ("deal_breakers", "deal-breaker"),
    ("core_strengths", "核心能力"),
    ("learning_goals", "学习目标"),
)


def _format_preferences(profile: Profile) -> str:
    """Format the user's preferences for the prompt.

    Source of truth is resume_config.yaml (loaded via scorer._load_preferences).
    profile.structured["preferences"] takes precedence if present so tests stay
    hermetic, but in practice it's empty and we fall back to the YAML config.
    """
    prefs: dict = {}
    if isinstance(profile.structured, dict):
        prefs = profile.structured.get("preferences", {}) or {}
    if not prefs:
        try:
            from jobpilot.ai.scorer import _load_preferences

            prefs = _load_preferences() or {}
        except Exception:  # noqa: BLE001 - config missing/unreadable is non-fatal
            prefs = {}
    if not prefs:
        return "(无明确偏好记录)"
    parts = [f"- {label}: {prefs[key]}" for key, label in _PREF_LABELS if prefs.get(key)]
    return "\n".join(parts) if parts else str(prefs)


ADVISOR_PROMPT = """\
你是一位务实的求职军师，服务对象是一名在校生，目标是 AI 产品经理实习。
下面是 ta 的真实求职数据诊断（每个数字都来自系统记录，不是估算）。
你的任务：基于这些数字给出本周可执行的策略建议。

## 一句话诊断
{headline}

## 数据
- 高分岗（>= {min_score:.0f}）：{high_score_total} 个，已投 {high_score_applied} 个，已定制简历 {high_score_tailored} 个
- 投递总数：{total_applications}
- 回音：回复 {replied} / 面试 {interview} / Offer {offer} / 被拒 {rejected}
- 近 {pace_days} 天投递：{recent_applied}
- 停滞待跟进（投了没动静）：{stale}

## 用户偏好
{preferences}

## 要求
1. 先认可已经做对的部分（如果有），再指出最该改的一件事——只挑最重要的一两个瓶颈，别列十条。
2. 给本周 3-5 个具体动作，每条都要能当天就做（例：「把这 5 个高分岗投掉」而不是「提升匹配度」）。
3. 数据不足时（投递很少）就直说先投起来，不要硬编转化率分析。
4. 讲人话，不堆名词。像一个带过很多人的学长，不像 PPT。
5. 不夸大、不灌鸡汤。被拒多的时候给建设性诊断，不是空安慰。
6. 中文，Markdown，控制在 400 字以内。
"""


def build_advisor_prompt(d: StrategyDiagnosis, profile: Profile) -> str:
    """Build the advisor prompt (pure, testable, no API call)."""
    return ADVISOR_PROMPT.format(
        headline=d.headline,
        min_score=config.MIN_RECOMMEND_SCORE,
        high_score_total=d.high_score_total,
        high_score_applied=d.high_score_applied,
        high_score_tailored=d.high_score_tailored,
        total_applications=d.total_applications,
        replied=d.replied_count,
        interview=d.interview_count,
        offer=d.offer_count,
        rejected=d.rejected_count,
        pace_days=config.ADVISOR_PACE_DAYS,
        recent_applied=d.recent_applied,
        stale=d.stale_count,
        preferences=_format_preferences(profile),
    )


def generate_advice(d: StrategyDiagnosis, profile: Profile) -> str:
    """Turn the diagnosis into plain-language advice via Claude.

    Raises:
        AdvisorError: when no API key is configured (use build_advisor_prompt
            for a manual Claude.ai workflow, or format_diagnosis_markdown for
            the rule-based view).
    """
    if not config.ANTHROPIC_API_KEY:
        raise AdvisorError(
            "未配置 ANTHROPIC_API_KEY。可用 format_diagnosis_markdown 看规则诊断，"
            "或 build_advisor_prompt 导出 prompt 到 Claude.ai。"
        )

    prompt = build_advisor_prompt(d, profile)

    import anthropic

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        logger.exception("Advisor API call failed")
        raise AdvisorError(f"API 调用失败: {exc}") from exc

    return message.content[0].text.strip()
