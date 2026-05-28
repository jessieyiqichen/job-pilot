"""Tests for the end-to-end automation pipeline (pipeline.py)."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot import pipeline
from jobpilot.pipeline import (
    DEFAULT_PLATFORMS,
    PipelineConfig,
    StageResult,
    build_config,
    default_keywords,
    run_pipeline,
)


# ----------------------------------------------------------------------
# default_keywords / build_config
# ----------------------------------------------------------------------


def test_default_keywords_from_career_track():
    prefs = {"career_track": ["AI产品经理", "产品经理"]}
    assert default_keywords(prefs) == ("AI产品经理", "产品经理")


def test_default_keywords_dedupes_preserving_order():
    prefs = {"career_track": ["AI产品经理", "AI产品经理", "产品经理"]}
    assert default_keywords(prefs) == ("AI产品经理", "产品经理")


def test_default_keywords_fallback_when_empty():
    assert default_keywords({}) == ("AI产品经理",)
    assert default_keywords({"career_track": []}) == ("AI产品经理",)


def test_build_config_uses_defaults():
    cfg = build_config({"career_track": ["产品经理"]})
    assert cfg.keywords == ("产品经理",)
    assert cfg.platforms == DEFAULT_PLATFORMS
    assert cfg.tailor_top == 5


def test_build_config_overrides():
    cfg = build_config(
        {},
        keywords=["大模型产品"],
        city="深圳",
        platforms=["websearch"],
        refine_top=3,
        tailor_top=2,
    )
    assert cfg.keywords == ("大模型产品",)
    assert cfg.city == "深圳"
    assert cfg.platforms == ("websearch",)
    assert cfg.refine_top == 3
    assert cfg.tailor_top == 2


# ----------------------------------------------------------------------
# search stage
# ----------------------------------------------------------------------


@patch("jobpilot.adapters.xhs_search.XHSSearchAdapter")
@patch("jobpilot.adapters.websearch.WebSearchAdapter")
def test_search_stage_aggregates_counts(mock_web, mock_xhs):
    mock_web.return_value.search.return_value = ["j1", "j2"]
    mock_xhs.return_value.search.return_value = ["j3"]
    db = MagicMock()
    db.upsert_jobs.side_effect = lambda jobs: len(jobs)

    cfg = PipelineConfig(keywords=("kw",), platforms=("websearch", "xhs"))
    result, count = pipeline._search_stage(db, cfg)

    assert result.ok is True
    assert count == 3  # 2 from web + 1 from xhs


@patch("jobpilot.adapters.xhs_search.XHSSearchAdapter")
@patch("jobpilot.adapters.websearch.WebSearchAdapter")
def test_search_stage_isolates_platform_failure(mock_web, mock_xhs):
    """One platform raising must not stop the other from contributing."""
    mock_web.return_value.search.return_value = ["j1", "j2"]
    mock_xhs.return_value.search.side_effect = RuntimeError("cookies expired")
    db = MagicMock()
    db.upsert_jobs.side_effect = lambda jobs: len(jobs)

    cfg = PipelineConfig(keywords=("kw",), platforms=("websearch", "xhs"))
    result, count = pipeline._search_stage(db, cfg)

    assert count == 2  # web still counted
    assert result.ok is False
    assert "cookies expired" in result.detail


def test_search_stage_unknown_platform_recorded():
    db = MagicMock()
    cfg = PipelineConfig(keywords=("kw",), platforms=("bogus",))
    result, count = pipeline._search_stage(db, cfg)
    assert count == 0
    assert result.ok is False
    assert "未知平台" in result.detail


# ----------------------------------------------------------------------
# score stage
# ----------------------------------------------------------------------


@patch("jobpilot.pipeline.config")
@patch("jobpilot.ai.scorer.score_jobs")
def test_score_stage_heuristic_and_refine(mock_score_jobs, mock_config):
    mock_config.ANTHROPIC_API_KEY = "key"
    new_job = MagicMock()
    heuristic_score = MagicMock(job_id="x")
    refined_score = MagicMock(job_id="x")
    # First call (heuristic) returns one score; second call (refine) returns one
    mock_score_jobs.side_effect = [[heuristic_score], [refined_score]]

    db = MagicMock()
    db.get_profile.return_value = MagicMock()
    db.list_jobs.return_value = [new_job]
    db.list_scores_with_jobs.return_value = [(refined_score, new_job)]

    cfg = PipelineConfig(keywords=("kw",), refine_top=20)
    result, scored, refined = pipeline._score_stage(db, cfg)

    assert result.ok is True
    assert scored == 1
    assert refined == 1
    # heuristic forced on first call, API on second
    assert mock_score_jobs.call_args_list[0].kwargs["force_heuristic"] is True
    assert mock_score_jobs.call_args_list[1].kwargs["force_heuristic"] is False


@patch("jobpilot.pipeline.config")
@patch("jobpilot.ai.scorer.score_jobs")
def test_score_stage_skips_refine_without_api_key(mock_score_jobs, mock_config):
    mock_config.ANTHROPIC_API_KEY = ""
    mock_score_jobs.return_value = [MagicMock(job_id="x")]
    db = MagicMock()
    db.get_profile.return_value = MagicMock()
    db.list_jobs.return_value = [MagicMock()]

    cfg = PipelineConfig(keywords=("kw",), refine_top=20)
    result, scored, refined = pipeline._score_stage(db, cfg)

    assert scored == 1
    assert refined == 0
    db.list_scores_with_jobs.assert_not_called()


def test_score_stage_no_profile():
    db = MagicMock()
    db.get_profile.return_value = None
    cfg = PipelineConfig(keywords=("kw",))
    result, scored, refined = pipeline._score_stage(db, cfg)
    assert result.ok is False
    assert scored == 0


# ----------------------------------------------------------------------
# tailor stage
# ----------------------------------------------------------------------


@patch("jobpilot.ai.tailor.save_tailored_resume")
def test_tailor_stage_success(mock_save):
    mock_save.return_value = "/tmp/out.docx"
    job = MagicMock(job_id="j1", company="字节")
    db = MagicMock()
    db.get_profile.return_value = MagicMock()
    db.list_top_untailored.return_value = [(MagicMock(), job)]

    cfg = PipelineConfig(keywords=("kw",), tailor_top=5)
    result, count = pipeline._tailor_stage(db, cfg)

    assert result.ok is True
    assert count == 1
    db.update_job_status.assert_called_with("j1", "tailored")


@patch("jobpilot.ai.tailor.save_tailored_resume")
def test_tailor_stage_isolates_failure(mock_save):
    mock_save.side_effect = RuntimeError("docx broken")
    job = MagicMock(job_id="j1", company="字节")
    db = MagicMock()
    db.get_profile.return_value = MagicMock()
    db.list_top_untailored.return_value = [(MagicMock(), job)]

    cfg = PipelineConfig(keywords=("kw",), tailor_top=5)
    result, count = pipeline._tailor_stage(db, cfg)

    assert result.ok is False
    assert count == 0
    assert "docx broken" in result.detail


def test_tailor_stage_skipped_when_zero():
    db = MagicMock()
    cfg = PipelineConfig(keywords=("kw",), tailor_top=0)
    result, count = pipeline._tailor_stage(db, cfg)
    assert result.ok is True
    assert count == 0
    db.list_top_untailored.assert_not_called()


# ----------------------------------------------------------------------
# greeting stage
# ----------------------------------------------------------------------


def test_greeting_stage_skipped_when_zero():
    db = MagicMock()
    cfg = PipelineConfig(keywords=("kw",), greeting_top=0)
    result, count = pipeline._greeting_stage(db, cfg)
    assert result.ok is True
    assert count == 0
    db.list_top_scored_jobs.assert_not_called()


@patch("jobpilot.ai.greeting._load_greeting_config")
def test_greeting_stage_skips_when_no_template(mock_cfg):
    mock_cfg.return_value = {}  # no base_template
    db = MagicMock()
    cfg = PipelineConfig(keywords=("kw",), greeting_top=5)
    result, count = pipeline._greeting_stage(db, cfg)
    assert result.ok is True
    assert count == 0
    assert "未配置" in result.detail
    db.list_top_scored_jobs.assert_not_called()


@patch("jobpilot.ai.greeting.generate_greeting")
@patch("jobpilot.ai.greeting._load_greeting_config")
def test_greeting_stage_writes_files(mock_cfg, mock_gen, tmp_path):
    from jobpilot.ai.greeting import GreetingResult

    mock_cfg.return_value = {"base_template": "intro {hook} end"}
    mock_gen.return_value = GreetingResult(channel="boss", body="您好，这是一条打招呼话术")
    job = MagicMock(job_id="j1", company="字节", title="AI产品")
    db = MagicMock()
    db.list_top_scored_jobs.return_value = [(MagicMock(), job)]

    cfg = PipelineConfig(keywords=("kw",), greeting_top=5)
    with patch.object(pipeline.config, "GREETINGS_DIR", tmp_path):
        result, count = pipeline._greeting_stage(db, cfg)

    assert result.ok is True
    assert count == 1
    written = list(tmp_path.glob("*.txt"))
    assert len(written) == 1
    assert "打招呼话术" in written[0].read_text(encoding="utf-8")


# ----------------------------------------------------------------------
# orchestrator
# ----------------------------------------------------------------------


def _stub_stage(name, ok=True):
    return StageResult(name, ok, "ok")


def test_run_pipeline_runs_all_stages_in_order():
    db = MagicMock()
    cfg = PipelineConfig(keywords=("kw",))
    calls = []

    with (
        patch.object(pipeline, "_search_stage", return_value=(_stub_stage("搜索"), 5)) as s,
        patch.object(pipeline, "_score_stage", return_value=(_stub_stage("打分"), 5, 2)),
        patch.object(pipeline, "_tailor_stage", return_value=(_stub_stage("定制简历"), 3)),
        patch.object(pipeline, "_greeting_stage", return_value=(_stub_stage("打招呼话术"), 4)),
        patch.object(pipeline, "_report_stage", return_value=(_stub_stage("日报"), "/tmp/r.md")),
    ):
        result = run_pipeline(db, cfg, progress=calls.append)

    assert [st.name for st in result.stages] == ["搜索", "打分", "定制简历", "打招呼话术", "日报"]
    assert result.found == 5
    assert result.scored == 5
    assert result.refined == 2
    assert result.tailored == 3
    assert result.greeted == 4
    assert result.report_path == "/tmp/r.md"
    assert len(calls) == 5  # one progress message per stage


def test_run_pipeline_isolates_stage_crash():
    """A crashing stage is recorded as failed but later stages still run."""
    db = MagicMock()
    cfg = PipelineConfig(keywords=("kw",))

    with (
        patch.object(pipeline, "_search_stage", side_effect=RuntimeError("boom")),
        patch.object(pipeline, "_score_stage", return_value=(_stub_stage("打分"), 4, 0)),
        patch.object(pipeline, "_tailor_stage", return_value=(_stub_stage("定制简历"), 1)),
        patch.object(pipeline, "_greeting_stage", return_value=(_stub_stage("打招呼话术"), 2)),
        patch.object(pipeline, "_report_stage", return_value=(_stub_stage("日报"), "/tmp/r.md")),
    ):
        result = run_pipeline(db, cfg)

    search_stage = result.stages[0]
    assert search_stage.name == "搜索"
    assert search_stage.ok is False
    assert "boom" in search_stage.detail
    # later stages still executed
    assert result.scored == 4
    assert result.tailored == 1
    assert result.report_path == "/tmp/r.md"
