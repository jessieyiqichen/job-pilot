"""
XHS (小红书) job import adapter.

Import-only module: parses structured job data extracted from XHS favorites
into Job models for database storage. Not a search adapter — XHS job discovery
happens via user favorites + Claude AI extraction.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from jobpilot.models import Job


def _generate_xhs_job_id(company: str, title: str, source_url: str = "") -> str:
    """Generate a deterministic job ID from company + title + source URL."""
    raw = f"xhs:{company}:{title}:{source_url}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _parse_salary(salary_str: str) -> tuple[int, int]:
    """Parse salary string into (min, max) in yuan/month.

    Handles formats:
    - "15-25K" or "15K-25K" or "15k-25k"
    - "15-25k/月"
    - "150-250" (plain numbers, treated as-is)
    - "15w-25w" or "15万-25万" (annual, /12 to monthly)
    """
    if not salary_str:
        return 0, 0

    salary_str = salary_str.strip()

    # Annual salary: "15w-25w" or "15万-25万"
    m = re.match(r"(\d+)\s*[wW万][_\-~到](\d+)\s*[wW万]", salary_str)
    if m:
        return int(m.group(1)) * 10000 // 12, int(m.group(2)) * 10000 // 12

    # Monthly K format: "15-25K" or "15K-25K"
    m = re.match(r"(\d+)\s*[kK]?\s*[_\-~到]\s*(\d+)\s*[kK]", salary_str)
    if m:
        return int(m.group(1)) * 1000, int(m.group(2)) * 1000

    # Plain number range: "15000-25000"
    m = re.match(r"(\d+)\s*[_\-~到]\s*(\d+)", salary_str)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return lo, hi

    return 0, 0


def parse_xhs_job(item: dict) -> Job | None:
    """Parse a single XHS note dict into a Job, or None if missing key fields."""
    company = str(item.get("company", "")).strip()
    title = str(item.get("title", "")).strip()

    if not company or not title:
        return None

    source_url = str(item.get("source_url", "") or item.get("url", "")).strip()
    sal_min, sal_max = _parse_salary(str(item.get("salary", "")))

    raw_data = dict(item)

    return Job(
        platform="xhs",
        job_id=_generate_xhs_job_id(company, title, source_url),
        title=title,
        company=company,
        salary_min=sal_min,
        salary_max=sal_max,
        city=str(item.get("city", "")).strip(),
        experience=str(item.get("experience", "")).strip(),
        education=str(item.get("education", "")).strip(),
        jd_text=str(item.get("jd_text", "")).strip(),
        raw_data=raw_data,
        discovered_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status="new",
    )


def parse_xhs_jobs(items: list[dict]) -> list[Job]:
    """Parse a list of XHS note dicts into Jobs, skipping invalid entries."""
    jobs: list[Job] = []
    for item in items:
        job = parse_xhs_job(item)
        if job is not None:
            jobs.append(job)
    return jobs
