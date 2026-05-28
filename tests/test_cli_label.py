"""Tests for label file helpers and the interactive `label` CLI command."""

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.eval import read_labels_file, write_labels_file
from jobpilot.models import Job, JobScore

runner = CliRunner()


# ----------------------------------------------------------------------
# file helpers
# ----------------------------------------------------------------------


def test_write_then_read_roundtrip(tmp_path):
    p = tmp_path / "labels.json"
    write_labels_file({"b": 1, "a": 0}, str(p))
    # sorted keys on disk
    assert list(json.loads(p.read_text()).keys()) == ["a", "b"]
    assert read_labels_file(str(p)) == {"a": 0, "b": 1}


def test_read_missing_file_empty(tmp_path):
    assert read_labels_file(str(tmp_path / "nope.json")) == {}


def test_read_coerces_truthy(tmp_path):
    p = tmp_path / "labels.json"
    p.write_text(json.dumps({"a": True, "b": 0, "c": 5}), encoding="utf-8")
    assert read_labels_file(str(p)) == {"a": 1, "b": 0, "c": 1}


# ----------------------------------------------------------------------
# interactive label command
# ----------------------------------------------------------------------


def _pair(job_id, score=8.0):
    return (
        JobScore(job_id=job_id, overall_score=score, suggestion="建议投递"),
        Job(job_id=job_id, title=f"岗位{job_id}", company="公司", city="上海"),
    )


@patch("jobpilot.cli._get_db")
def test_label_writes_choices(mock_get_db, tmp_path):
    db = MagicMock()
    db.list_scores_with_jobs.return_value = [_pair("a"), _pair("b"), _pair("c")]
    mock_get_db.return_value = db
    out = tmp_path / "labels.json"

    # a=y(1), b=n(0), c=s(skip)
    result = runner.invoke(
        app, ["label", "--labels", str(out)], input="y\nn\ns\n"
    )

    assert result.exit_code == 0
    saved = json.loads(out.read_text())
    assert saved == {"a": 1, "b": 0}  # c skipped


@patch("jobpilot.cli._get_db")
def test_label_quit_saves_progress(mock_get_db, tmp_path):
    db = MagicMock()
    db.list_scores_with_jobs.return_value = [_pair("a"), _pair("b")]
    mock_get_db.return_value = db
    out = tmp_path / "labels.json"

    # a=y then quit before b
    result = runner.invoke(app, ["label", "--labels", str(out)], input="y\nq\n")

    assert result.exit_code == 0
    assert json.loads(out.read_text()) == {"a": 1}


@patch("jobpilot.cli._get_db")
def test_label_skips_already_labeled(mock_get_db, tmp_path):
    db = MagicMock()
    db.list_scores_with_jobs.return_value = [_pair("a"), _pair("b")]
    mock_get_db.return_value = db
    out = tmp_path / "labels.json"
    write_labels_file({"a": 1}, str(out))  # 'a' already labeled

    # only 'b' should be presented; label it n
    result = runner.invoke(app, ["label", "--labels", str(out)], input="n\n")

    assert result.exit_code == 0
    assert json.loads(out.read_text()) == {"a": 1, "b": 0}
