"""
Data models for JobPilot.

Pure data containers using dataclasses. No database logic here.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Profile:
    """User resume profile."""

    id: int | None = None
    name: str = ""
    raw_text: str = ""
    structured: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["structured"] = json.dumps(d["structured"], ensure_ascii=False)
        return d

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Profile:
        structured = row.get("structured", "{}")
        if isinstance(structured, str):
            structured = json.loads(structured) if structured else {}
        return cls(
            id=row.get("id"),
            name=row.get("name", ""),
            raw_text=row.get("raw_text", ""),
            structured=structured,
            updated_at=row.get("updated_at", ""),
        )


@dataclass(frozen=True)
class Job:
    """Job posting from a recruitment platform."""

    id: int | None = None
    platform: str = ""
    job_id: str = ""
    title: str = ""
    company: str = ""
    salary_min: int = 0
    salary_max: int = 0
    city: str = ""
    experience: str = ""
    education: str = ""
    jd_text: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)
    discovered_at: str = ""
    status: str = "new"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["raw_data"] = json.dumps(d["raw_data"], ensure_ascii=False)
        return d

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Job:
        raw_data = row.get("raw_data", "{}")
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data) if raw_data else {}
        return cls(
            id=row.get("id"),
            platform=row.get("platform", ""),
            job_id=row.get("job_id", ""),
            title=row.get("title", ""),
            company=row.get("company", ""),
            salary_min=row.get("salary_min", 0) or 0,
            salary_max=row.get("salary_max", 0) or 0,
            city=row.get("city", ""),
            experience=row.get("experience", ""),
            education=row.get("education", ""),
            jd_text=row.get("jd_text", ""),
            raw_data=raw_data,
            discovered_at=row.get("discovered_at", ""),
            status=row.get("status", "new"),
        )


@dataclass(frozen=True)
class JobScore:
    """AI matching score for a job against a profile."""

    id: int | None = None
    job_id: str = ""
    profile_id: int = 0
    overall_score: float = 0.0
    skill_match: float = 0.0
    experience_match: float = 0.0
    salary_match: float = 0.0
    highlights: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    suggestion: str = ""
    scored_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["highlights"] = json.dumps(d["highlights"], ensure_ascii=False)
        d["concerns"] = json.dumps(d["concerns"], ensure_ascii=False)
        return d

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> JobScore:
        highlights = row.get("highlights", "[]")
        if isinstance(highlights, str):
            highlights = json.loads(highlights) if highlights else []
        concerns = row.get("concerns", "[]")
        if isinstance(concerns, str):
            concerns = json.loads(concerns) if concerns else []
        return cls(
            id=row.get("id"),
            job_id=row.get("job_id", ""),
            profile_id=row.get("profile_id", 0),
            overall_score=row.get("overall_score", 0.0) or 0.0,
            skill_match=row.get("skill_match", 0.0) or 0.0,
            experience_match=row.get("experience_match", 0.0) or 0.0,
            salary_match=row.get("salary_match", 0.0) or 0.0,
            highlights=highlights,
            concerns=concerns,
            suggestion=row.get("suggestion", ""),
            scored_at=row.get("scored_at", ""),
        )


@dataclass(frozen=True)
class Application:
    """Job application tracking record."""

    id: int | None = None
    job_id: str = ""
    status: str = "applied"
    resume_path: str = ""
    applied_at: str = ""
    updated_at: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Application:
        return cls(
            id=row.get("id"),
            job_id=row.get("job_id", ""),
            status=row.get("status", "applied"),
            resume_path=row.get("resume_path", ""),
            applied_at=row.get("applied_at", ""),
            updated_at=row.get("updated_at", ""),
            notes=row.get("notes", ""),
        )


def now_iso() -> str:
    """Return current time as ISO string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
