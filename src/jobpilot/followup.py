"""
Follow-up engine — turns the intentions you voice in chat into trackable
commitments the 军师 proactively checks on.

Flow:
  1. On chat exit, extract_commitments() asks Claude to pull concrete action
     intentions ("本周投字节", "改简历") out of the conversation.
  2. They're stored (followup_store) so next time chat opens, the 军师 brings
     them up first instead of waiting to be asked.
  3. reconcile_with_applications() auto-closes a commitment when its linked job
     is already applied — data-driven, no nagging about things you've done.

The model + parsing + reconciliation here are deterministic and tested; only
extract_commitments() touches the API.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, replace
from typing import Any

from jobpilot import config
from jobpilot.db import JobPilotDB
from jobpilot.models import now_iso

logger = logging.getLogger(__name__)

Message = dict[str, str]

_VALID_STATUS = frozenset({"open", "done", "dropped"})


class FollowupError(RuntimeError):
    """Raised when commitment extraction fails (e.g. no API key)."""


@dataclass(frozen=True)
class Commitment:
    """A trackable action the user said they'd take."""

    id: str
    text: str
    job_id: str = ""
    due_hint: str = ""
    created_at: str = ""
    status: str = "open"

    @classmethod
    def new(cls, text: str, job_id: str = "", due_hint: str = "") -> Commitment:
        created = now_iso()
        raw = f"{text}|{created}".encode()
        cid = hashlib.md5(raw, usedforsecurity=False).hexdigest()[:12]
        return cls(
            id=cid,
            text=text.strip(),
            job_id=job_id,
            due_hint=due_hint,
            created_at=created,
            status="open",
        )

    def with_status(self, status: str) -> Commitment:
        return replace(self, status=status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "job_id": self.job_id,
            "due_hint": self.due_hint,
            "created_at": self.created_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Commitment:
        return cls(
            id=d.get("id", ""),
            text=d.get("text", ""),
            job_id=d.get("job_id", ""),
            due_hint=d.get("due_hint", ""),
            created_at=d.get("created_at", ""),
            status=d.get("status", "open") if d.get("status") in _VALID_STATUS else "open",
        )


EXTRACT_PROMPT = """\
下面是用户和求职军师的一段对话。请提取用户**明确表达过的、具体的、尚未完成的行动意图**
（例如：投某个岗位、改简历、联系某个内推、准备某场面试）。

规则：
- 只提取具体可执行的行动，忽略泛泛的想法、纯提问、纯情绪表达。
- 用户已经说做完的，不要提取。
- 每条尽量短、可核对（"本周投字节AI产品实习"而不是"多投点岗位"）。
- 如果提到具体公司，填 job_hint（公司或岗位名）。
- 如果提到时间，填 due_hint（如"本周""周五前""3天内"），没有就留空。
- 没有任何明确行动意图时，返回空数组。

对话：
{conversation}

## 输出格式（严格 JSON，不要其他文字）
{{"commitments": [{{"text": "行动描述", "job_hint": "公司或岗位（可选）", "due_hint": "时间（可选）"}}]}}
"""


def _format_conversation(history: list[Message]) -> str:
    lines = []
    for m in history:
        role = "用户" if m.get("role") == "user" else "军师"
        lines.append(f"{role}：{m.get('content', '')}")
    return "\n".join(lines)


def build_extract_prompt(history: list[Message]) -> str:
    """Build the commitment-extraction prompt (pure, testable)."""
    return EXTRACT_PROMPT.format(conversation=_format_conversation(history))


def _extract_json(text: str) -> dict:
    """Extract a JSON object, tolerant of code fences (mirrors interview.py)."""
    text = text.strip()
    for candidate in (text,):
        try:
            return json.loads(candidate)
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


def parse_commitments_response(text: str) -> list[Commitment]:
    """Parse the model's JSON into Commitments (pure, tolerant)."""
    data = _extract_json(text)
    raw = data.get("commitments", []) if isinstance(data, dict) else []
    out: list[Commitment] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text_val = (item.get("text") or "").strip()
        if not text_val:
            continue
        out.append(
            Commitment.new(
                text_val,
                job_id=(item.get("job_hint") or "").strip(),
                due_hint=(item.get("due_hint") or "").strip(),
            )
        )
    return out


def extract_commitments(history: list[Message]) -> list[Commitment]:
    """Extract commitments from a conversation via Claude.

    Raises:
        FollowupError: when no API key is configured.
    """
    if not config.ANTHROPIC_API_KEY:
        raise FollowupError("未配置 ANTHROPIC_API_KEY，无法提取承诺。")
    if not history:
        return []

    prompt = build_extract_prompt(history)

    import anthropic

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        logger.exception("Commitment extraction failed")
        raise FollowupError(f"API 调用失败: {exc}") from exc

    return parse_commitments_response(message.content[0].text)


def reconcile_with_applications(
    commitments: list[Commitment], db: JobPilotDB
) -> tuple[list[Commitment], list[str]]:
    """Auto-close open commitments whose linked job is already applied.

    Returns (updated_commitments, closed_ids). Pure data — no LLM. A commitment
    with a job_id that resolves to an existing application is marked done.
    """
    updated: list[Commitment] = []
    closed: list[str] = []
    for c in commitments:
        if c.status == "open" and c.job_id and db.get_application(c.job_id) is not None:
            updated.append(c.with_status("done"))
            closed.append(c.id)
        else:
            updated.append(c)
    return updated, closed
