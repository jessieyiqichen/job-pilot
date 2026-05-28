"""
Cognitive profile loader — bridges the sibling Nous project into the advisor.

Nous (../nous) models the user at the *cognitive* layer: how they decide, where
their blind spots are, what their value hierarchy is — not just what job data
says. Loading that profile lets the 军师 ground its guidance in how the user
actually thinks. For example: someone whose model shows "acts only when the
framework converges" + "unsustainable standards when engaged" isn't procrastinating
when they tailor 19 resumes but apply to zero — they're stuck on a cognitive
blind spot, and the advice should address *that*, not nag them to "just apply".

Optional by design: if the Nous model file is absent, the advisor degrades to
job-data-only grounding.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from jobpilot import config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CognitiveDimension:
    name: str
    description: str
    behavioral_predictions: tuple[str, ...] = field(default_factory=tuple)
    confidence: str = ""


@dataclass(frozen=True)
class CognitiveProfile:
    summary: str = ""
    dimensions: tuple[CognitiveDimension, ...] = field(default_factory=tuple)


def load_cognitive_profile(path: str | None = None) -> CognitiveProfile | None:
    """Load the Nous cognitive model. Returns None if absent/unreadable/empty.

    Never raises — a missing or broken model just means the advisor falls back
    to job-data grounding.
    """
    p = Path(path or config.COGNITIVE_MODEL_PATH)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Cognitive model unreadable, skipping: %s", p)
        return None
    if not isinstance(data, dict):
        return None

    dims: list[CognitiveDimension] = []
    for d in data.get("dimensions", []):
        if not isinstance(d, dict) or not d.get("name"):
            continue
        preds = d.get("behavioral_predictions", [])
        dims.append(
            CognitiveDimension(
                name=d.get("name", ""),
                description=d.get("description", ""),
                behavioral_predictions=tuple(p for p in preds if isinstance(p, str)),
                confidence=d.get("confidence", ""),
            )
        )
    summary = data.get("summary", "") if isinstance(data.get("summary"), str) else ""
    if not summary and not dims:
        return None
    return CognitiveProfile(summary=summary, dimensions=tuple(dims))


_USAGE_GUARD = """\
## 怎么用这份认知画像（重要）
- 这是帮你「理解 ta 怎么决策、卡点在哪」的，不是用来给 ta 贴标签或当面诊断人格。
- 别直接复述模型内容（"你的盲区是X"会让人不适）；用它来调整你建议的**方式**。
- 例：ta 决策需要框架收敛、且在乎的事会用过高标准——当 ta 卡住不行动（如筛了岗却不投），
  别催"快做"，而是帮 ta 给这件事建个最小框架、或主动允许"先做到 good enough 能启动"。
- 你是 ta 认知盲区的质检员和陪伴者，不是心理医生。点到为止，尊重 ta。"""


def format_cognitive_prompt(profile: CognitiveProfile | None) -> str:
    """Format the cognitive profile as a prompt block. Empty string if None."""
    if not profile:
        return ""
    lines = ["## 关于这个人的认知画像（来自 Nous 认知建模，帮你理解 ta 怎么想）"]
    if profile.summary:
        lines.append(profile.summary)
    if profile.dimensions:
        lines.append("\n各认知维度：")
        for d in profile.dimensions:
            lines.append(f"- **{d.name}**：{d.description}")
    lines.append("")
    lines.append(_USAGE_GUARD)
    return "\n".join(lines)
