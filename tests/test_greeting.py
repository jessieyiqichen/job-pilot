"""Tests for the personal-style greeting generator (fixed intro + LLM hook)."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot.ai.greeting import (
    GreetingError,
    build_hook_prompt,
    check_style_violations,
    compose_greeting,
    generate_greeting,
)
from jobpilot.models import Job

PRODUCTS = [
    {"name": "JobPilot", "desc": "多渠道求职 Agent", "use_for": "招聘 / Agent", "hook_detail": "多 Agent 分工"},
    {"name": "MusiClaw", "desc": "演出数据平台", "use_for": "eval / 数据", "hook_detail": "自建 eval 框架"},
]


# ----------------------------------------------------------------------
# build_hook_prompt
# ----------------------------------------------------------------------


def test_hook_prompt_includes_jd_products_and_rules():
    p = build_hook_prompt("负责 Agent 数字员工，做 eval", PRODUCTS)
    assert "Agent 数字员工" in p
    assert "JobPilot" in p and "MusiClaw" in p
    assert "长破折号" in p  # style rules embedded
    assert "vibe coding" in p  # echo keyword listed


# ----------------------------------------------------------------------
# compose_greeting
# ----------------------------------------------------------------------


def test_compose_inserts_hook_and_strips_punctuation():
    tpl = "您好，我是X。{hook}，希望能进一步沟通。"
    out = compose_greeting(tpl, "我用 JobPilot 做了多 Agent 协作。")
    assert out == "您好，我是X。我用 JobPilot 做了多 Agent 协作，希望能进一步沟通。"


def test_compose_strips_quotes():
    tpl = "intro{hook}end"
    out = compose_greeting(tpl, '"钩子"')
    assert out == "intro钩子end"


# ----------------------------------------------------------------------
# check_style_violations
# ----------------------------------------------------------------------


def test_style_flags_dash_parens_banned():
    v = check_style_violations("我做过 JobPilot——多渠道求职 Agent（很厉害），届时联系")
    joined = " ".join(v)
    assert "破折号" in joined
    assert "括号" in joined
    assert "届时" in joined


def test_style_flags_vibe_coding_as_self_label():
    # JD doesn't mention it -> violation
    assert any("vibe coding" in x for x in check_style_violations("我擅长 vibe coding", jd_text="AI产品"))
    # JD mentions it -> allowed (echo)
    assert not any("vibe coding" in x for x in check_style_violations("我擅长 vibe coding", jd_text="我们推崇 vibe coding"))


def test_style_clean_text_no_violations():
    assert check_style_violations("我用多渠道求职 Agent JobPilot 做了 AI 打分", jd_text="") == []


# ----------------------------------------------------------------------
# generate_greeting
# ----------------------------------------------------------------------


@patch("jobpilot.ai.greeting._load_greeting_config")
@patch("jobpilot.ai.greeting.config")
def test_generate_raises_without_template(mock_config, mock_cfg):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_cfg.return_value = {}  # no base_template
    with pytest.raises(GreetingError):
        generate_greeting(Job(job_id="x", jd_text="jd"))


@patch("jobpilot.ai.greeting._load_greeting_config")
@patch("jobpilot.ai.greeting.config")
def test_generate_raises_without_api_key(mock_config, mock_cfg):
    mock_config.ANTHROPIC_API_KEY = ""
    mock_cfg.return_value = {"base_template": "intro {hook} end", "products": PRODUCTS}
    with pytest.raises(GreetingError):
        generate_greeting(Job(job_id="x", jd_text="jd"))


@patch("jobpilot.ai.greeting._load_greeting_config")
@patch("jobpilot.ai.greeting.config")
def test_generate_composes_hook_into_template(mock_config, mock_cfg):
    mock_config.ANTHROPIC_API_KEY = "key"
    mock_config.ANTHROPIC_MODEL = "claude-x"
    mock_cfg.return_value = {
        "base_template": "您好，我是X。{hook}，希望沟通。",
        "products": PRODUCTS,
    }
    fake = MagicMock()
    fake.content = [MagicMock(text="我用 JobPilot 做了多 Agent 协作")]
    with patch("anthropic.Anthropic") as mc:
        mc.return_value.messages.create.return_value = fake
        out = generate_greeting(Job(job_id="x", jd_text="招 Agent"))
    assert out == "您好，我是X。我用 JobPilot 做了多 Agent 协作，希望沟通。"
