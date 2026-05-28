"""
Commitment persistence — stores follow-up commitments per profile as JSON under
config.CHATS_DIR (gitignored, alongside chat transcripts). Mirrors chat_store.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jobpilot import config
from jobpilot.followup import Commitment

logger = logging.getLogger(__name__)


def commit_file(profile_id: int) -> Path:
    """Path to the commitments file for a profile."""
    return config.CHATS_DIR / f"commitments_{profile_id}.json"


def load_commitments(profile_id: int) -> list[Commitment]:
    """Load saved commitments. Returns [] if missing/corrupt; drops bad entries."""
    path = commit_file(profile_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Commitments unreadable, starting fresh: %s", path)
        return []
    if not isinstance(data, list):
        return []
    out: list[Commitment] = []
    for d in data:
        if isinstance(d, dict) and (d.get("text") or "").strip():
            out.append(Commitment.from_dict(d))
    return out


def save_commitments(profile_id: int, commitments: list[Commitment]) -> None:
    """Persist commitments (atomic write)."""
    path = commit_file(profile_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps([c.to_dict() for c in commitments], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def add_commitments(profile_id: int, new: list[Commitment]) -> list[Commitment]:
    """Merge new commitments into storage, deduping by text. Returns those added."""
    existing = load_commitments(profile_id)
    existing_texts = {c.text for c in existing}
    added = [c for c in new if c.text and c.text not in existing_texts]
    if added:
        save_commitments(profile_id, existing + added)
    return added


def update_status(profile_id: int, commitment_id: str, status: str) -> None:
    """Set the status of a commitment by id."""
    commitments = load_commitments(profile_id)
    updated = [
        c.with_status(status) if c.id == commitment_id else c for c in commitments
    ]
    save_commitments(profile_id, updated)


def list_commitments(profile_id: int, status: str | None = None) -> list[Commitment]:
    """List commitments, optionally filtered by status."""
    commitments = load_commitments(profile_id)
    if status is None:
        return commitments
    return [c for c in commitments if c.status == status]
