"""
Interview preparation generator.

Given a target job + the user's resume profile (and optionally the AI match
score), produce likely interview questions across categories, each mapped to a
STAR talking point grounded in the candidate's REAL experience.

Honesty rule (mirrors the resume-tailoring philosophy): talking points must
trace to actual resume content — never fabricate experience.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from jobpilot import config
from jobpilot.models import Job, JobScore, Profile

logger = logging.getLogger(__name__)


class InterviewPrepError(RuntimeError):
    """Raised when interview prep cannot be generated (e.g. no API key)."""


@dataclass(frozen=True)
class InterviewQuestion:
    """One likely interview question with a grounded talking point."""

    category: str
    question: str
    talking_point: str


@dataclass(frozen=True)
class InterviewPrep:
    """Full interview prep for a job."""

    job_title: str
    company: str
    questions: tuple[InterviewQuestion, ...] = field(default_factory=tuple)
    prep_notes: str = ""


INTERVIEW_PROMPT = """\
你是一位资深 AI 产品面试官 + 求职教练。基于以下岗位和候选人简历，生成一份面试准备。

## 目标岗位
- 职位：{job_title}
- 公司：{company}
- JD：
{jd_text}

## 候选人简历
{resume_text}
{score_context}
## 任务
生成 8-10 个该岗位**大概率会问**的问题，覆盖这些类别：
- 行为面（过往经历、协作、冲突）
- 产品 sense（产品判断、取舍、指标）
- 技术理解（对 AI/大模型/数据的理解，匹配 JD）
- 项目深挖（针对简历里的具体项目追问）
- 岗位&公司匹配（为什么这家、为什么这个方向）

每个问题给一个 talking_point：用候选人**简历里真实存在**的经历，按 STAR（情境-任务-行动-结果）组织答题要点。

## 严格规则
- talking_point 必须基于简历真实内容，**不许编造**经历或数据
- 如果某类问题简历里没有合适素材，talking_point 要诚实指出"这块需要补强"并给准备方向
- 中文输出

## 输出格式（严格 JSON，不要其他文字）
{{
  "questions": [
    {{"category": "行为面", "question": "问题原文", "talking_point": "STAR 要点，引用简历真实经历"}}
  ],
  "prep_notes": "总体准备建议：要突出什么、要提前准备回应哪些短板"
}}
"""


def _format_score_context(score: JobScore | None) -> str:
    """Feed the AI score's concerns/highlights so prep can pre-empt weak spots."""
    if not score:
        return ""
    parts = ["\n## AI 匹配分析（用于针对性准备）"]
    if score.highlights:
        parts.append("匹配亮点（面试可主动强调）：" + "；".join(score.highlights))
    if score.concerns:
        parts.append("潜在短板（提前准备如何回应）：" + "；".join(score.concerns))
    return "\n".join(parts) + "\n"


def build_interview_prompt(
    profile: Profile, job: Job, score: JobScore | None = None
) -> str:
    """Build the interview-prep prompt (pure, testable, no API call)."""
    return INTERVIEW_PROMPT.format(
        job_title=job.title,
        company=job.company,
        jd_text=job.jd_text or "(无 JD)",
        resume_text=profile.raw_text or "(无简历文本)",
        score_context=_format_score_context(score),
    )


def _extract_json(text: str) -> dict:
    """Extract a JSON object from the model response, tolerant of code fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def parse_interview_response(text: str, job: Job) -> InterviewPrep:
    """Parse the model's JSON into an InterviewPrep (pure, testable)."""
    data = _extract_json(text)
    raw_questions = data.get("questions", []) if isinstance(data, dict) else []
    questions: list[InterviewQuestion] = []
    for q in raw_questions:
        if not isinstance(q, dict):
            continue
        question = (q.get("question") or "").strip()
        if not question:
            continue
        questions.append(
            InterviewQuestion(
                category=(q.get("category") or "其他").strip(),
                question=question,
                talking_point=(q.get("talking_point") or "").strip(),
            )
        )
    return InterviewPrep(
        job_title=job.title,
        company=job.company,
        questions=tuple(questions),
        prep_notes=(data.get("prep_notes") or "").strip() if isinstance(data, dict) else "",
    )


def format_markdown(prep: InterviewPrep) -> str:
    """Render an InterviewPrep as Markdown for console display or saving."""
    lines = [f"# 面试准备 — {prep.job_title} @ {prep.company}", ""]
    # Group questions by category, preserving first-seen order
    by_cat: dict[str, list[InterviewQuestion]] = {}
    for q in prep.questions:
        by_cat.setdefault(q.category, []).append(q)
    for cat, qs in by_cat.items():
        lines.append(f"## {cat}")
        for q in qs:
            lines.append(f"**Q：{q.question}**")
            if q.talking_point:
                lines.append(f"- 要点：{q.talking_point}")
            lines.append("")
    if prep.prep_notes:
        lines.append("## 总体准备建议")
        lines.append(prep.prep_notes)
    return "\n".join(lines).rstrip() + "\n"


def generate_interview_prep(
    profile: Profile, job: Job, score: JobScore | None = None
) -> InterviewPrep:
    """Generate interview prep via Claude API.

    Raises:
        InterviewPrepError: when no API key is configured (use
            build_interview_prompt for a manual Claude.ai workflow instead).
    """
    if not config.ANTHROPIC_API_KEY:
        raise InterviewPrepError(
            "未配置 ANTHROPIC_API_KEY。可用 build_interview_prompt 导出 prompt "
            "到 Claude.ai 手动生成。"
        )

    prompt = build_interview_prompt(profile, job, score)

    import anthropic

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        logger.exception("Interview prep API call failed")
        raise InterviewPrepError(f"API 调用失败: {exc}") from exc

    text = message.content[0].text.strip()
    return parse_interview_response(text, job)
