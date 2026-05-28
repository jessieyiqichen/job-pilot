"""Tests for the GitHub issue-search job adapter."""

import json
from unittest.mock import MagicMock, patch

from jobpilot.adapters.base import SearchFilters
from jobpilot.adapters.github_jobs import (
    GitHubAdapter,
    _extract_json_array,
    _parse_github_jobs,
    broaden_query,
)


def test_broaden_query_strips_job_type_tokens():
    assert broaden_query("AI产品 实习") == "AI产品"
    assert broaden_query("大模型 产品 全职") == "大模型 产品"
    assert broaden_query("AI product intern") == "AI product"
    assert broaden_query("实习") == "实习"  # don't empty it out


# ----------------------------------------------------------------------
# pure helpers
# ----------------------------------------------------------------------


def test_extract_json_array_plain_and_fenced():
    assert _extract_json_array('[{"a":1}]') == [{"a": 1}]
    assert _extract_json_array('```json\n[{"a":2}]\n```') == [{"a": 2}]
    assert _extract_json_array("前言\n[{\"a\":3}]\n后语") == [{"a": 3}]
    assert _extract_json_array("not json") == []


def test_parse_github_jobs_builds_jobs_and_skips_invalid():
    items = [
        {"company": "字节", "title": "AI产品实习", "salary": "15-25K", "city": "上海",
         "source_url": "https://github.com/x/y/issues/1"},
        {"company": "", "title": "无公司"},  # skipped
        {"title": "无公司名"},               # skipped
    ]
    jobs = _parse_github_jobs(items)
    assert len(jobs) == 1
    j = jobs[0]
    assert j.platform == "github"
    assert j.company == "字节"
    assert j.salary_min == 15000 and j.salary_max == 25000
    assert j.job_id  # hashed id present


# ----------------------------------------------------------------------
# adapter.search
# ----------------------------------------------------------------------


def test_platform_name():
    assert GitHubAdapter().platform_name == "github"


@patch("jobpilot.adapters.github_jobs._extract_jobs_via_ai")
@patch("jobpilot.adapters.github_jobs.call_gh_search")
def test_search_happy_path(mock_gh, mock_ai):
    mock_gh.return_value = [{"title": "招聘", "body": "...", "url": "u", "repository": {}}]
    mock_ai.return_value = [
        {"company": "MiniMax", "title": "AI产品经理实习", "source_url": "u"}
    ]
    jobs = GitHubAdapter().search("AI产品 实习", SearchFilters(city="上海"))
    assert len(jobs) == 1
    assert jobs[0].company == "MiniMax"
    assert jobs[0].platform == "github"
    # city NOT appended; job-type token stripped → broadened keyword
    sent = mock_gh.call_args[0][0]
    assert "上海" not in sent
    assert "实习" not in sent


@patch("jobpilot.adapters.github_jobs.call_gh_search")
def test_search_no_issues_returns_empty(mock_gh):
    mock_gh.return_value = []
    assert GitHubAdapter().search("AI产品") == []


@patch("jobpilot.adapters.github_jobs.call_gh_search", side_effect=FileNotFoundError("no gh"))
def test_search_handles_missing_gh(mock_gh):
    assert GitHubAdapter().search("AI产品") == []


@patch("jobpilot.adapters.github_jobs.subprocess.run")
def test_call_gh_search_parses_json(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps([{"title": "t"}]), stderr="")
    from jobpilot.adapters.github_jobs import call_gh_search

    out = call_gh_search("AI产品")
    assert out == [{"title": "t"}]
    # query includes the hiring marker
    assert "招聘" in mock_run.call_args[0][0][3]
