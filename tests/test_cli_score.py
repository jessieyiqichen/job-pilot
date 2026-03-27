"""Tests for score CLI command (--heuristic / --refine flags) and list --profile."""

from unittest.mock import MagicMock, call, patch

import pytest
from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.models import Job, JobScore, Profile

runner = CliRunner()


def _make_profile() -> Profile:
    return Profile(
        id=10,
        name="Jane Doe",
        raw_text="Jane Doe",
        structured={
            "name": "Jane Doe",
            "title": "Data Analyst",
            "years_of_experience": 1,
            "skills": {"programming": ["Python", "SQL"]},
            "education": [{"school": "U", "degree": "Master", "major": "Econ"}],
            "experience": [],
            "projects": [],
        },
        updated_at="2026-03-25",
    )


def _make_job(job_id: str = "j1") -> Job:
    return Job(
        platform="boss",
        job_id=job_id,
        title="数据分析师",
        company="TestCo",
        salary_min=10000,
        salary_max=20000,
        city="上海",
        experience="1-3年",
        education="本科",
        jd_text="技能要求：Python, SQL",
        raw_data={},
        discovered_at="2026-03-25",
    )


def _make_score(job_id: str = "j1") -> JobScore:
    return JobScore(
        job_id=job_id,
        profile_id=10,
        overall_score=7.5,
        skill_match=8.0,
        experience_match=7.0,
        salary_match=7.0,
        highlights=["匹配技能: Python, SQL"],
        concerns=[],
        suggestion="建议投递",
        scored_at="2026-03-25",
    )


class TestScoreHeuristicFlag:
    """Tests for --heuristic flag."""

    @patch("jobpilot.cli._get_db")
    @patch("jobpilot.ai.scorer.config")
    @patch("jobpilot.ai.scorer._load_preferences")
    def test_heuristic_flag_forces_heuristic(self, mock_prefs, mock_scorer_config, mock_get_db):
        """--heuristic flag should call score_jobs with force_heuristic=True."""
        mock_prefs.return_value = {}
        mock_scorer_config.ANTHROPIC_API_KEY = "sk-test"

        db = MagicMock()
        mock_get_db.return_value = db
        db.get_profile.return_value = _make_profile()
        db.list_jobs.return_value = [_make_job()]
        db.get_job.return_value = _make_job()

        with patch("jobpilot.ai.scorer.score_jobs", wraps=None) as mock_score_jobs:
            # Use the real heuristic scorer to avoid needing API
            from jobpilot.ai.scorer import score_jobs as real_score_jobs

            def fake_score_jobs(profile, jobs, *, force_heuristic=False):
                # Verify force_heuristic is passed
                assert force_heuristic is True
                return [_make_score()]

            mock_score_jobs.side_effect = fake_score_jobs

            result = runner.invoke(app, ["score", "--heuristic", "--profile", "10"])
            assert result.exit_code == 0
            mock_score_jobs.assert_called_once()

    @patch("jobpilot.cli._get_db")
    @patch("jobpilot.ai.scorer.config")
    @patch("jobpilot.ai.scorer._load_preferences")
    def test_no_heuristic_flag_default(self, mock_prefs, mock_scorer_config, mock_get_db):
        """Without --heuristic, force_heuristic should be False."""
        mock_prefs.return_value = {}
        mock_scorer_config.ANTHROPIC_API_KEY = ""  # No API key → heuristic anyway

        db = MagicMock()
        mock_get_db.return_value = db
        db.get_profile.return_value = _make_profile()
        db.list_jobs.return_value = [_make_job()]
        db.get_job.return_value = _make_job()

        with patch("jobpilot.ai.scorer.score_jobs") as mock_score_jobs:
            mock_score_jobs.return_value = [_make_score()]
            result = runner.invoke(app, ["score", "--profile", "10"])
            assert result.exit_code == 0
            # force_heuristic should be False (default)
            _, kwargs = mock_score_jobs.call_args
            assert kwargs.get("force_heuristic") is False


