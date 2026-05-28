"""Tests for the follow-up engine: Commitment model, extraction, reconciliation."""

from unittest.mock import MagicMock

from jobpilot.followup import (
    Commitment,
    build_extract_prompt,
    parse_commitments_response,
    reconcile_with_applications,
)
from jobpilot.models import Application, Job


# ----------------------------------------------------------------------
# Commitment model
# ----------------------------------------------------------------------


def test_commitment_new_sets_defaults():
    c = Commitment.new("投字节", job_id="j1", due_hint="本周")
    assert c.text == "投字节"
    assert c.job_id == "j1"
    assert c.due_hint == "本周"
    assert c.status == "open"
    assert c.id  # non-empty id
    assert c.created_at


def test_commitment_roundtrip_dict():
    c = Commitment.new("改简历")
    c2 = Commitment.from_dict(c.to_dict())
    assert c2 == c


# ----------------------------------------------------------------------
# parse_commitments_response — tolerant JSON extraction
# ----------------------------------------------------------------------


def test_parse_extracts_commitments():
    text = '{"commitments": [{"text": "本周投字节", "job_hint": "字节", "due_hint": "本周"}]}'
    out = parse_commitments_response(text)
    assert len(out) == 1
    assert out[0].text == "本周投字节"
    assert out[0].due_hint == "本周"


def test_parse_handles_code_fence():
    text = '```json\n{"commitments": [{"text": "改简历"}]}\n```'
    out = parse_commitments_response(text)
    assert out[0].text == "改简历"


def test_parse_empty_or_garbage_returns_empty():
    assert parse_commitments_response("没有明确承诺") == []
    assert parse_commitments_response("") == []


def test_parse_skips_entries_without_text():
    text = '{"commitments": [{"text": ""}, {"due_hint": "本周"}, {"text": "投腾讯"}]}'
    out = parse_commitments_response(text)
    assert [c.text for c in out] == ["投腾讯"]


# ----------------------------------------------------------------------
# build_extract_prompt
# ----------------------------------------------------------------------


def test_extract_prompt_includes_conversation():
    history = [
        {"role": "user", "content": "我想这周投字节"},
        {"role": "assistant", "content": "好，记住了"},
    ]
    prompt = build_extract_prompt(history)
    assert "我想这周投字节" in prompt
    assert "JSON" in prompt or "json" in prompt


# ----------------------------------------------------------------------
# reconcile_with_applications — data-driven auto-close
# ----------------------------------------------------------------------


def test_reconcile_marks_done_when_job_applied():
    commitments = [
        Commitment.new("投字节", job_id="j1"),
        Commitment.new("投腾讯", job_id="j2"),
    ]
    db = MagicMock()
    # j1 已投递, j2 还没
    db.get_application.side_effect = lambda jid: (
        Application(job_id="j1", status="applied") if jid == "j1" else None
    )

    updated, closed_ids = reconcile_with_applications(commitments, db)

    by_text = {c.text: c for c in updated}
    assert by_text["投字节"].status == "done"   # auto-closed: already applied
    assert by_text["投腾讯"].status == "open"    # still pending
    assert closed_ids == [commitments[0].id]


def test_reconcile_ignores_commitments_without_job():
    commitments = [Commitment.new("随便改改简历")]  # no job_id
    db = MagicMock()
    updated, closed_ids = reconcile_with_applications(commitments, db)
    assert updated[0].status == "open"
    assert closed_ids == []
    db.get_application.assert_not_called()


def test_reconcile_skips_already_done():
    c = Commitment.new("投字节", job_id="j1")
    done = c.with_status("done")
    db = MagicMock()
    updated, closed_ids = reconcile_with_applications([done], db)
    assert closed_ids == []
    db.get_application.assert_not_called()
