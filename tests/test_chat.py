"""Tests for the conversational chat advisor (jobpilot chat).

  - build_system_prompt(): pure, testable
  - run_chat(): REPL loop with injectable input/output + mocked reply
  - generate_reply(): LLM layer — degrade-without-key + one mocked success path
"""

from unittest.mock import MagicMock, patch

import pytest

from jobpilot import config
from jobpilot.ask import AskContext
from jobpilot.advisor import StrategyDiagnosis
from jobpilot.chat import (
    ChatError,
    build_system_prompt,
    generate_reply,
    run_chat,
)
from jobpilot.models import Job, JobScore, Profile


def _ctx():
    d = StrategyDiagnosis(high_score_total=37, total_applications=0, headline="先投起来")
    return AskContext(diagnosis=d, top_jobs=(("AI产品实习 @ 字节", 8.5),))


def _mock_db(*, high_pairs=None, applications=None):
    db = MagicMock()
    db.get_profile.return_value = Profile(
        id=10, structured={"preferences": {"career_track": "AI产品经理"}}
    )
    db.count_jobs_by_status.return_value = {"scored": 10}
    db.list_top_scored_jobs.return_value = high_pairs or [
        (JobScore(job_id="a", overall_score=8.5), Job(job_id="a", title="AI产品实习", company="字节")),
    ]
    db.list_applications.return_value = applications or []
    db.get_job.return_value = None
    db.get_score.return_value = None
    return db


# ----------------------------------------------------------------------
# build_system_prompt
# ----------------------------------------------------------------------


def test_system_prompt_includes_persona_data_and_prefs():
    profile = Profile(
        id=10, structured={"preferences": {"career_track": "AI产品经理", "preferred_cities": ["上海"]}}
    )
    sp = build_system_prompt(profile, _ctx())

    assert "军师" in sp                       # persona
    assert "37" in sp                          # diagnosis number
    assert "先投起来" in sp                    # headline
    assert "AI产品实习 @ 字节" in sp           # top job grounding
    assert "AI产品经理" in sp or "上海" in sp  # prefs


# ----------------------------------------------------------------------
# run_chat — REPL loop
# ----------------------------------------------------------------------


def test_run_chat_multi_turn_accumulates_history(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "key")
    db = _mock_db()
    inputs = iter(["怎么投？", "那字节呢？", "exit"])
    outputs: list[str] = []

    captured_histories = []

    def fake_reply(history, system):
        # snapshot the history length seen on each call
        captured_histories.append(len(history))
        return f"回复{len(captured_histories)}"

    with patch("jobpilot.chat.generate_reply", side_effect=fake_reply):
        run_chat(db, profile_id=10, input_fn=lambda _="": next(inputs), output_fn=outputs.append)

    # two user turns → two reply calls; history grows (1 then 3 messages)
    assert captured_histories == [1, 3]
    joined = "\n".join(outputs)
    assert "回复1" in joined and "回复2" in joined


def test_run_chat_exits_on_quit_word(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "key")
    db = _mock_db()
    inputs = iter(["q"])
    outputs: list[str] = []

    with patch("jobpilot.chat.generate_reply") as mock_reply:
        run_chat(db, profile_id=10, input_fn=lambda _="": next(inputs), output_fn=outputs.append)

    mock_reply.assert_not_called()  # quit immediately, no API call


def test_run_chat_skips_empty_input(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "key")
    db = _mock_db()
    inputs = iter(["", "  ", "真问题", "exit"])
    outputs: list[str] = []

    with patch("jobpilot.chat.generate_reply", return_value="答") as mock_reply:
        run_chat(db, profile_id=10, input_fn=lambda _="": next(inputs), output_fn=outputs.append)

    assert mock_reply.call_count == 1  # only the non-empty turn hit the API


def test_run_chat_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    db = _mock_db()
    with pytest.raises(ChatError):
        run_chat(db, profile_id=10, input_fn=lambda _="": "hi", output_fn=lambda _x: None)


def test_run_chat_handles_eof(monkeypatch):
    """Ctrl-D / piped EOF should end the loop gracefully, not crash."""
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "key")
    db = _mock_db()

    def raise_eof(_prompt=""):
        raise EOFError

    # should not raise
    run_chat(db, profile_id=10, input_fn=raise_eof, output_fn=lambda _x: None)


# ----------------------------------------------------------------------
# generate_reply — API contract
# ----------------------------------------------------------------------


def test_generate_reply_calls_api_with_system_and_history(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "key")
    history = [{"role": "user", "content": "你好"}]

    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="你好，我是你的军师")]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_msg

    with patch("anthropic.Anthropic", return_value=fake_client):
        reply = generate_reply(history, system="SYS")

    assert reply == "你好，我是你的军师"
    kwargs = fake_client.messages.create.call_args.kwargs
    assert kwargs["system"] == "SYS"
    assert kwargs["messages"] == history
