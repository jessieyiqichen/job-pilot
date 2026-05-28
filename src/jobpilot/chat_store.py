"""
Chat history persistence.

Stores the full conversation per profile as JSON under config.CHATS_DIR so the
军师 can pick up where it left off next time ("接着上次聊"). The full transcript
is kept on disk; the chat loop only feeds a recent window to the API (see
config.CHAT_MAX_CONTEXT_MESSAGES) to bound token cost.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jobpilot import config

logger = logging.getLogger(__name__)

# Message = {"role": "user"|"assistant", "content": str}
Message = dict[str, str]

_VALID_ROLES = frozenset({"user", "assistant"})


def chat_file(profile_id: int) -> Path:
    """Path to the chat transcript for a profile."""
    return config.CHATS_DIR / f"chat_{profile_id}.json"


def load_history(profile_id: int) -> list[Message]:
    """Load saved chat history. Returns [] if missing/corrupt.

    Malformed entries are dropped (never trust file content) so a partially
    bad file still yields a usable conversation.
    """
    path = chat_file(profile_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Chat history unreadable, starting fresh: %s", path)
        return []
    if not isinstance(data, list):
        return []
    out: list[Message] = []
    for m in data:
        if (
            isinstance(m, dict)
            and m.get("role") in _VALID_ROLES
            and isinstance(m.get("content"), str)
        ):
            out.append({"role": m["role"], "content": m["content"]})
    return out


def save_history(profile_id: int, history: list[Message]) -> None:
    """Persist the full chat history (atomic write)."""
    path = chat_file(profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)  # atomic on POSIX


def clear_history(profile_id: int) -> None:
    """Delete the saved chat history, if any."""
    path = chat_file(profile_id)
    if path.exists():
        path.unlink()
