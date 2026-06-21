"""Tests for the research module — 军师 on-demand 资料检索 (面试题/面经/相关帖)."""

import dataclasses
from unittest.mock import MagicMock, patch

import pytest

from jobpilot.research import (
    ResearchResult,
    _distill_notes_via_ai,
    research,
    research_web,
    research_xhs,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_MCP_OUTPUT = """\
标题: AI产品经理面试真题汇总
作者: 上岸学姐
内容: 分享我面字节AI产品实习的面经
1. 如何评估一个大模型功能的好坏？
2. 举一个你做过的需求，怎么定北极星指标
#AI产品 #面经 #实习
点赞: 120
评论: 30
链接: https://www.xiaohongshu.com/explore/aaa111
---
标题: 减肥餐分享
作者: 健身达人
内容: 今天吃的鸡胸肉沙拉
#减肥 #健康
点赞: 5
评论: 1
链接: https://www.xiaohongshu.com/explore/bbb222
---"""

SAMPLE_DISTILLED = [
    {
        "title": "AI产品经理面试真题汇总",
        "summary": "字节AI产品实习面经：1) 如何评估大模型功能好坏 2) 怎么定北极星指标",
        "url": "https://www.xiaohongshu.com/explore/aaa111",
        "author": "上岸学姐",
    },
]


def _fake_web_response(json_text: str) -> MagicMock:
    """Build a fake Anthropic response whose content yields json_text."""
    block = MagicMock()
    block.type = "text"
    block.text = json_text
    resp = MagicMock()
    resp.content = [block]
    return resp


# ---------------------------------------------------------------------------
# ResearchResult dataclass
# ---------------------------------------------------------------------------

class TestResearchResult:
    def test_is_frozen(self):
        r = ResearchResult(title="t", summary="s")
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.title = "x"  # type: ignore[misc]

    def test_defaults(self):
        r = ResearchResult(title="t", summary="s")
        assert r.url == ""
        assert r.source == ""
        assert r.author == ""


# ---------------------------------------------------------------------------
# research_xhs
# ---------------------------------------------------------------------------

class TestResearchXHS:
    @patch("jobpilot.research.config")
    @patch("jobpilot.research._distill_notes_via_ai")
    @patch("jobpilot.research.call_mcp_search")
    def test_end_to_end_with_api(self, mock_mcp, mock_distill, mock_config):
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_mcp.return_value = SAMPLE_MCP_OUTPUT
        mock_distill.return_value = [
            ResearchResult(
                title=SAMPLE_DISTILLED[0]["title"],
                summary=SAMPLE_DISTILLED[0]["summary"],
                url=SAMPLE_DISTILLED[0]["url"],
                author=SAMPLE_DISTILLED[0]["author"],
                source="xhs",
            )
        ]
        results = research_xhs("AI产品实习面试题")
        assert len(results) == 1
        assert all(isinstance(r, ResearchResult) for r in results)
        assert results[0].source == "xhs"
        assert "北极星" in results[0].summary

    @patch("jobpilot.research.config")
    @patch("jobpilot.research.call_mcp_search")
    def test_no_api_key_falls_back_to_raw_notes(self, mock_mcp, mock_config):
        """Without API key we still surface the raw notes, just undistilled."""
        mock_mcp.return_value = SAMPLE_MCP_OUTPUT
        mock_config.ANTHROPIC_API_KEY = ""
        results = research_xhs("AI产品实习面试题")
        assert len(results) == 2  # both notes returned raw
        assert all(r.source == "xhs" for r in results)
        assert results[0].url.startswith("https://")

    @patch("jobpilot.research.call_mcp_search")
    def test_mcp_not_available(self, mock_mcp):
        mock_mcp.side_effect = FileNotFoundError("not found")
        assert research_xhs("x") == []

    @patch("jobpilot.research.call_mcp_search")
    def test_timeout(self, mock_mcp):
        import subprocess

        mock_mcp.side_effect = subprocess.TimeoutExpired(cmd="node", timeout=120)
        assert research_xhs("x") == []

    @patch("jobpilot.research.call_mcp_search")
    def test_empty_output(self, mock_mcp):
        mock_mcp.return_value = ""
        assert research_xhs("x") == []

    @patch("jobpilot.research.call_mcp_search")
    def test_runtime_error(self, mock_mcp):
        mock_mcp.side_effect = RuntimeError("mcp failed")
        assert research_xhs("x") == []


# ---------------------------------------------------------------------------
# research_web
# ---------------------------------------------------------------------------

class TestResearchWeb:
    @patch("jobpilot.research.config")
    def test_no_api_key_returns_empty(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = ""
        assert research_web("AI产品实习面试题") == []

    @patch("jobpilot.research.config")
    def test_with_api_extracts_results(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        payload = (
            '[{"title": "牛客AI产品面经", "summary": "常见题：估算、指标设计",'
            ' "url": "https://nowcoder.com/x"}]'
        )
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = _fake_web_response(payload)
            results = research_web("AI产品实习面试题")
        assert len(results) == 1
        assert results[0].source == "web"
        assert results[0].title == "牛客AI产品面经"
        assert results[0].url == "https://nowcoder.com/x"

    @patch("jobpilot.research.config")
    def test_api_error_returns_empty(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = Exception("boom")
            assert research_web("x") == []

    @patch("jobpilot.research.config")
    def test_skips_items_without_title(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        payload = '[{"summary": "no title here", "url": "https://x.com"}]'
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = _fake_web_response(payload)
            assert research_web("x") == []


# ---------------------------------------------------------------------------
# _distill_notes_via_ai
# ---------------------------------------------------------------------------

class TestDistillNotesViaAI:
    @patch("jobpilot.research.config")
    def test_no_api_key_returns_empty(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = ""
        assert _distill_notes_via_ai([{"title": "t", "content": "c"}], "q") == []

    @patch("jobpilot.research.config")
    def test_api_error_returns_empty(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = Exception("boom")
            assert _distill_notes_via_ai([{"title": "t"}], "q") == []

    @patch("jobpilot.research.config")
    def test_distills_to_results(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        import json as _json

        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = _fake_web_response(
                _json.dumps(SAMPLE_DISTILLED, ensure_ascii=False)
            )
            results = _distill_notes_via_ai(
                [{"title": "AI产品经理面试真题汇总", "content": "..."}], "q"
            )
        assert len(results) == 1
        assert results[0].source == "xhs"
        assert results[0].author == "上岸学姐"

    @staticmethod
    def _content_blocks_from_call(mock_cls) -> list:
        kwargs = mock_cls.return_value.messages.create.call_args.kwargs
        return kwargs["messages"][0]["content"]

    @patch("jobpilot.research.config")
    def test_passes_images_as_image_blocks(self, mock_config):
        """笔记里有 images → 多模态调用，附 image block。"""
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = _fake_web_response("[]")
            _distill_notes_via_ai(
                [{
                    "title": "面经",
                    "content": "图里",
                    "images": ["https://cdn.xhs.com/a.jpg", "https://cdn.xhs.com/b.jpg"],
                }],
                "AI产品",
            )
            blocks = self._content_blocks_from_call(mock_cls)
        image_blocks = [b for b in blocks if b.get("type") == "image"]
        assert len(image_blocks) == 2
        assert image_blocks[0]["source"]["url"] == "https://cdn.xhs.com/a.jpg"

    @patch("jobpilot.research.config")
    def test_caps_images_per_note(self, mock_config):
        """每条笔记最多取 MAX_IMAGES_PER_NOTE=3 张。"""
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = _fake_web_response("[]")
            _distill_notes_via_ai(
                [{
                    "title": "面经",
                    "content": "x",
                    "images": [f"https://x.com/{i}.jpg" for i in range(10)],
                }],
                "q",
            )
            blocks = self._content_blocks_from_call(mock_cls)
        assert len([b for b in blocks if b.get("type") == "image"]) == 3

    @patch("jobpilot.research.config")
    def test_caps_total_images(self, mock_config):
        """跨笔记的全局图片预算 MAX_IMAGES_PER_REQUEST=12 不会被突破。"""
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        notes = [
            {"title": f"n{i}", "content": "x", "images": [f"https://x.com/{i}-{j}.jpg" for j in range(3)]}
            for i in range(6)  # 6 notes * 3 imgs = 18 > 12
        ]
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = _fake_web_response("[]")
            _distill_notes_via_ai(notes, "q")
            blocks = self._content_blocks_from_call(mock_cls)
        assert len([b for b in blocks if b.get("type") == "image"]) == 12

    @patch("jobpilot.research.config")
    def test_no_images_means_no_image_blocks(self, mock_config):
        """老路径（无 images）必须依然工作、不附带任何 image block。"""
        mock_config.ANTHROPIC_API_KEY = "sk-test"
        mock_config.ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = _fake_web_response("[]")
            _distill_notes_via_ai([{"title": "t", "content": "c"}], "q")
            blocks = self._content_blocks_from_call(mock_cls)
        assert [b for b in blocks if b.get("type") == "image"] == []


# ---------------------------------------------------------------------------
# research() dispatch
# ---------------------------------------------------------------------------

class TestResearchDispatch:
    @patch("jobpilot.research.research_web")
    @patch("jobpilot.research.research_xhs")
    def test_channel_xhs_only(self, mock_xhs, mock_web):
        mock_xhs.return_value = [ResearchResult(title="a", summary="s", source="xhs")]
        research("q", channel="xhs")
        mock_xhs.assert_called_once()
        mock_web.assert_not_called()

    @patch("jobpilot.research.research_web")
    @patch("jobpilot.research.research_xhs")
    def test_channel_web_only(self, mock_xhs, mock_web):
        mock_web.return_value = [ResearchResult(title="a", summary="s", source="web")]
        research("q", channel="web")
        mock_web.assert_called_once()
        mock_xhs.assert_not_called()

    @patch("jobpilot.research.research_web")
    @patch("jobpilot.research.research_xhs")
    def test_channel_both_merges(self, mock_xhs, mock_web):
        mock_xhs.return_value = [ResearchResult(title="x", summary="s", source="xhs")]
        mock_web.return_value = [ResearchResult(title="w", summary="s", source="web")]
        results = research("q", channel="both")
        assert len(results) == 2
        sources = {r.source for r in results}
        assert sources == {"xhs", "web"}
