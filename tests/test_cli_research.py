"""Integration tests for the `research` CLI command."""

from unittest.mock import patch

from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.research import ResearchResult

runner = CliRunner()


@patch("jobpilot.research.research")
def test_research_prints_results(mock_research):
    mock_research.return_value = [
        ResearchResult(
            title="AI产品经理面经",
            summary="常见题：估算、北极星指标设计",
            url="https://xhs.com/x",
            source="xhs",
            author="学姐",
        ),
    ]
    result = runner.invoke(app, ["research", "AI产品实习面试题", "--channel", "xhs"])
    assert result.exit_code == 0
    assert "AI产品经理面经" in result.output
    assert "北极星" in result.output
    assert "共 1 条资料" in result.output


@patch("jobpilot.research.research")
def test_research_no_results(mock_research):
    mock_research.return_value = []
    result = runner.invoke(app, ["research", "不存在的关键词", "--channel", "xhs"])
    assert result.exit_code == 0
    assert "没查到相关资料" in result.output


def test_research_unknown_channel():
    result = runner.invoke(app, ["research", "x", "--channel", "bogus"])
    assert result.exit_code == 1
    assert "未知渠道" in result.output


@patch("jobpilot.cli.config")
@patch("jobpilot.research.research")
def test_research_warns_when_web_without_key(mock_research, mock_config):
    mock_config.ANTHROPIC_API_KEY = ""
    mock_research.return_value = []
    result = runner.invoke(app, ["research", "x", "--channel", "web"])
    assert result.exit_code == 0
    assert "web 检索跳过" in result.output


@patch("jobpilot.research.research")
def test_research_saves_to_file(mock_research, tmp_path):
    mock_research.return_value = [
        ResearchResult(title="面经", summary="题目1", url="https://x.com", source="web"),
    ]
    out = tmp_path / "research.md"
    result = runner.invoke(
        app, ["research", "AI产品", "--channel", "web", "-o", str(out)]
    )
    assert result.exit_code == 0
    assert out.exists()
    assert "面经" in out.read_text(encoding="utf-8")
