"""Tests for scoring-agreement evaluation (eval.py)."""

import json
from unittest.mock import MagicMock

from jobpilot.eval import EvalResult, evaluate, load_labels
from jobpilot.models import Application, JobScore


# ----------------------------------------------------------------------
# EvalResult metrics
# ----------------------------------------------------------------------


def test_eval_result_metrics():
    r = EvalResult(threshold=7.0, n=10, tp=4, fp=1, fn=2, tn=3)
    assert r.precision == 4 / 5
    assert r.recall == 4 / 6
    assert round(r.f1, 3) == round(2 * (4 / 5) * (4 / 6) / ((4 / 5) + (4 / 6)), 3)
    assert r.accuracy == 7 / 10


def test_eval_result_zero_division_safe():
    r = EvalResult(threshold=7.0, n=0, tp=0, fp=0, fn=0, tn=0)
    assert r.precision == 0.0
    assert r.recall == 0.0
    assert r.f1 == 0.0
    assert r.accuracy == 0.0


# ----------------------------------------------------------------------
# load_labels
# ----------------------------------------------------------------------


def test_load_labels_from_applications():
    db = MagicMock()
    db.list_applications.return_value = [
        Application(job_id="a", status="applied"),
        Application(job_id="b", status="offer"),
        Application(job_id="c", status="rejected"),
        Application(job_id="d", status="scored"),  # neutral, ignored
    ]
    labels = load_labels(db, labels_path=None)
    assert labels == {"a": 1, "b": 1, "c": 0}


def test_load_labels_file_overrides_applications(tmp_path):
    db = MagicMock()
    db.list_applications.return_value = [Application(job_id="a", status="applied")]
    lf = tmp_path / "labels.json"
    lf.write_text(json.dumps({"a": 0, "z": 1}), encoding="utf-8")

    labels = load_labels(db, labels_path=str(lf))
    assert labels["a"] == 0  # file overrides applied->1
    assert labels["z"] == 1


def test_load_labels_missing_file_is_ignored(tmp_path):
    db = MagicMock()
    db.list_applications.return_value = []
    labels = load_labels(db, labels_path=str(tmp_path / "nope.json"))
    assert labels == {}


# ----------------------------------------------------------------------
# evaluate
# ----------------------------------------------------------------------


def _db_with_scores(scores: dict[str, float]):
    db = MagicMock()

    def _get_score(job_id, profile_id=10):
        if job_id in scores:
            return JobScore(job_id=job_id, overall_score=scores[job_id])
        return None

    db.get_score.side_effect = _get_score
    return db


def test_evaluate_confusion_matrix():
    # labels: a,b want(1); c,d dont(0)
    labels = {"a": 1, "b": 1, "c": 0, "d": 0}
    # scores: a=8(>=7 TP), b=5(<7 FN), c=9(>=7 FP), d=4(<7 TN)
    db = _db_with_scores({"a": 8.0, "b": 5.0, "c": 9.0, "d": 4.0})

    r = evaluate(db, labels, threshold=7.0, profile_id=10)

    assert (r.tp, r.fn, r.fp, r.tn) == (1, 1, 1, 1)
    assert r.n == 4
    assert r.precision == 0.5
    assert r.recall == 0.5


def test_evaluate_skips_unscored_jobs():
    labels = {"a": 1, "missing": 1}
    db = _db_with_scores({"a": 8.0})  # 'missing' has no score
    r = evaluate(db, labels, threshold=7.0)
    assert r.n == 1
    assert r.tp == 1
