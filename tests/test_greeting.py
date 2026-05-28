"""Tests for the greeting (打招呼语) generator."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot.ai.greeting import (
    GreetingError,
    build_greeting_prompt,
    generate_greeting,
)
from jobpilot.models import Job, JobScore, Profile


def _job():
    return Job(job_id="x", title="AI产品实习生", company="字节", jd_text="负责大模型应用")


def _profile():
    return Profile(id=10, name="J", raw_text="做过 NLP 模型，10万+ 文本")


def test_prompt_includes_job_and_resume():
    p = build_greeting_prompt(_profile(), _job())
    assert "AI产品实习生" in p
    assert "字节" in p
    assert "NLP" in p


def test_prompt_includes_highlights_when_score_given():
    score = JobScore(job_id="x", highlights=["技能高度匹配"])
    p = build_greeting_prompt(_profile(), _job(), score)
    assert "技能高度匹配" in p


def test_prompt_omits_score_context_when_none():
    p = build_greeting_prompt(_profile(), _job(), None)
    assert "可强调的匹配亮点" not in p


@patch("jobpilot.ai.greeting.config")
def test_generate_raises_without_api_key(mock_config):
    mock_config.ANTHROPIC_API_KEY = ""
    with pytest.raises(GreetingError):
        generate_greeting(_profile(), _job())


@patch("jobpilot.ai.greeting.config")
def test_generate_returns_text_and_strips_quotes(mock_config):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_config.ANTHROPIC_MODEL = "claude-x"
    fake = MagicMock()
    fake.content = [MagicMock(text='"您好，我是做 NLP 的候选人，想聊聊这个岗位。"')]
    with patch("anthropic.Anthropic") as mc:
        mc.return_value.messages.create.return_value = fake
        out = generate_greeting(_profile(), _job())
    assert out.startswith("您好")
    assert '"' not in out[:2]  # surrounding quotes stripped
