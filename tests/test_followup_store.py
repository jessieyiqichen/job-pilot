"""Tests for commitment (follow-up) persistence."""

import json

import pytest

from jobpilot import config
from jobpilot.followup import Commitment
from jobpilot.followup_store import (
    add_commitments,
    commit_file,
    list_commitments,
    load_commitments,
    save_commitments,
    update_status,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHATS_DIR", tmp_path / "chats")


def _c(text, **kw):
    return Commitment.new(text, **kw)


def test_load_missing_returns_empty():
    assert load_commitments(10) == []


def test_save_then_load_roundtrip():
    items = [_c("投字节", job_id="j1"), _c("改简历")]
    save_commitments(10, items)
    loaded = load_commitments(10)
    assert [c.text for c in loaded] == ["投字节", "改简历"]
    assert loaded[0].job_id == "j1"


def test_add_dedups_by_text():
    save_commitments(10, [_c("投字节")])
    added = add_commitments(10, [_c("投字节"), _c("投腾讯")])
    # only the genuinely-new one is added
    assert [c.text for c in added] == ["投腾讯"]
    assert {c.text for c in load_commitments(10)} == {"投字节", "投腾讯"}


def test_update_status_marks_done():
    items = [_c("投字节")]
    save_commitments(10, items)
    cid = items[0].id
    update_status(10, cid, "done")
    loaded = load_commitments(10)
    assert loaded[0].status == "done"


def test_list_commitments_filters_open():
    a = _c("open one")
    b = _c("done one")
    save_commitments(10, [a, b])
    update_status(10, b.id, "done")
    open_only = list_commitments(10, status="open")
    assert [c.text for c in open_only] == ["open one"]


def test_load_corrupt_returns_empty():
    p = commit_file(10)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{bad json", encoding="utf-8")
    assert load_commitments(10) == []


def test_load_skips_malformed_entries():
    p = commit_file(10)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([{"id": "x", "text": "ok", "status": "open"}, {"no_text": 1}, "nope"]),
        encoding="utf-8",
    )
    out = load_commitments(10)
    assert [c.text for c in out] == ["ok"]
