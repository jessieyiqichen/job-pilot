"""Tests for chat history persistence (chat_store)."""

import json

import pytest

from jobpilot import config
from jobpilot.chat_store import (
    chat_file,
    clear_history,
    load_history,
    save_history,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHATS_DIR", tmp_path / "chats")


def test_load_missing_returns_empty():
    assert load_history(10) == []


def test_save_then_load_roundtrip():
    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，我是军师"},
    ]
    save_history(10, history)
    assert load_history(10) == history


def test_per_profile_files_isolated():
    save_history(10, [{"role": "user", "content": "A"}])
    save_history(20, [{"role": "user", "content": "B"}])
    assert load_history(10)[0]["content"] == "A"
    assert load_history(20)[0]["content"] == "B"


def test_clear_removes_history():
    save_history(10, [{"role": "user", "content": "x"}])
    clear_history(10)
    assert load_history(10) == []


def test_clear_missing_is_noop():
    clear_history(999)  # should not raise


def test_load_ignores_malformed_entries():
    p = chat_file(10)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            [
                {"role": "user", "content": "ok"},
                {"role": "bogus", "content": "drop me"},
                {"role": "assistant"},          # missing content
                "not a dict",
            ]
        ),
        encoding="utf-8",
    )
    out = load_history(10)
    assert out == [{"role": "user", "content": "ok"}]


def test_load_corrupt_json_returns_empty():
    p = chat_file(10)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not json", encoding="utf-8")
    assert load_history(10) == []
