"""Tests for XHS (小红书) import adapter."""

from jobpilot.adapters.xhs import (
    _generate_xhs_job_id,
    _parse_salary,
    parse_xhs_job,
    parse_xhs_jobs,
)


class TestGenerateXhsJobId:
    def test_deterministic(self):
        """Same inputs always produce the same ID."""
        id1 = _generate_xhs_job_id("字节跳动", "Python开发", "https://xhs.com/1")
        id2 = _generate_xhs_job_id("字节跳动", "Python开发", "https://xhs.com/1")
        assert id1 == id2
        assert len(id1) == 16

    def test_different_company(self):
        id1 = _generate_xhs_job_id("字节跳动", "Python开发")
        id2 = _generate_xhs_job_id("阿里巴巴", "Python开发")
        assert id1 != id2

    def test_different_url(self):
        id1 = _generate_xhs_job_id("字节跳动", "Python开发", "https://xhs.com/1")
        id2 = _generate_xhs_job_id("字节跳动", "Python开发", "https://xhs.com/2")
        assert id1 != id2

    def test_empty_url_ok(self):
        job_id = _generate_xhs_job_id("字节跳动", "Python开发")
        assert len(job_id) == 16


class TestParseSalary:
    def test_standard_k_format(self):
        assert _parse_salary("15-25K") == (15000, 25000)

    def test_k_both_sides(self):
        assert _parse_salary("15K-25K") == (15000, 25000)

    def test_lowercase_k(self):
        assert _parse_salary("15k-25k") == (15000, 25000)

    def test_with_month_suffix(self):
        assert _parse_salary("15-25k/月") == (15000, 25000)

    def test_annual_wan(self):
        """Annual salary in 万 → divide by 12."""
        sal_min, sal_max = _parse_salary("15万-25万")
        assert sal_min == 12500
        assert sal_max == 20833

    def test_annual_w(self):
        sal_min, sal_max = _parse_salary("15w-25w")
        assert sal_min == 12500
        assert sal_max == 20833

    def test_plain_numbers(self):
        assert _parse_salary("15000-25000") == (15000, 25000)

    def test_tilde_separator(self):
        assert _parse_salary("15~25K") == (15000, 25000)

    def test_dao_separator(self):
        assert _parse_salary("15到25K") == (15000, 25000)

    def test_empty_string(self):
        assert _parse_salary("") == (0, 0)

    def test_unparseable(self):
        assert _parse_salary("面议") == (0, 0)

    def test_none_input(self):
        assert _parse_salary("None") == (0, 0)


class TestParseXhsJob:
    def test_valid_job(self):
        item = {
            "company": "字节跳动",
            "title": "Python开发工程师",
            "salary": "25-40K",
            "city": "上海",
            "experience": "3-5年",
            "education": "本科",
            "jd_text": "负责后端开发",
            "source_url": "https://www.xiaohongshu.com/explore/abc123",
        }
        job = parse_xhs_job(item)
        assert job is not None
        assert job.platform == "xhs"
        assert job.company == "字节跳动"
        assert job.title == "Python开发工程师"
        assert job.salary_min == 25000
        assert job.salary_max == 40000
        assert job.city == "上海"
        assert job.experience == "3-5年"
        assert job.education == "本科"
        assert job.jd_text == "负责后端开发"
        assert job.status == "new"
        assert job.raw_data["source_url"] == "https://www.xiaohongshu.com/explore/abc123"

    def test_missing_company(self):
        item = {"title": "Python开发", "salary": "15-25K"}
        assert parse_xhs_job(item) is None

    def test_missing_title(self):
        item = {"company": "字节跳动", "salary": "15-25K"}
        assert parse_xhs_job(item) is None

    def test_empty_company(self):
        item = {"company": "", "title": "Python开发"}
        assert parse_xhs_job(item) is None

    def test_whitespace_company(self):
        item = {"company": "  ", "title": "Python开发"}
        assert parse_xhs_job(item) is None

    def test_minimal_fields(self):
        item = {"company": "Test Co", "title": "Dev"}
        job = parse_xhs_job(item)
        assert job is not None
        assert job.company == "Test Co"
        assert job.title == "Dev"
        assert job.salary_min == 0
        assert job.salary_max == 0
        assert job.city == ""

    def test_url_fallback(self):
        """If source_url missing, fall back to url field."""
        item = {"company": "A", "title": "B", "url": "https://xhs.com/note/123"}
        job = parse_xhs_job(item)
        assert job is not None
        assert "xhs.com" in job.raw_data.get("url", "")

    def test_job_id_includes_url(self):
        """job_id is different when source_url differs."""
        item1 = {"company": "A", "title": "B", "source_url": "url1"}
        item2 = {"company": "A", "title": "B", "source_url": "url2"}
        j1 = parse_xhs_job(item1)
        j2 = parse_xhs_job(item2)
        assert j1.job_id != j2.job_id


class TestParseXhsJobs:
    def test_batch_parse(self):
        items = [
            {"company": "A公司", "title": "前端开发", "salary": "15-25K", "city": "北京"},
            {"company": "B公司", "title": "后端开发", "salary": "20-35K", "city": "上海"},
        ]
        jobs = parse_xhs_jobs(items)
        assert len(jobs) == 2
        assert jobs[0].company == "A公司"
        assert jobs[1].company == "B公司"

    def test_skips_invalid(self):
        items = [
            {"company": "A公司", "title": "前端开发"},
            {"company": "", "title": "无效"},
            {"title": "也无效"},
            {"company": "B公司", "title": "后端开发"},
        ]
        jobs = parse_xhs_jobs(items)
        assert len(jobs) == 2

    def test_empty_list(self):
        assert parse_xhs_jobs([]) == []
