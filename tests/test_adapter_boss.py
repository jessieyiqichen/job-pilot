"""Tests for Boss adapter."""

from unittest.mock import patch

from jobpilot.adapters.base import SearchFilters
from jobpilot.adapters.boss import BossAdapter, _parse_salary


class TestParseSalary:
    def test_standard_k(self):
        assert _parse_salary("15-25K") == (15000, 25000)

    def test_lowercase_k(self):
        assert _parse_salary("15-25k") == (15000, 25000)

    def test_empty(self):
        assert _parse_salary("") == (0, 0)

    def test_no_k(self):
        assert _parse_salary("150-250") == (150, 250)


class TestBossAdapter:
    def test_platform_name(self):
        adapter = BossAdapter()
        assert adapter.platform_name == "boss"

    def test_returns_empty_when_boss_cli_not_found(self):
        adapter = BossAdapter()
        # boss-cli not found → return empty list (triggers websearch fallback)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            jobs = adapter.search("Python开发", SearchFilters(city="上海"))
        assert jobs == []

    def test_parse_search_output_json_array(self):
        adapter = BossAdapter()
        output = '[{"jobName": "Python开发", "brandName": "Test", "salary": "15-25K", "cityName": "上海"}]'
        jobs = adapter._parse_search_output(output)
        assert len(jobs) == 1
        assert jobs[0].title == "Python开发"

    def test_parse_search_output_jsonl(self):
        adapter = BossAdapter()
        output = '{"jobName": "Job1", "brandName": "C1"}\n{"jobName": "Job2", "brandName": "C2"}'
        jobs = adapter._parse_search_output(output)
        assert len(jobs) == 2
