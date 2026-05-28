"""Tests for the channel-aware, config-driven greeting generator."""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot.ai.greeting import (
    GreetingError,
    GreetingResult,
    build_email_prompt,
    build_hook_prompt,
    check_style_violations,
    compose_greeting,
    generate_greeting,
    interaction_tips,
)
from jobpilot.models import Job

PRODUCTS = [
    {"name": "JobPilot", "desc": "多渠道求职 Agent", "use_for": "招聘 / Agent", "hook_detail": "多 Agent 分工"},
    {"name": "MusiClaw", "desc": "演出数据平台", "use_for": "eval / 数据", "hook_detail": "自建 eval 框架"},
]

GCFG = {
    "base_template": "您好，我是陈亦奇，经济学方向。{hook}，希望能进一步沟通。",
    "products": PRODUCTS,
    "formality": "商务正式但自然",
    "channels": {
        "boss": {"tone": "短克制", "hook_max_chars": 80, "attachment_note": "这是我的简历照片~"},
        "xhs": {"tone": "稍自然", "hook_max_chars": 130},
        "email": {
            "subject_format": "【陈亦奇 + {job_title} + 实习】",
            "structure": "自我介绍→兴趣→经历→简历→沟通",
            "signature": "陈亦奇\n手机：123\n邮箱：a@b.com",
        },
    },
    "interaction_rules": ["二次锚定发 demo", "不催等 48-72h"],
}


def _job():
    return Job(job_id="x", title="AI产品实习生", company="字节", jd_text="负责 Agent 与 eval")


# ----------------------------------------------------------------------
# prompts
# ----------------------------------------------------------------------


def test_hook_prompt_includes_tone_maxchars_and_rules():
    p = build_hook_prompt("做 Agent 和 eval", PRODUCTS, {"tone": "短克制", "hook_max_chars": 80}, "正式但自然")
    assert "短克制" in p
    assert "80 字" in p
    assert "正式但自然" in p
    assert "MusiClaw" in p


def test_email_prompt_includes_structure_and_facts():
    p = build_email_prompt("jd", "AI产品实习生", "字节", PRODUCTS, "我是陈亦奇，经济学方向", "自我介绍→兴趣", "正式")
    assert "自我介绍→兴趣" in p
    assert "陈亦奇" in p
    assert "全角冒号" in p


# ----------------------------------------------------------------------
# compose / style / tips
# ----------------------------------------------------------------------


def test_compose_inserts_and_strips():
    out = compose_greeting("您好。{hook}，希望沟通。", '"我做过 JobPilot。"')
    assert out == "您好。我做过 JobPilot，希望沟通。"


def test_style_flags_casual_and_oldfashioned():
    v = check_style_violations("这套方法挺像的，届时联系")
    joined = " ".join(v)
    assert "这套" in joined
    assert "挺像的" in joined
    assert "届时" in joined


def test_interaction_tips_from_config():
    with patch("jobpilot.ai.greeting._load_greeting_config", return_value=GCFG):
        tips = interaction_tips()
    assert len(tips) == 2
    assert "二次锚定发 demo" in tips


# ----------------------------------------------------------------------
# generate_greeting — channels
# ----------------------------------------------------------------------


@patch("jobpilot.ai.greeting.config")
def test_unknown_channel_raises(mock_config):
    mock_config.ANTHROPIC_API_KEY = "key"
    with pytest.raises(GreetingError):
        generate_greeting(_job(), channel="wechat")


@patch("jobpilot.ai.greeting.config")
@patch("jobpilot.ai.greeting._load_greeting_config", return_value=GCFG)
def test_generate_raises_without_api_key(mock_cfg, mock_config):
    mock_config.ANTHROPIC_API_KEY = ""
    with pytest.raises(GreetingError):
        generate_greeting(_job(), channel="boss")


@patch("jobpilot.ai.greeting._call_llm", return_value="我用 MusiClaw 做了 eval 框架")
@patch("jobpilot.ai.greeting.config")
@patch("jobpilot.ai.greeting._load_greeting_config", return_value=GCFG)
def test_boss_channel_composes_intro_and_attachment(mock_cfg, mock_config, mock_llm):
    mock_config.ANTHROPIC_API_KEY = "key"
    r = generate_greeting(_job(), channel="boss")
    assert r.channel == "boss"
    assert "陈亦奇" in r.body  # fixed intro
    assert "MusiClaw" in r.body  # hook
    assert r.attachment_note == "这是我的简历照片~"
    assert r.subject == ""


@patch("jobpilot.ai.greeting._call_llm", return_value="正文内容")
@patch("jobpilot.ai.greeting.config")
@patch("jobpilot.ai.greeting._load_greeting_config", return_value=GCFG)
def test_email_channel_has_subject_and_signature(mock_cfg, mock_config, mock_llm):
    mock_config.ANTHROPIC_API_KEY = "key"
    r = generate_greeting(_job(), channel="email")
    assert r.channel == "email"
    assert r.subject == "【陈亦奇 + AI产品实习生 + 实习】"
    assert "正文内容" in r.body
    assert "手机：123" in r.body  # signature appended


def test_greeting_result_save_text():
    r = GreetingResult(channel="email", body="正文", subject="主题X")
    assert "主题：主题X" in r.save_text()
    assert "正文" in r.save_text()
    r2 = GreetingResult(channel="boss", body="打招呼", attachment_note="截图配文")
    assert "截图配文" in r2.save_text()
