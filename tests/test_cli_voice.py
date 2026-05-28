"""Integration tests for the `voice` CLI command."""

import pytest
from typer.testing import CliRunner

from jobpilot import config
from jobpilot.cli import app
from jobpilot.voice import VoiceSample, load_samples, save_samples

runner = CliRunner()

PID = config.DEFAULT_PROFILE_ID


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VOICE_DIR", tmp_path / "voice")


def test_voice_add_text():
    result = runner.invoke(app, ["voice", "你好，看到你们在招 AI 产品实习"])
    assert result.exit_code == 0
    assert "已加入" in result.output
    assert load_samples(PID)[0].text == "你好，看到你们在招 AI 产品实习"


def test_voice_list_empty():
    result = runner.invoke(app, ["voice", "--list"])
    assert result.exit_code == 0
    assert "还没有语言样本" in result.output


def test_voice_list_shows_samples():
    save_samples(PID, [VoiceSample.new("我自己的真实话术样本")])
    result = runner.invoke(app, ["voice", "--list"])
    assert result.exit_code == 0
    assert "我自己的真实话术样本" in result.output


def test_voice_revised_flag_marks_source():
    result = runner.invoke(app, ["voice", "改完回灌的话术", "--revised"])
    assert result.exit_code == 0
    assert load_samples(PID)[0].source == "revised"


def test_voice_dedup_skips_identical():
    runner.invoke(app, ["voice", "重复样本"])
    result = runner.invoke(app, ["voice", "重复样本"])
    assert "已存在" in result.output
    assert len(load_samples(PID)) == 1
