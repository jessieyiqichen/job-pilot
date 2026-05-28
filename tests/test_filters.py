"""Tests for post-scoring company blacklist / headhunter filters."""

from jobpilot.filters import (
    BLACKLIST_CAP,
    HEADHUNTER_CAP,
    apply_company_filters,
    is_blacklisted,
    is_headhunter,
)
from jobpilot.models import Job, JobScore


def _score(v=8.0):
    return JobScore(job_id="x", overall_score=v, concerns=["原有顾虑"])


def test_is_blacklisted_substring_case_insensitive():
    job = Job(job_id="x", company="某外包科技有限公司")
    assert is_blacklisted(job, ["外包科技"]) is True
    assert is_blacklisted(job, ["阿里"]) is False
    assert is_blacklisted(job, []) is False


def test_is_headhunter_detects_markers():
    assert is_headhunter(Job(job_id="x", company="XX猎头")) is True
    assert is_headhunter(Job(job_id="x", title="AI产品经理", jd_text="本岗位由人才顾问代招")) is True
    assert is_headhunter(Job(job_id="x", company="字节跳动", title="AI产品", jd_text="负责大模型")) is False


def test_blacklist_caps_and_annotates():
    job = Job(job_id="x", company="黑名单公司")
    out = apply_company_filters(_score(8.0), job, ["黑名单公司"])
    assert out.overall_score == BLACKLIST_CAP
    assert any("黑名单" in c for c in out.concerns)
    assert "原有顾虑" in out.concerns  # preserves existing concerns


def test_headhunter_soft_cap():
    job = Job(job_id="x", company="某猎头公司", title="AI产品")
    out = apply_company_filters(_score(9.0), job, [])
    assert out.overall_score == HEADHUNTER_CAP
    assert any("猎头" in c for c in out.concerns)


def test_headhunter_can_be_disabled():
    job = Job(job_id="x", company="某猎头公司")
    out = apply_company_filters(_score(9.0), job, [], filter_headhunter=False)
    assert out.overall_score == 9.0  # unchanged


def test_no_match_is_noop():
    job = Job(job_id="x", company="字节跳动", title="AI产品", jd_text="大模型")
    out = apply_company_filters(_score(8.0), job, ["阿里"])
    assert out.overall_score == 8.0
    assert out.concerns == ["原有顾虑"]


def test_blacklist_does_not_raise_score():
    """Cap only lowers; a low score stays low, never bumped up to the cap."""
    job = Job(job_id="x", company="黑名单公司")
    out = apply_company_filters(_score(1.0), job, ["黑名单公司"])
    assert out.overall_score == 1.0
