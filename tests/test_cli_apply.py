"""Tests for the apply and pipeline CLI commands (Feature 2)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.db import JobPilotDB
from jobpilot.models import Job, JobScore, Profile

runner = CliRunner()


def _setup_db(tmp_path: Path, n_jobs: int = 3) -> JobPilotDB:
    """Create a test DB with a profile and scored jobs."""
    db = JobPilotDB(db_path=tmp_path / "test.db")
    profile = Profile(
        name="Test User",
        raw_text="Test resume",
        structured={
            "name": "Test User",
            "title": "Data Analyst",
            "skills": {"programming": ["Python", "SQL"]},
            "education": [{"school": "MIT", "degree": "Master", "major": "CS"}],
            "experience": [],
            "projects": [],
            "years_of_experience": 1,
        },
        updated_at="2026-03-25",
    )
    db.upsert_profile(profile)

    for i in range(1, n_jobs + 1):
        job = Job(
            platform="boss",
            job_id=f"job_{i:03d}",
            title=f"数据分析师{i}",
            company=f"公司{i}",
            salary_min=10000 * i,
            salary_max=20000 * i,
            city="上海",
            experience="1-3年",
            education="本科",
            jd_text="技能要求：Python, SQL",
            raw_data={},
            discovered_at="2026-03-25",
            status="scored",
        )
        db.upsert_job(job)
        score = JobScore(
            job_id=f"job_{i:03d}",
            profile_id=1,
            overall_score=9.0 - i * 0.5,
            skill_match=8.0,
            experience_match=7.0,
            salary_match=7.0,
            highlights=["good match"],
            concerns=[],
            suggestion="建议投递",
            scored_at="2026-03-25",
        )
        db.upsert_score(score)

    return db


class TestApplyCommand:
    def test_apply_shows_table(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["apply", "-p", "1", "-m", "7.0"], input="q\n")
        assert result.exit_code == 0
        assert "可投递岗位" in result.output
        assert "公司1" in result.output

    def test_apply_mark_selected(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["apply", "-p", "1", "-m", "7.0"], input="1\n")
        assert result.exit_code == 0
        assert "已标记" in result.output
        # Verify the job status was updated
        updated_job = db.get_job("job_001")
        assert updated_job.status == "applied"

    def test_apply_empty_db(self, tmp_path: Path):
        db = JobPilotDB(db_path=tmp_path / "empty.db")
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["apply"])
        assert result.exit_code == 0
        assert "没有符合条件" in result.output

    def test_apply_quit(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["apply", "-p", "1", "-m", "7.0"], input="q\n")
        assert result.exit_code == 0
        assert "已退出" in result.output

    def test_apply_invalid_input(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["apply", "-p", "1", "-m", "7.0"], input="abc\n")
        assert result.exit_code == 0
        assert "忽略无效输入" in result.output

    def test_apply_out_of_range(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["apply", "-p", "1", "-m", "7.0"], input="99\n")
        assert result.exit_code == 0
        assert "忽略无效编号" in result.output

    def test_apply_multiple_selection(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["apply", "-p", "1", "-m", "7.0"], input="1,2\n")
        assert result.exit_code == 0
        assert "已标记 2" in result.output


class TestPipelineCommand:
    def test_pipeline_shows_funnel(self, tmp_path: Path):
        db = _setup_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["pipeline"])
        assert result.exit_code == 0
        assert "求职漏斗" in result.output
        assert "搜索" in result.output
        assert "已评分" in result.output

    def test_pipeline_empty_db(self, tmp_path: Path):
        db = JobPilotDB(db_path=tmp_path / "empty.db")
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["pipeline"])
        assert result.exit_code == 0
        assert "求职漏斗" in result.output
