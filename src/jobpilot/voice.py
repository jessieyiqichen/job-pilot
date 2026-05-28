"""
Voice (language-style) samples — teach the advisor to write in *your* voice.

The problem: generated greetings/copy come out in generic "AI 腔" and you rewrite
them every time. The fix isn't describing your style in adjectives — it's giving
the model your real text to mimic (few-shot beats description). And your rewrites
are the best samples: feed the version you actually sent back in, and next time
it writes closer to you.

Samples are stored per profile under config.VOICE_DIR (gitignored — personal),
and build_voice_block() turns them into a few-shot prompt fragment injected into
greeting generation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobpilot import config
from jobpilot.models import now_iso

logger = logging.getLogger(__name__)

_VALID_SOURCES = frozenset({"manual", "revised", "chat"})


@dataclass(frozen=True)
class VoiceSample:
    """One piece of the user's real writing, used as a style exemplar."""

    text: str
    source: str = "manual"   # manual (cold start) / revised (rewrite feedback) / chat
    context: str = ""        # optional: "greeting" / "email" / ...
    created_at: str = ""

    @classmethod
    def new(cls, text: str, source: str = "manual", context: str = "") -> VoiceSample:
        return cls(
            text=text.strip(),
            source=source if source in _VALID_SOURCES else "manual",
            context=context,
            created_at=now_iso(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "context": self.context,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> VoiceSample:
        src = d.get("source", "manual")
        return cls(
            text=d.get("text", ""),
            source=src if src in _VALID_SOURCES else "manual",
            context=d.get("context", ""),
            created_at=d.get("created_at", ""),
        )


def voice_file(profile_id: int) -> Path:
    return config.VOICE_DIR / f"voice_{profile_id}.json"


def load_samples(profile_id: int = config.DEFAULT_PROFILE_ID) -> list[VoiceSample]:
    """Load voice samples. Returns [] if missing/corrupt; drops malformed entries."""
    path = voice_file(profile_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Voice samples unreadable, starting fresh: %s", path)
        return []
    if not isinstance(data, list):
        return []
    return [
        VoiceSample.from_dict(d)
        for d in data
        if isinstance(d, dict) and (d.get("text") or "").strip()
    ]


def save_samples(profile_id: int, samples: list[VoiceSample]) -> None:
    """Persist voice samples (atomic write)."""
    path = voice_file(profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps([s.to_dict() for s in samples], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def add_sample(profile_id: int, sample: VoiceSample) -> bool:
    """Append a sample, deduping by exact text. Returns True if added."""
    samples = load_samples(profile_id)
    if any(s.text == sample.text for s in samples):
        return False
    save_samples(profile_id, samples + [sample])
    return True


_VOICE_HEADER = """\
## 用户的真实语言风格（重要：模仿这个声音，别用 AI 腔，让 ta 不用再改）
下面是用户自己写的真实文字。注意 ta 的用词、句式、长短、语气、标点习惯。
生成时贴近这些样本的表达方式，写得像 ta 本人，而不是像 AI 模板。"""


def build_voice_block(samples: list[VoiceSample], max_n: int = 6) -> str:
    """Build a few-shot voice block from the most recent samples. Empty if none.

    Recent samples win — your latest rewrites best reflect how you want to sound.
    """
    if not samples:
        return ""
    recent = samples[-max_n:]
    lines = [_VOICE_HEADER, ""]
    for i, s in enumerate(recent, 1):
        lines.append(f"样本{i}：{s.text}")
    return "\n".join(lines)
