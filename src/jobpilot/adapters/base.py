"""
Abstract base adapter for recruitment platforms.

Each platform (Boss直聘, 拉勾, 猎聘...) implements this interface.
Business logic depends only on this interface, never on platform specifics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from jobpilot.models import Job


@dataclass(frozen=True)
class SearchFilters:
    """Search filters for job queries."""

    city: str = ""
    experience: str = ""       # e.g. "3-5年"
    education: str = ""        # e.g. "本科"
    salary_range: str = ""     # e.g. "15-25K"
    industry: str = ""
    company_size: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    """Abstract adapter for a recruitment platform."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g. 'boss', 'lagou')."""
        ...

    @abstractmethod
    def search(self, query: str, filters: SearchFilters | None = None) -> list[Job]:
        """Search for jobs matching the query and filters.

        Args:
            query: Search keywords (e.g. "Python开发")
            filters: Optional search filters

        Returns:
            List of Job objects found
        """
        ...

    @abstractmethod
    def get_job_detail(self, job_id: str) -> Job | None:
        """Get full details for a specific job.

        Args:
            job_id: Platform-specific job identifier

        Returns:
            Job with full JD text, or None if not found
        """
        ...
