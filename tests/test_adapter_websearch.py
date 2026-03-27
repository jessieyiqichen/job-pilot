"""Tests for WebSearch adapter."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from jobpilot.adapters.base import SearchFilters
from jobpilot.adapters.websearch import (
    WebSearchAdapter,
    _extract_json_from_text,
    _generate_job_id,
)


class TestGenerateJobId:
    def test_deterministic(self):
        """Same company+title always produces the same ID."""
        id1 = _generate_job_id("字节跳动", "Python开发")
        id2 = _generate_job_id("字节跳动", "Python开发")
        assert id1 == id2
        assert len(id1) == 16

    def test_different_inputs(self):
        """Different company+title produces different IDs."""
        id1 = _generate_job_id("字节跳动", "Python开发")
        id2 = _generate_job_id("阿里巴巴", "Python开发")
        assert id1 != id2


class TestExtractJson:
    def test_raw_json_array(self):
        text = '[{"company": "Test"}]'
        result = _extract_json_from_text(text)
        assert len(result) == 1
        assert result[0]["company"] == "Test"

    def test_markdown_code_block(self):
        text = '```json\n[{"company": "Test"}]\n```'
        result = _extract_json_from_text(text)
        assert len(result) == 1

    def test_embedded_array(self):
        text = 'Here are the results:\n[{"company": "Test"}]\nDone.'
        result = _extract_json_from_text(text)
        assert len(result) == 1

    def test_no_json(self):
        text = "No jobs found."
        result = _extract_json_from_text(text)
        assert result == []


class TestWebSearchAdapter:
    def test_platform_name(self):
        adapter = WebSearchAdapter()
        assert adapter.platform_name == "websearch"

    def test_get_job_detail_returns_none(self):
        adapter = WebSearchAdapter()
        assert adapter.get_job_detail("anything") is None

    @patch("jobpilot.adapters.websearch.config")
    def test_search_no_api_key(self, mock_config):
        """No API key → return empty list without crashing."""
        mock_config.ANTHROPIC_API_KEY = ""
        adapter = WebSearchAdapter()
        jobs = adapter.search("Python开发", SearchFilters(city="上海"))
        assert jobs == []

    @patch("jobpilot.adapters.websearch.config")
    def test_search_extracts_jobs(self, mock_config):
        """Mock Anthropic API response → parse into Job list."""
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        mock_config.DEFAULT_CITY = "上海"

        fake_jobs = [
            {
                "company": "字节跳动",
                "title": "AI工程师",
                "salary": "30-50K",
                "city": "上海",
                "experience": "3-5年",
                "education": "本科",
                "jd_text": "负责AI模型开发",
                "source_url": "https://example.com/job/1",
            },
            {
                "company": "阿里巴巴",
                "title": "算法工程师",
                "salary": "25-40K",
                "city": "上海",
                "experience": "3-5年",
                "education": "硕士",
                "jd_text": "推荐算法优化",
                "source_url": "https://example.com/job/2",
            },
        ]

        mock_response = MagicMock()
        mock_response.content = [
            SimpleNamespace(type="text", text=json.dumps(fake_jobs, ensure_ascii=False))
        ]

        with patch("jobpilot.adapters.websearch.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client

            adapter = WebSearchAdapter()
            jobs = adapter.search("AI", SearchFilters(city="上海"))

        assert len(jobs) == 2
        assert jobs[0].platform == "websearch"
        assert jobs[0].company == "字节跳动"
        assert jobs[0].title == "AI工程师"
        assert jobs[0].salary_min == 30000
        assert jobs[0].salary_max == 50000
        assert jobs[0].city == "上海"
        assert jobs[0].jd_text == "负责AI模型开发"
        assert jobs[0].raw_data["source_url"] == "https://example.com/job/1"
        assert jobs[1].company == "阿里巴巴"

    @patch("jobpilot.adapters.websearch.config")
    def test_search_api_error(self, mock_config):
        """API error → return empty list, no crash."""
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        mock_config.DEFAULT_CITY = "上海"

        with patch("jobpilot.adapters.websearch.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.side_effect = RuntimeError("API down")

            adapter = WebSearchAdapter()
            jobs = adapter.search("AI", SearchFilters(city="上海"))

        assert jobs == []


class TestCliFallback:
    """Test that CLI search triggers websearch fallback when boss returns few results."""

    @patch("jobpilot.cli._get_db")
    @patch("jobpilot.adapters.websearch.WebSearchAdapter.search")
    @patch("jobpilot.adapters.boss.BossAdapter.search")
    def test_fallback_triggers_when_boss_empty(
        self, mock_boss_search, mock_ws_search, mock_get_db
    ):
        from typer.testing import CliRunner

        from jobpilot.cli import app
        from jobpilot.models import Job

        # Boss returns 0 jobs
        mock_boss_search.return_value = []

        # Websearch returns 1 job
        web_job = Job(
            platform="websearch",
            job_id="web001",
            title="AI工程师",
            company="测试公司",
            salary_min=20000,
            salary_max=30000,
            city="上海",
        )
        mock_ws_search.return_value = [web_job]

        mock_db = MagicMock()
        mock_db.upsert_jobs.return_value = 1
        mock_get_db.return_value = mock_db

        runner = CliRunner()
        result = runner.invoke(app, ["search", "AI startup", "--city", "上海"])

        assert result.exit_code == 0
        mock_ws_search.assert_called_once()
        assert "Web" in result.output or "web" in result.output

    @patch("jobpilot.cli._get_db")
    @patch("jobpilot.adapters.boss.BossAdapter.search")
    def test_no_fallback_when_enough_results(
        self, mock_boss_search, mock_get_db
    ):
        from typer.testing import CliRunner

        from jobpilot.cli import app
        from jobpilot.models import Job

        # Boss returns 5 jobs (above threshold)
        boss_jobs = [
            Job(
                platform="boss",
                job_id=f"boss_{i}",
                title=f"Python开发{i}",
                company=f"公司{i}",
                salary_min=15000,
                salary_max=25000,
                city="北京",
            )
            for i in range(5)
        ]
        mock_boss_search.return_value = boss_jobs

        mock_db = MagicMock()
        mock_db.upsert_jobs.return_value = 5
        mock_get_db.return_value = mock_db

        runner = CliRunner()
        result = runner.invoke(app, ["search", "Python开发", "--city", "北京"])

        assert result.exit_code == 0
        assert "web 搜索" not in result.output.lower()