class TestScoreRefineFlag:
    """Tests for --refine flag."""

    @patch("jobpilot.cli._get_db")
    @patch("jobpilot.ai.scorer.config")
    @patch("jobpilot.ai.scorer._load_preferences")
    def test_refine_queries_existing_scores(self, mock_prefs, mock_scorer_config, mock_get_db):
        """--refine N should query list_scores_with_jobs and re-score."""
        mock_prefs.return_value = {}
        mock_scorer_config.ANTHROPIC_API_KEY = ""

        db = MagicMock()
        mock_get_db.return_value = db
        db.get_profile.return_value = _make_profile()

        job = _make_job()
        score_obj = _make_score()
        db.list_scores_with_jobs.return_value = [(score_obj, job)]
        db.get_job.return_value = job

        with patch("jobpilot.ai.scorer.score_jobs") as mock_score_jobs:
            mock_score_jobs.return_value = [_make_score()]
            result = runner.invoke(app, ["score", "--refine", "5", "--profile", "10"])
            assert result.exit_code == 0

            # Should query existing scores, not new jobs
            db.list_scores_with_jobs.assert_called_once_with(profile_id=10, limit=5)
            db.list_jobs.assert_not_called()

            # force_heuristic should be False for refine
            _, kwargs = mock_score_jobs.call_args
            assert kwargs.get("force_heuristic") is False

    @patch("jobpilot.cli._get_db")
    @patch("jobpilot.ai.scorer.config")
    @patch("jobpilot.ai.scorer._load_preferences")
    def test_refine_upserts_scores(self, mock_prefs, mock_scorer_config, mock_get_db):
        """--refine should upsert new scores (overwrite old heuristic scores)."""
        mock_prefs.return_value = {}
        mock_scorer_config.ANTHROPIC_API_KEY = ""

        db = MagicMock()
        mock_get_db.return_value = db
        db.get_profile.return_value = _make_profile()

        job = _make_job()
        score_obj = _make_score()
        db.list_scores_with_jobs.return_value = [(score_obj, job)]
        db.get_job.return_value = job

        new_score = _make_score()
        with patch("jobpilot.ai.scorer.score_jobs") as mock_score_jobs:
            mock_score_jobs.return_value = [new_score]
            result = runner.invoke(app, ["score", "--refine", "5", "--profile", "10"])
            assert result.exit_code == 0

            # upsert_score should be called but NOT update_job_status
            db.upsert_score.assert_called_once_with(new_score)
            db.update_job_status.assert_not_called()

    @patch("jobpilot.cli._get_db")
    def test_refine_no_scored_jobs(self, mock_get_db):
        """--refine with no scored jobs should show warning."""
        db = MagicMock()
        mock_get_db.return_value = db
        db.get_profile.return_value = _make_profile()
        db.list_scores_with_jobs.return_value = []

        result = runner.invoke(app, ["score", "--refine", "5", "--profile", "10"])
        assert result.exit_code == 0
        assert "没有已评分岗位" in result.output


class TestListProfileFlag:
    """Tests for list --profile flag (bug fix: profile_id passthrough)."""

    @patch("jobpilot.cli._get_db")
    def test_list_min_score_passes_profile_id(self, mock_get_db):
        """list --min-score --profile should pass profile_id to list_scores_with_jobs."""
        db = MagicMock()
        mock_get_db.return_value = db

        job = _make_job()
        score_obj = _make_score()
        db.list_scores_with_jobs.return_value = [(score_obj, job)]

        result = runner.invoke(app, ["list", "--min-score", "7", "--profile", "10"])
        assert result.exit_code == 0
        db.list_scores_with_jobs.assert_called_once_with(
            profile_id=10, min_score=7.0, limit=20
        )

    @patch("jobpilot.cli._get_db")
    def test_list_min_score_default_profile(self, mock_get_db):
        """list --min-score without --profile should default to profile_id=10."""
        db = MagicMock()
        mock_get_db.return_value = db
        db.list_scores_with_jobs.return_value = []

        result = runner.invoke(app, ["list", "--min-score", "5"])
        assert result.exit_code == 0
        db.list_scores_with_jobs.assert_called_once_with(
            profile_id=10, min_score=5.0, limit=20
        )
