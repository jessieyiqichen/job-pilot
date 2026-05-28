"""Integration tests for the `pipeline-all` CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.pipeline import PipelineResult, StageResult

runner = CliRunner()


@patch("jobpilot.cli._get_db")
@patch("jobpilot.ai.scorer._load_preferences")
@patch("jobpilot.pipeline.run_pipeline")
def test_pipeline_all_invokes_run_pipeline(mock_run, mock_prefs, mock_db):
    mock_prefs.return_value = {"career_track": ["AI产品经理"]}
    mock_db.return_value = MagicMock()
    mock_run.return_value = PipelineResult(
        stages=(
            StageResult("搜索", True, "入库 10 个岗位"),
            StageResult("打分", True, "启发式秒评 10 个，API 精评 5 个"),
            StageResult("定制简历", True, "定制 5/5 份简历"),
            StageResult("日报", True, "已保存: /tmp/report.md"),
        ),
        found=10,
        scored=10,
        refined=5,
        tailored=5,
        report_path="/tmp/report.md",
    )

    result = runner.invoke(app, ["pipeline-all"])

    assert result.exit_code == 0
    mock_run.assert_called_once()
    # config derived from preferences when no --keywords given
    cfg = mock_run.call_args[0][1]
    assert cfg.keywords == ("AI产品经理",)
    assert "入库 10" in result.output
    assert "/tmp/report.md" in result.output


@patch("jobpilot.cli._get_db")
@patch("jobpilot.ai.scorer._load_preferences")
@patch("jobpilot.pipeline.run_pipeline")
def test_pipeline_all_respects_keyword_override(mock_run, mock_prefs, mock_db):
    mock_prefs.return_value = {"career_track": ["AI产品经理"]}
    mock_db.return_value = MagicMock()
    mock_run.return_value = PipelineResult(stages=())

    result = runner.invoke(
        app, ["pipeline-all", "--keywords", "大模型产品,AIGC实习", "--tailor", "0"]
    )

    assert result.exit_code == 0
    cfg = mock_run.call_args[0][1]
    assert cfg.keywords == ("大模型产品", "AIGC实习")
    assert cfg.tailor_top == 0
