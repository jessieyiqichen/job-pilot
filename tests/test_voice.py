"""Tests for the voice (language-style) sample store + few-shot block."""

import pytest

from jobpilot import config
from jobpilot.voice import (
    VoiceSample,
    add_sample,
    build_voice_block,
    load_samples,
    save_samples,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VOICE_DIR", tmp_path / "voice")


def test_sample_new_and_roundtrip():
    s = VoiceSample.new("你好呀，我看到你们在招AI产品实习", source="manual", context="greeting")
    assert s.text.startswith("你好呀")
    assert s.source == "manual"
    assert s.created_at
    assert VoiceSample.from_dict(s.to_dict()) == s


def test_load_missing_returns_empty():
    assert load_samples(10) == []


def test_save_then_load_roundtrip():
    samples = [VoiceSample.new("样本一"), VoiceSample.new("样本二")]
    save_samples(10, samples)
    assert [s.text for s in load_samples(10)] == ["样本一", "样本二"]


def test_add_sample_appends():
    save_samples(10, [VoiceSample.new("旧的")])
    add_sample(10, VoiceSample.new("新的", source="revised"))
    texts = [s.text for s in load_samples(10)]
    assert texts == ["旧的", "新的"]


def test_add_sample_dedups_identical_text():
    save_samples(10, [VoiceSample.new("一样的")])
    add_sample(10, VoiceSample.new("一样的"))
    assert len(load_samples(10)) == 1


def test_build_voice_block_includes_samples_and_instruction():
    samples = [VoiceSample.new("我自己写的真实话术，口语一点")]
    block = build_voice_block(samples)
    assert "我自己写的真实话术" in block
    assert "模仿" in block  # instruction to mimic the voice


def test_build_voice_block_empty_returns_empty():
    assert build_voice_block([]) == ""


def test_build_voice_block_caps_to_recent():
    samples = [VoiceSample.new(f"样本{i}") for i in range(10)]
    block = build_voice_block(samples, max_n=3)
    # only the most recent 3 are included
    assert "样本9" in block
    assert "样本7" in block
    assert "样本6" not in block
