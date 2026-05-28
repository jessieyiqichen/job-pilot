"""Tests for the conversational advisor (jobpilot ask).

Layers mirror advisor.py:
  - gather_context() / build_ask_prompt(): pure, testable, no network
  - answer_question(): LLM layer — only the degrade-without-key contract
"""

from unittest.mock import MagicMock

import pytest

from jobpilot import config
from jobpilot.ask import (
    AskContext,
    AskError,
    answer_question,
    build_ask_prompt,
    gather_context,
)
from jobpilot.advisor import StrategyDiagnosis
from jobpilot.models import Application, Job, JobScore, Profile


def _pair(job_id: str, score: float, status: str = "scored"):
    return (
        JobScore(job_id=job_id, overall_score=score),
        Job(job_id=job_id, title=f"岗位{job_id}", company=f"公司{job_id}", status=status),
    )


def _mock_db(*, high_pairs=None, applications=None, job=None, score=None):
    db = MagicMock()
    db.count_jobs_by_status.return_value = {"scored": 10}
    db.list_top_scored_jobs.return_value = high_pairs or []
    db.list_applications.return_value = applications or []
    db.get_job.return_value = job
    db.get_score.return_value = score
    return db


# ----------------------------------------------------------------------
# gather_context
# ----------------------------------------------------------------------


def test_gather_context_collects_diagnosis_and_top_jobs():
    db = _mock_db(high_pairs=[_pair("a", 8.5), _pair("b", 7.5)])
    ctx = gather_context(db, profile_id=10)

    assert isinstance(ctx.diagnosis, StrategyDiagnosis)
    assert ctx.diagnosis.high_score_total == 2
    assert len(ctx.top_jobs) == 2
    assert ctx.job is None
    assert ctx.score is None


def test_gather_context_injects_specific_job():
    job = Job(job_id="x", title="AI产品实习", company="字节", jd_text="负责大模型产品")
    score = JobScore(job_id="x", overall_score=8.0)
    db = _mock_db(high_pairs=[_pair("a", 8.0)], job=job, score=score)

    ctx = gather_context(db, profile_id=10, job_id="x")

    assert ctx.job is not None
    assert ctx.job.title == "AI产品实习"
    assert ctx.score is not None
    db.get_job.assert_called_once_with("x")


# ----------------------------------------------------------------------
# build_ask_prompt
# ----------------------------------------------------------------------


def _ctx(job=None, score=None):
    d = StrategyDiagnosis(high_score_total=37, total_applications=0, headline="先投起来")
    return AskContext(
        diagnosis=d,
        top_jobs=(("AI产品实习 @ 字节", 8.5),),
        job=job,
        score=score,
    )


def test_build_prompt_includes_question_prefs_and_context():
    profile = Profile(
        id=10,
        structured={"preferences": {"career_track": "AI产品经理", "cities": ["上海"]}},
    )
    prompt = build_ask_prompt("这个 offer 该不该接？", profile, _ctx())

    assert "这个 offer 该不该接？" in prompt   # the question
    assert "37" in prompt                       # diagnosis number
    assert "先投起来" in prompt                 # headline
    assert "AI产品经理" in prompt or "上海" in prompt  # prefs
    assert "AI产品实习 @ 字节" in prompt        # top job context


def test_build_prompt_includes_job_jd_when_present():
    job = Job(job_id="x", title="AI产品实习", company="字节", jd_text="负责大模型产品落地")
    prompt = build_ask_prompt("我该准备什么？", Profile(id=10), _ctx(job=job))
    assert "负责大模型产品落地" in prompt
    assert "字节" in prompt


# ----------------------------------------------------------------------
# answer_question — degrade-without-key contract
# ----------------------------------------------------------------------


def test_answer_question_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    db = _mock_db()
    with pytest.raises(AskError):
        answer_question("随便问问", Profile(id=10), db)
