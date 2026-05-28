"""Tests for the cognitive-profile loader (reads the sibling Nous model)."""

import json

from jobpilot.cognitive import (
    CognitiveProfile,
    format_cognitive_prompt,
    load_cognitive_profile,
)


def _write_model(tmp_path):
    p = tmp_path / "model.json"
    p.write_text(
        json.dumps(
            {
                "summary": "bimodal cognitive architecture, caring-driven attention",
                "dimensions": [
                    {
                        "name": "Decision Architecture",
                        "description": "intuition-first, acts only when framework converges",
                        "behavioral_predictions": ["will miss deadlines rather than start unclear"],
                        "confidence": "high",
                    },
                    {
                        "name": "Blind Spots",
                        "description": "underweights good-enough; unsustainable standards when engaged",
                        "behavioral_predictions": [],
                        "confidence": "high",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def test_load_missing_returns_none():
    assert load_cognitive_profile("/no/such/file.json") is None


def test_load_parses_model(tmp_path):
    prof = load_cognitive_profile(str(_write_model(tmp_path)))
    assert isinstance(prof, CognitiveProfile)
    assert "bimodal" in prof.summary
    assert prof.dimensions[0].name == "Decision Architecture"
    assert len(prof.dimensions) == 2


def test_load_corrupt_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert load_cognitive_profile(str(p)) is None


def test_load_empty_model_returns_none(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"summary": "", "dimensions": []}), encoding="utf-8")
    assert load_cognitive_profile(str(p)) is None


def test_format_includes_summary_dims_and_usage_guard(tmp_path):
    prof = load_cognitive_profile(str(_write_model(tmp_path)))
    out = format_cognitive_prompt(prof)
    assert "bimodal" in out                  # summary
    assert "Decision Architecture" in out    # dimension
    assert "贴标签" in out                    # usage guard against labeling the user


def test_format_none_returns_empty():
    assert format_cognitive_prompt(None) == ""


def test_cognitive_block_injected_into_all_advisor_prompts():
    """The cognitive block must thread through advisor / ask / chat prompts."""
    from jobpilot.advisor import StrategyDiagnosis, build_advisor_prompt
    from jobpilot.ask import AskContext, build_ask_prompt
    from jobpilot.chat import build_system_prompt
    from jobpilot.models import Profile

    marker = "COGNITIVE_BLOCK_MARKER_纳斯"
    d = StrategyDiagnosis(headline="先投起来")
    ctx = AskContext(diagnosis=d)
    profile = Profile(id=10)

    assert marker in build_advisor_prompt(d, profile, marker)
    assert marker in build_ask_prompt("怎么投？", profile, ctx, marker)
    assert marker in build_system_prompt(profile, ctx, marker)

    # absent by default → graceful degradation
    assert marker not in build_advisor_prompt(d, profile)
