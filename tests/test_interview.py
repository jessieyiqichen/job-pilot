"""Tests for the interview-prep generator (ai/interview.py)."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot.ai import interview
from jobpilot.ai.interview import (
    InterviewPrep,
    InterviewPrepError,
    InterviewQuestion,
    build_interview_prompt,
    format_markdown,
    generate_interview_prep,
    parse_interview_response,
)
from jobpilot.models import Job, JobScore, Profile


def _job() -> Job:
    return Job(job_id="x", title="AI产品经理实习生", company="字节跳动", jd_text="负责大模型应用")


def _profile() -> Profile:
    return Profile(id=10, name="Jessie", raw_text="主导过数据分析项目，做过 NLP 模型")


# ----------------------------------------------------------------------
# build_interview_prompt
# ----------------------------------------------------------------------


def test_prompt_includes_job_and_resume():
    p = build_interview_prompt(_profile(), _job())
    assert "AI产品经理实习生" in p
    assert "字节跳动" in p
    assert "数据分析项目" in p


def test_prompt_includes_score_context_when_given():
    score = JobScore(job_id="x", highlights=["技能匹配高"], concerns=["缺乏产品经验"])
    p = build_interview_prompt(_profile(), _job(), score)
    assert "技能匹配高" in p
    assert "缺乏产品经验" in p


def test_prompt_omits_score_context_when_none():
    p = build_interview_prompt(_profile(), _job(), None)
    assert "AI 匹配分析" not in p


# ----------------------------------------------------------------------
# parse_interview_response
# ----------------------------------------------------------------------


def test_parse_valid_json():
    raw = """{
      "questions": [
        {"category": "行为面", "question": "讲一个你主导的项目", "talking_point": "用数据分析项目"}
      ],
      "prep_notes": "突出技术背景"
    }"""
    prep = parse_interview_response(raw, _job())
    assert isinstance(prep, InterviewPrep)
    assert prep.job_title == "AI产品经理实习生"
    assert len(prep.questions) == 1
    assert prep.questions[0].category == "行为面"
    assert prep.prep_notes == "突出技术背景"


def test_parse_tolerates_code_fence():
    raw = "```json\n{\"questions\": [], \"prep_notes\": \"x\"}\n```"
    prep = parse_interview_response(raw, _job())
    assert prep.prep_notes == "x"
    assert prep.questions == ()


def test_parse_skips_malformed_questions():
    raw = """{"questions": [
        {"category": "行为面", "question": "", "talking_point": "空问题跳过"},
        "not a dict",
        {"category": "产品sense", "question": "如何定义指标", "talking_point": "ok"}
    ], "prep_notes": ""}"""
    prep = parse_interview_response(raw, _job())
    assert len(prep.questions) == 1
    assert prep.questions[0].question == "如何定义指标"


def test_parse_garbage_returns_empty():
    prep = parse_interview_response("not json at all", _job())
    assert prep.questions == ()
    assert prep.prep_notes == ""


# ----------------------------------------------------------------------
# generate_interview_prep
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# format_markdown
# ----------------------------------------------------------------------


def test_format_markdown_groups_by_category():
    prep = InterviewPrep(
        job_title="AI产品实习",
        company="字节",
        questions=(
            InterviewQuestion("行为面", "Q1", "T1"),
            InterviewQuestion("行为面", "Q2", "T2"),
            InterviewQuestion("产品sense", "Q3", "T3"),
        ),
        prep_notes="加油",
    )
    md = format_markdown(prep)
    assert "# 面试准备 — AI产品实习 @ 字节" in md
    assert md.count("## 行为面") == 1  # grouped, not repeated per question
    assert "## 产品sense" in md
    assert "Q1" in md and "T3" in md
    assert "加油" in md


# ----------------------------------------------------------------------
# generate_interview_prep
# ----------------------------------------------------------------------


@patch("jobpilot.ai.interview.config")
def test_generate_raises_without_api_key(mock_config):
    mock_config.ANTHROPIC_API_KEY = ""
    with pytest.raises(InterviewPrepError):
        generate_interview_prep(_profile(), _job())


@patch("jobpilot.ai.interview.config")
def test_generate_parses_api_response(mock_config):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_config.ANTHROPIC_MODEL = "claude-x"
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text='{"questions": [{"category":"行为面","question":"Q1","talking_point":"T1"}], "prep_notes":"N"}')]

    with patch("anthropic.Anthropic") as mock_client:
        mock_client.return_value.messages.create.return_value = fake_msg
        prep = generate_interview_prep(_profile(), _job())

    assert len(prep.questions) == 1
    assert prep.questions[0].question == "Q1"
    assert prep.prep_notes == "N"
