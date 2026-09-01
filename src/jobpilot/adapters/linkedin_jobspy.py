"""
LinkedIn job-search adapter backed by the JobSpy library.

JobSpy (https://github.com/speedyapply/JobSpy) queries LinkedIn's public
job-listing endpoints — no login, no cookies, no account at risk — which
fits JobPilot's no-scraping-with-real-accounts stance the same way the
websearch adapter does.

The dependency is optional: install with `pip install python-jobspy`.
Without it the adapter degrades to an empty result with a warning, so the
rest of the pipeline keeps working.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any, Callable

from jobpilot import config
from jobpilot.adapters.base import BaseAdapter, SearchFilters
from jobpilot.models import Job

logger = logging.getLogger(__name__)

_LINKEDIN_VIEW_RE = re.compile(r"/jobs/view/(\d+)")

# Columns worth keeping in raw_data (JobSpy returns many more).
_RAW_KEEP = (
    "site",
    "job_url",
    "date_posted",
    "is_remote",
    "job_type",
    "min_amount",
    "max_amount",
    "interval",
    "currency",
    "location",
)


def _load_scraper() -> Callable[..., Any] | None:
    """Return jobspy.scrape_jobs, or None when the library is not installed."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        logger.warning(
            "python-jobspy 未安装，linkedin 渠道跳过（pip install python-jobspy）"
        )
        return None
    return scrape_jobs


def _clean(value: Any) -> str:
    """Normalize JobSpy cell values: None/NaN → ''."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    return str(value).strip()


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, float) and value != value:  # NaN
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _job_id_from_url(url: str, title: str, company: str) -> str:
    """Stable per-posting id: LinkedIn's numeric id when present, else a hash."""
    match = _LINKEDIN_VIEW_RE.search(url or "")
    if match:
        return f"li-{match.group(1)}"
    digest = hashlib.sha1(f"{title}|{company}|{url}".encode()).hexdigest()[:16]
    return f"li-{digest}"


def _row_to_job(row: dict[str, Any]) -> Job | None:
    """Map one JobSpy dataframe row to a Job; None when title/company missing."""
    title = _clean(row.get("title"))
    company = _clean(row.get("company"))
    if not title or not company:
        return None

    url = _clean(row.get("job_url"))
    description = _clean(row.get("description"))
    location = _clean(row.get("location"))
    posted = _clean(row.get("date_posted"))

    jd_parts = [f"{title} @ {company}"]
    if location:
        jd_parts.append(f"地点: {location}")
    if posted:
        jd_parts.append(f"发布: {posted}")
    if url:
        jd_parts.append(f"链接: {url}")
    if description:
        jd_parts.append(description)

    raw_data = {k: _clean(row.get(k)) for k in _RAW_KEEP if k in row}

    return Job(
        platform="linkedin",
        job_id=_job_id_from_url(url, title, company),
        title=title,
        company=company,
        salary_min=_to_int(row.get("min_amount")),
        salary_max=_to_int(row.get("max_amount")),
        city=location,
        jd_text="\n".join(jd_parts),
        raw_data=raw_data,
        discovered_at=datetime.now().isoformat(timespec="seconds"),
        status="new",
    )


class LinkedInJobSpyAdapter(BaseAdapter):
    """LinkedIn listings via JobSpy's login-free public search."""

    @property
    def platform_name(self) -> str:
        return "linkedin"

    def search(self, query: str, filters: SearchFilters | None = None) -> list[Job]:
        scrape = _load_scraper()
        if scrape is None:
            return []

        f = filters or SearchFilters()
        is_remote = bool(f.extra.get("remote", config.JOBSPY_REMOTE_DEFAULT))
        sites = list(f.extra.get("sites") or config.JOBSPY_SITES)

        try:
            df = scrape(
                site_name=sites,
                search_term=query,
                is_remote=is_remote,
                results_wanted=config.JOBSPY_RESULTS_WANTED,
                hours_old=config.JOBSPY_HOURS_OLD,
                country_indeed=config.JOBSPY_COUNTRY,
                linkedin_fetch_description=False,
            )
        except (
            Exception
        ) as exc:  # noqa: BLE001 — one dead channel must not kill the run
            logger.error("JobSpy 抓取失败（query=%s）: %s", query, exc)
            return []

        rows = df.to_dict("records") if df is not None else []
        jobs = [job for row in rows if (job := _row_to_job(row)) is not None]
        logger.info("linkedin(jobspy) 「%s」→ %d 条", query, len(jobs))
        return jobs

    def get_job_detail(self, job_id: str) -> Job | None:
        """Listing rows already carry what we store; no separate detail call."""
        return None


if __name__ == "__main__":  # pragma: no cover — manual smoke test
    logging.basicConfig(level=logging.INFO)
    found = LinkedInJobSpyAdapter().search("AI product intern")
    print(json.dumps([j.to_dict() for j in found[:3]], ensure_ascii=False, indent=2))
