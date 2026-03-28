"""Tests for XHS search adapter (rednote-mcp integration)."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot.adapters.xhs_search import (
    XHSSearchAdapter,
    _build_mcp_script,
    _extract_json_from_text,
    _parse_notes_text,
)
from jobpilot.models import Job


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_MCP_OUTPUT = """\
标题: 急招 AI产品经理 实习生
作者: 第二人生
内容: BASE上海 需要线下面试
需要有AI基础和实操经验
招2-3名AI产品经理实习
薪资200-300/天
#实习生 #ai #AI产品经理
点赞: 3
评论: 1
链接: https://www.xiaohongshu.com/explore/abc123
---
标题: AI产品经理的一天
作者: 分享达人
内容: 今天来分享一下AI产品经理的工作日常
早上9点到公司，先看数据看板
#产品经理日常 #工作分享
点赞: 50
评论: 10
链接: https://www.xiaohongshu.com/explore/def456
---
标题: 字节跳动招聘AI产品实习生
作者: HR小王
内容: 字节跳动AI产品团队招实习生
岗位：AI产品经理实习生
城市：上海
薪资：400/天
要求：
1. 本科及以上
2. 熟悉AI产品
3. 有实习经验优先
投递邮箱：hr@bytedance.com
点赞: 20
评论: 5
链接: https://www.xiaohongshu.com/explore/ghi789
---"""

SAMPLE_AI_EXTRACTION = [
    {
        "company": "第二人生",
        "title": "AI产品经理实习生",
        "salary": "200-300/天",
        "city": "上海",
        "experience": "",
        "education": "",
        "jd_text": "需要有AI基础和实操经验，招2-3名AI产品经理实习",
        "source_url": "https://www.xiaohongshu.com/explore/abc123",
    },
    {
        "company": "字节跳动",
        "title": "AI产品经理实习生",
        "salary": "400/天",
        "city": "上海",
        "experience": "",
        "education": "本科",
        "jd_text": "字节跳动AI产品团队招实习生\n1. 本科及以上\n2. 熟悉AI产品\n3. 有实习经验优先",
        "source_url": "https://www.xiaohongshu.com/explore/ghi789",
    },
]


# ---------------------------------------------------------------------------
# _parse_notes_text tests
# ---------------------------------------------------------------------------

class TestParseNotesText:
    def test_parses_multiple_notes(self):
        notes = _parse_notes_text(SAMPLE_MCP_OUTPUT)
        assert len(notes) == 3

    def test_extracts_title(self):
        notes = _parse_notes_text(SAMPLE_MCP_OUTPUT)
        assert notes[0]["title"] == "急招 AI产品经理 实习生"

    def test_extracts_author(self):
        notes = _parse_notes_text(SAMPLE_MCP_OUTPUT)
        assert notes[0]["author"] == "第二人生"

    def test_extracts_url(self):
        notes = _parse_notes_text(SAMPLE_MCP_OUTPUT)
        assert notes[0]["url"] == "https://www.xiaohongshu.com/explore/abc123"

    def test_extracts_multiline_content(self):
        notes = _parse_notes_text(SAMPLE_MCP_OUTPUT)
        assert "需要有AI基础" in notes[0]["content"]
        assert "200-300/天" in notes[0]["content"]

    def test_empty_input(self):
        notes = _parse_notes_text("")
        assert notes == []

    def test_single_note_no_separator(self):
        raw = "标题: Test\n作者: Author\n内容: Hello world\n链接: https://xhs.com/1"
        notes = _parse_notes_text(raw)
        assert len(notes) == 1
        assert notes[0]["title"] == "Test"

    def test_joined_separator(self):
        """Handle '---标题: ...' where separator and title are joined (real MCP output)."""
        raw = (
            "标题: First\n作者: A\n内容: Hello\n链接: https://xhs.com/1\n"
            "---标题: Second\n作者: B\n内容: World\n链接: https://xhs.com/2\n---"
        )
        notes = _parse_notes_text(raw)
        assert len(notes) == 2
        assert notes[0]["title"] == "First"
        assert notes[1]["title"] == "Second"


# ---------------------------------------------------------------------------
# _extract_json_from_text tests
# ---------------------------------------------------------------------------

class TestExtractJsonFromText:
    def test_raw_json(self):
        text = '[{"company": "A", "title": "B"}]'
        result = _extract_json_from_text(text)
        assert len(result) == 1
        assert result[0]["company"] == "A"

    def test_markdown_code_block(self):
        text = '```json\n[{"company": "A"}]\n```'
        result = _extract_json_from_text(text)
        assert len(result) == 1

    def test_embedded_json(self):
        text = 'Here are jobs:\n[{"company": "A"}]\nEnd.'
        result = _extract_json_from_text(text)
        assert len(result) == 1

    def test_invalid_json(self):
        result = _extract_json_from_text("not json at all")
        assert result == []

    def test_empty_array(self):
        result = _extract_json_from_text("[]")
        assert result == []

    def test_truncated_json(self):
        """Handle truncated JSON from max_tokens cutoff."""
        text = '[{"company": "A", "title": "PM"}, {"company": "B", "ti'
        result = _extract_json_from_text(text)
        assert len(result) == 1
        assert result[0]["company"] == "A"


# ---------------------------------------------------------------------------
# _build_mcp_script tests
# ---------------------------------------------------------------------------

class TestBuildMCPScript:
    def test_contains_keywords(self):
        script = _build_mcp_script("/path/to/mcp", "AI产品", 10)
        assert "AI产品" in script
        assert "limit: 10" in script

    def test_escapes_quotes_in_keywords(self):
        script = _build_mcp_script("/path/to/mcp", 'test "quotes"', 5)
        assert 'test \\"quotes\\"' in script

    def test_contains_stdio_flag(self):
        script = _build_mcp_script("/path/to/mcp", "test", 10)
        assert "--stdio" in script


# ---------------------------------------------------------------------------
# XHSSearchAdapter tests
# ---------------------------------------------------------------------------

class TestXHSSearchAdapter:
    def test_platform_name(self):
        adapter = XHSSearchAdapter()
        assert adapter.platform_name == "xhs"

    def test_get_job_detail_returns_none(self):
        adapter = XHSSearchAdapter()
        assert adapter.get_job_detail("any_id") is None

    @patch("jobpilot.adapters.xhs_search._extract_jobs_via_ai")
    @patch("jobpilot.adapters.xhs_search.call_mcp_search")
    def test_search_end_to_end(self, mock_mcp, mock_ai):
        """Full search: MCP → notes → AI → jobs."""
        mock_mcp.return_value = SAMPLE_MCP_OUTPUT
        mock_ai.return_value = SAMPLE_AI_EXTRACTION

        adapter = XHSSearchAdapter()
        jobs = adapter.search("AI产品经理")

        assert len(jobs) == 2
        assert all(isinstance(j, Job) for j in jobs)
        assert all(j.platform == "xhs" for j in jobs)
        assert jobs[0].company in ("第二人生", "字节跳动")

    @patch("jobpilot.adapters.xhs_search.call_mcp_search")
    def test_search_mcp_not_available(self, mock_mcp):
        """Should return empty list if rednote-mcp not found."""
        mock_mcp.side_effect = FileNotFoundError("not found")

        adapter = XHSSearchAdapter()
        jobs = adapter.search("AI产品")
        assert jobs == []

    @patch("jobpilot.adapters.xhs_search.call_mcp_search")
    def test_search_mcp_timeout(self, mock_mcp):
        """Should return empty list on timeout."""
        import subprocess
        mock_mcp.side_effect = subprocess.TimeoutExpired(cmd="node", timeout=120)

        adapter = XHSSearchAdapter()
        jobs = adapter.search("AI产品")
        assert jobs == []

    @patch("jobpilot.adapters.xhs_search.call_mcp_search")
    def test_search_empty_results(self, mock_mcp):
        """Should return empty list when MCP returns nothing."""
        mock_mcp.return_value = ""

        adapter = XHSSearchAdapter()
        jobs = adapter.search("AI产品")
        assert jobs == []

    @patch("jobpilot.adapters.xhs_search._extract_jobs_via_ai")
    @patch("jobpilot.adapters.xhs_search.call_mcp_search")
    def test_search_no_jobs_in_notes(self, mock_mcp, mock_ai):
        """AI finds no job posts in notes."""
        mock_mcp.return_value = SAMPLE_MCP_OUTPUT
        mock_ai.return_value = []

        adapter = XHSSearchAdapter()
        jobs = adapter.search("AI产品")
        assert jobs == []

    @patch("jobpilot.adapters.xhs_search._extract_jobs_via_ai")
    @patch("jobpilot.adapters.xhs_search.call_mcp_search")
    def test_search_appends_city_to_keywords(self, mock_mcp, mock_ai):
        """City from filters should be appended to search keywords."""
        mock_mcp.return_value = ""
        mock_ai.return_value = []

        from jobpilot.adapters.base import SearchFilters

        adapter = XHSSearchAdapter()
        adapter.search("AI产品", SearchFilters(city="上海"))

        # Check that city was appended to keywords
        call_args = mock_mcp.call_args
        assert "上海" in call_args[0][0]

    @patch("jobpilot.adapters.xhs_search._extract_jobs_via_ai")
    @patch("jobpilot.adapters.xhs_search.call_mcp_search")
    def test_search_dedup_via_job_id(self, mock_mcp, mock_ai):
        """Jobs from same company+title should have same job_id (dedup)."""
        mock_mcp.return_value = SAMPLE_MCP_OUTPUT
        # Return two identical job dicts
        mock_ai.return_value = [
            {"company": "TestCo", "title": "PM", "source_url": "https://xhs.com/1"},
            {"company": "TestCo", "title": "PM", "source_url": "https://xhs.com/1"},
        ]

        adapter = XHSSearchAdapter()
        jobs = adapter.search("test")
        # Both have same job_id because same company+title+url
        assert jobs[0].job_id == jobs[1].job_id


# ---------------------------------------------------------------------------
# _extract_jobs_via_ai tests (mocked API)
# ---------------------------------------------------------------------------

class TestExtractJobsViaAI:
    @patch("jobpilot.adapters.xhs_search.config")
    def test_no_api_key_returns_empty(self, mock_config):
        """Without API key, should return empty list."""
        from jobpilot.adapters.xhs_search import _extract_jobs_via_ai

        mock_config.ANTHROPIC_API_KEY = ""
        result = _extract_jobs_via_ai([{"title": "test", "content": "test"}], "test")
        assert result == []

    @patch("jobpilot.adapters.xhs_search.config")
    def test_api_error_returns_empty(self, mock_config):
        """API error should return empty list, not crash."""
        from jobpilot.adapters.xhs_search import _extract_jobs_via_ai

        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"

        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = Exception("API error")
            result = _extract_jobs_via_ai([{"title": "test"}], "test")
            assert result == []
