"""Tests for the LinkedIn (JobSpy-backed) adapter."""

from unittest.mock import MagicMock, patch

from jobpilot.adapters.linkedin_jobspy import (
    LinkedInJobSpyAdapter,
    _job_id_from_url,
    _row_to_job,
)

from jobpilot.adapters.base import SearchFilters

# ----------------------------------------------------------------------
# pure helpers
# ----------------------------------------------------------------------


def test_job_id_from_linkedin_view_url():
    url = "https://www.linkedin.com/jobs/view/4123456789"
    assert _job_id_from_url(url, "PM Intern", "Acme") == "li-4123456789"


def test_job_id_fallback_hash_is_stable():
    a = _job_id_from_url("", "PM Intern", "Acme")
    b = _job_id_from_url("", "PM Intern", "Acme")
    assert a == b and a.startswith("li-") and len(a) > 5


def test_row_to_job_maps_fields():
    row = {
        "title": "AI Product Intern",
        "company": "Startup Inc",
        "location": "Remote, US",
        "job_url": "https://www.linkedin.com/jobs/view/99",
        "min_amount": 4000.0,
        "max_amount": 6000.0,
        "description": "Build AI products.",
        "date_posted": "2026-08-30",
        "is_remote": True,
        "site": "linkedin",
    }
    job = _row_to_job(row)
    assert job is not None
    assert job.platform == "linkedin"
    assert job.job_id == "li-99"
    assert job.title == "AI Product Intern"
    assert job.company == "Startup Inc"
    assert job.city == "Remote, US"
    assert job.salary_min == 4000 and job.salary_max == 6000
    assert "Build AI products." in job.jd_text
    assert job.raw_data["job_url"].endswith("/99")
    assert job.status == "new"


def test_row_to_job_handles_nan_and_missing():
    nan = float("nan")
    row = {
        "title": "PM Intern",
        "company": "Acme",
        "location": nan,
        "job_url": nan,
        "min_amount": nan,
        "max_amount": None,
        "description": nan,
        "date_posted": nan,
    }
    job = _row_to_job(row)
    assert job is not None
    assert job.city == ""
    assert job.salary_min == 0 and job.salary_max == 0
    assert "PM Intern" in job.jd_text  # jd falls back to title/company line


def test_row_to_job_skips_rows_without_company_or_title():
    assert _row_to_job({"title": "", "company": "Acme"}) is None
    assert _row_to_job({"title": "PM", "company": ""}) is None


# ----------------------------------------------------------------------
# adapter.search
# ----------------------------------------------------------------------


def test_platform_name():
    assert LinkedInJobSpyAdapter().platform_name == "linkedin"


@patch("jobpilot.adapters.linkedin_jobspy._load_scraper", return_value=None)
def test_search_returns_empty_when_jobspy_missing(_):
    assert LinkedInJobSpyAdapter().search("pm intern") == []


@patch("jobpilot.adapters.linkedin_jobspy._load_scraper")
def test_search_maps_dataframe_rows(mock_loader):
    fake_df = MagicMock()
    fake_df.to_dict.return_value = [
        {
            "title": "Product Intern",
            "company": "Acme",
            "location": "Remote",
            "job_url": "https://www.linkedin.com/jobs/view/7",
            "description": "desc",
        },
        {"title": "", "company": "skipme"},
    ]
    scraper = MagicMock(return_value=fake_df)
    mock_loader.return_value = scraper

    jobs = LinkedInJobSpyAdapter().search(
        "product intern", SearchFilters(extra={"remote": True})
    )

    assert len(jobs) == 1
    assert jobs[0].job_id == "li-7"
    kwargs = scraper.call_args.kwargs
    assert kwargs["search_term"] == "product intern"
    assert kwargs["is_remote"] is True


@patch("jobpilot.adapters.linkedin_jobspy._load_scraper")
def test_search_swallows_scraper_errors(mock_loader):
    mock_loader.return_value = MagicMock(side_effect=RuntimeError("boom"))
    assert LinkedInJobSpyAdapter().search("pm") == []


def test_get_job_detail_returns_none():
    assert LinkedInJobSpyAdapter().get_job_detail("li-1") is None
