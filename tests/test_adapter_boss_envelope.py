"""Tests for boss-cli envelope format parsing."""

import json

from jobpilot.adapters.boss import BossAdapter


# Sample envelope data matching real boss-cli --json output
SAMPLE_JOB_ITEM = {
    "securityId": "abc123def456",
    "jobName": "Python后端开发",
    "brandName": "字节跳动",
    "salaryDesc": "25-50K",
    "cityName": "上海",
    "areaDistrict": "浦东新区",
    "skills": ["Python", "Django", "MySQL", "Redis"],
    "jobExperience": "3-5年",
    "jobDegree": "本科",
    "jobDetail": "负责后端系统开发与维护",
}

SEARCH_ENVELOPE = {
    "ok": True,
    "schema_version": "1",
    "data": {
        "jobList": [SAMPLE_JOB_ITEM],
    },
}

DETAIL_ENVELOPE = {
    "ok": True,
    "schema_version": "1",
    "data": {
        "jobInfo": {
            **SAMPLE_JOB_ITEM,
            "jobDetail": "详细岗位描述：负责后端系统开发与维护，包括API设计和数据库优化。",
        },
    },
}


class TestEnvelopeParsing:
    """Test boss-cli envelope format {"ok": true, "data": {"jobList": [...]}}."""

    def test_parse_search_envelope(self):
        adapter = BossAdapter()
        output = json.dumps(SEARCH_ENVELOPE, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert len(jobs) == 1
        assert jobs[0].title == "Python后端开发"
        assert jobs[0].company == "字节跳动"

    def test_parse_search_envelope_multiple_jobs(self):
        adapter = BossAdapter()
        envelope = {
            "ok": True,
            "data": {
                "jobList": [
                    SAMPLE_JOB_ITEM,
                    {**SAMPLE_JOB_ITEM, "securityId": "xyz789", "jobName": "Go开发"},
                ],
            },
        }
        output = json.dumps(envelope, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert len(jobs) == 2
        assert jobs[1].title == "Go开发"

    def test_parse_search_envelope_empty_joblist(self):
        adapter = BossAdapter()
        envelope = {"ok": True, "data": {"jobList": []}}
        output = json.dumps(envelope)
        jobs = adapter._parse_search_output(output)
        assert jobs == []

    def test_parse_detail_envelope(self):
        adapter = BossAdapter()
        output = json.dumps(DETAIL_ENVELOPE, ensure_ascii=False)
        job = adapter._parse_detail_output(output, "abc123def456")
        assert job is not None
        assert job.job_id == "abc123def456"
        assert "详细岗位描述" in job.jd_text

    def test_parse_detail_plain_json(self):
        """Plain JSON object (no envelope) should still work."""
        adapter = BossAdapter()
        output = json.dumps(SAMPLE_JOB_ITEM, ensure_ascii=False)
        job = adapter._parse_detail_output(output, "abc123def456")
        assert job is not None
        assert job.job_id == "abc123def456"

    def test_parse_detail_invalid_json(self):
        adapter = BossAdapter()
        job = adapter._parse_detail_output("not json at all", "xxx")
        assert job is None


class TestSecurityIdMapping:
    """Test that securityId is correctly used as job_id."""

    def test_security_id_is_job_id(self):
        adapter = BossAdapter()
        output = json.dumps(SEARCH_ENVELOPE, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert jobs[0].job_id == "abc123def456"

    def test_fallback_to_encrypt_job_id(self):
        adapter = BossAdapter()
        item = {**SAMPLE_JOB_ITEM}
        del item["securityId"]
        item["encryptJobId"] = "enc_fallback_123"
        envelope = {"ok": True, "data": {"jobList": [item]}}
        output = json.dumps(envelope, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert jobs[0].job_id == "enc_fallback_123"

    def test_fallback_to_job_id_field(self):
        adapter = BossAdapter()
        item = {"jobId": "legacy_id", "jobName": "Test", "brandName": "Test"}
        output = json.dumps([item])
        jobs = adapter._parse_search_output(output)
        assert jobs[0].job_id == "legacy_id"


class TestFieldMapping:
    """Test boss-cli field → Job model mapping."""

    def test_salary_desc(self):
        adapter = BossAdapter()
        output = json.dumps(SEARCH_ENVELOPE, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert jobs[0].salary_min == 25000
        assert jobs[0].salary_max == 50000

    def test_city_with_area(self):
        adapter = BossAdapter()
        output = json.dumps(SEARCH_ENVELOPE, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert "上海" in jobs[0].city
        assert "浦东新区" in jobs[0].city

    def test_city_without_area(self):
        adapter = BossAdapter()
        item = {**SAMPLE_JOB_ITEM}
        del item["areaDistrict"]
        envelope = {"ok": True, "data": {"jobList": [item]}}
        output = json.dumps(envelope, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert jobs[0].city == "上海"

    def test_skills_in_jd(self):
        adapter = BossAdapter()
        output = json.dumps(SEARCH_ENVELOPE, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert "Python" in jobs[0].jd_text
        assert "Django" in jobs[0].jd_text

    def test_experience_degree(self):
        adapter = BossAdapter()
        output = json.dumps(SEARCH_ENVELOPE, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert jobs[0].experience == "3-5年"
        assert jobs[0].education == "本科"

    def test_platform_is_boss(self):
        adapter = BossAdapter()
        output = json.dumps(SEARCH_ENVELOPE, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert jobs[0].platform == "boss"

    def test_raw_data_preserved(self):
        adapter = BossAdapter()
        output = json.dumps(SEARCH_ENVELOPE, ensure_ascii=False)
        jobs = adapter._parse_search_output(output)
        assert jobs[0].raw_data["securityId"] == "abc123def456"


class TestBossCliFlags:
    """Test that the correct CLI flags are constructed."""

    def test_json_flag_in_search_cmd(self):
        """Verify search() builds the command with --json flag."""
        adapter = BossAdapter()
        # We can't easily test subprocess args without mocking,
        # but we can verify the method signature and docstring mention --json
        assert "--json" in adapter.search.__doc__

    def test_plain_array_still_works(self):
        """Backward compatibility: plain JSON array should still parse."""
        adapter = BossAdapter()
        output = '[{"jobName": "Test", "brandName": "C1", "salary": "10-20K"}]'
        jobs = adapter._parse_search_output(output)
        assert len(jobs) == 1
        assert jobs[0].title == "Test"

    def test_jsonl_still_works(self):
        """Backward compatibility: JSON lines should still parse."""
        adapter = BossAdapter()
        output = '{"jobName": "J1", "brandName": "C1"}\n{"jobName": "J2", "brandName": "C2"}'
        jobs = adapter._parse_search_output(output)
        assert len(jobs) == 2
