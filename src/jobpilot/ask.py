"""
Conversational advisor (jobpilot ask).

Answers free-form job-hunt questions ("这个 offer 接不接", "薪资怎么谈",
"HR 这样回我怎么办") grounded in the user's REAL situation — their funnel
diagnosis, preferences, and high-score jobs — not generic advice. Optionally
pins to a specific job (--job) to fold in its JD + AI score.

This is what separates it from "open another ChatGPT tab": the model answers
knowing what the user has actually done and what they actually want.

Degrades without an API key: export the prompt for a manual Claude.ai workflow.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from jobpilot import config
from jobpilot.advisor import StrategyDiagnosis, _format_preferences, diagnose
from jobpilot.db import JobPilotDB
from jobpilot.models import Job, JobScore, Profile

logger = logging.getLogger(__name__)


class AskError(RuntimeError):
    """Raised when an answer cannot be generated (e.g. no API key)."""


@dataclass(frozen=True)
class AskContext:
    """The user's situation, assembled to ground an answer."""

    diagnosis: StrategyDiagnosis
    top_jobs: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    job: Job | None = None
    score: JobScore | None = None


def gather_context(
    db: JobPilotDB,
    profile_id: int = config.DEFAULT_PROFILE_ID,
    job_id: str | None = None,
) -> AskContext:
    """Assemble the user's situation for grounding (pure data, no LLM)."""
    d = diagnose(db, profile_id)

    pairs = db.list_top_scored_jobs(
        profile_id=profile_id,
        min_score=config.MIN_RECOMMEND_SCORE,
        limit=10,
    )
    top_jobs = tuple(
        (f"{j.title} @ {j.company}", s.overall_score) for s, j in pairs
    )

    job: Job | None = None
    score: JobScore | None = None
    if job_id:
        job = db.get_job(job_id)
        score = db.get_score(job_id, profile_id)

    return AskContext(diagnosis=d, top_jobs=top_jobs, job=job, score=score)


def _format_top_jobs(top_jobs: tuple[tuple[str, float], ...]) -> str:
    if not top_jobs:
        return "(暂无高分岗)"
    return "\n".join(f"  - [{score:.1f}] {label}" for label, score in top_jobs)


def _format_job_context(job: Job | None, score: JobScore | None) -> str:
    """Optional block describing a specific job the question is about."""
    if not job:
        return ""
    parts = [
        "\n## 这个问题针对的具体岗位",
        f"- 职位：{job.title}",
        f"- 公司：{job.company}",
    ]
    if job.city:
        parts.append(f"- 城市：{job.city}")
    if job.jd_text:
        parts.append(f"- JD：\n{job.jd_text}")
    if score:
        parts.append(f"- AI 匹配分：{score.overall_score:.1f}")
        if score.concerns:
            parts.append("- 已知短板：" + "；".join(score.concerns))
    return "\n".join(parts) + "\n"


ASK_PROMPT = """\
你是一位务实的求职军师，服务对象是一名在校生，目标是 AI 产品经理实习。
下面是 ta 当前的真实求职处境（来自系统记录，不是估算）。请基于这些信息回答 ta 的问题。

## 当前处境
{headline}
- 高分岗（>= {min_score:.0f}）：{high_score_total} 个，已投 {high_score_applied} 个
- 投递总数：{total_applications}（回复 {replied} / 面试 {interview} / Offer {offer} / 被拒 {rejected}）

## 高分岗（可在回答中具体引用）
{top_jobs}

## 用户偏好
{preferences}
{job_context}
## 问题
{question}

## 回答要求
1. 紧扣 ta 的真实处境和偏好回答，能引用上面的具体数据/岗位就引用，别给放之四海皆准的废话。
2. 讲人话，像带过很多人的学长，不堆名词、不灌鸡汤。
3. 不知道的（如某公司内部情况、ta 没提供的信息）就说不知道，别编。
4. 给可执行的下一步，不止讲道理。
5. 中文，简洁，控制在 350 字以内。
"""


def build_ask_prompt(question: str, profile: Profile, context: AskContext) -> str:
    """Build the ask prompt (pure, testable, no API call)."""
    d = context.diagnosis
    return ASK_PROMPT.format(
        headline=d.headline,
        min_score=config.MIN_RECOMMEND_SCORE,
        high_score_total=d.high_score_total,
        high_score_applied=d.high_score_applied,
        total_applications=d.total_applications,
        replied=d.replied_count,
        interview=d.interview_count,
        offer=d.offer_count,
        rejected=d.rejected_count,
        top_jobs=_format_top_jobs(context.top_jobs),
        preferences=_format_preferences(profile),
        job_context=_format_job_context(context.job, context.score),
        question=question,
    )


def answer_question(
    question: str,
    profile: Profile,
    db: JobPilotDB,
    job_id: str | None = None,
) -> str:
    """Answer a free-form job-hunt question via Claude, grounded in user data.

    Raises:
        AskError: when no API key is configured (use build_ask_prompt for a
            manual Claude.ai workflow instead).
    """
    if not config.ANTHROPIC_API_KEY:
        raise AskError(
            "未配置 ANTHROPIC_API_KEY。可用 build_ask_prompt 导出 prompt 到 Claude.ai。"
        )

    profile_id = profile.id or config.DEFAULT_PROFILE_ID
    context = gather_context(db, profile_id, job_id)
    prompt = build_ask_prompt(question, profile, context)

    import anthropic

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        logger.exception("Ask API call failed")
        raise AskError(f"API 调用失败: {exc}") from exc

    return message.content[0].text.strip()
