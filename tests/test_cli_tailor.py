"""Tests for the CLI tailor and pdf commands."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.db import JobPilotDB
from jobpilot.models import Job, Profile

runner = CliRunner()


def _make_test_db(tmp_path: Path) -> JobPilotDB:
    """Create a test DB with a profile and a job."""
    db = JobPilotDB(db_path=tmp_path / "test.db")
    profile = Profile(
        name="测试用户",
        raw_text="测试简历内容",
        structured={
            "name": "测试用户",
            "title": "Python开发工程师",
            "skills": {"languages": ["Python", "Go"]},
            "experience": [{"title": "开发工程师", "company": "测试公司", "highlights": ["做了很多事"]}],
            "education": [{"school": "测试大学", "degree": "本科", "major": "计算机"}],
        },
        updated_at="2026-03-25 10:00:00",
    )
    db.upsert_profile(profile)

    job = Job(
        platform="boss",
        job_id="test_job_001",
        title="Python后端开发",
        company="字节跳动",
        salary_min=25000,
        salary_max=50000,
        city="上海",
        experience="3-5年",
        education="本科",
        jd_text="负责后端系统开发",
        raw_data={"source": "test"},
        discovered_at="2026-03-25 10:00:00",
        status="scored",
    )
    db.upsert_job(job)
    return db


class TestTailorCommand:
    def test_tailor_success(self, tmp_path: Path):
        db = _make_test_db(tmp_path)
        tailored_dir = tmp_path / "tailored"

        with (
            patch("jobpilot.cli._get_db", return_value=db),
            patch(
                "jobpilot.ai.tailor.save_tailored_resume",
                return_value=tailored_dir / "output.md",
            ) as mock_save,
        ):
            result = runner.invoke(app, ["tailor", "test_job_001", "-p", "1", "-o", str(tailored_dir)])

        assert result.exit_code == 0
        assert "Tailored resume saved" in result.output
        assert "tailored" in result.output
        mock_save.assert_called_once()

        # Verify job status was updated
        updated_job = db.get_job("test_job_001")
        assert updated_job.status == "tailored"

    def test_tailor_missing_profile(self, tmp_path: Path):
        db = JobPilotDB(db_path=tmp_path / "empty.db")

        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["tailor", "some_job"])

        assert result.exit_code == 1
        assert "No profile found" in result.output

    def test_tailor_missing_job(self, tmp_path: Path):
        db = _make_test_db(tmp_path)

        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["tailor", "nonexistent_job", "-p", "1"])

        assert result.exit_code == 1
        assert "Job not found" in result.output


class TestBatchTailor:
    def test_batch_top_3(self, tmp_path: Path):
        db = _make_test_db(tmp_path)
        # Add more scored jobs
        for i in range(1, 4):
            job = Job(
                platform="boss",
                job_id=f"batch_job_{i:03d}",
                title=f"数据分析{i}",
                company=f"公司{i}",
                salary_min=10000,
                salary_max=20000,
                city="上海",
                experience="1-3年",
                education="本科",
                jd_text="技能要求：Python, SQL",
                raw_data={},
                discovered_at="2026-03-25",
                status="scored",
            )
            db.upsert_job(job)
            from jobpilot.models import JobScore
            score = JobScore(
                job_id=f"batch_job_{i:03d}",
                profile_id=1,
                overall_score=8.0 - i * 0.3,
                skill_match=7.0,
                experience_match=7.0,
                salary_match=7.0,
                highlights=[],
                concerns=[],
                suggestion="ok",
                scored_at="2026-03-25",
            )
            db.upsert_score(score)

        with (
            patch("jobpilot.cli._get_db", return_value=db),
            patch(
                "jobpilot.ai.tailor.save_tailored_resume",
                return_value=tmp_path / "out.docx",
            ),
        ):
            result = runner.invoke(app, ["tailor", "--top", "3", "-p", "1"])

        assert result.exit_code == 0
        assert "批量定制" in result.output
        assert "OK" in result.output

    def test_batch_no_candidates(self, tmp_path: Path):
        db = _make_test_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["tailor", "--top", "5", "-p", "1"])
        assert result.exit_code == 0
        assert "没有待定制" in result.output

    def test_batch_missing_profile(self, tmp_path: Path):
        db = JobPilotDB(db_path=tmp_path / "empty.db")
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["tailor", "--top", "3"])
        assert result.exit_code == 1
        assert "No profile found" in result.output

    def test_no_args_shows_error(self, tmp_path: Path):
        db = _make_test_db(tmp_path)
        with patch("jobpilot.cli._get_db", return_value=db):
            result = runner.invoke(app, ["tailor"])
        assert result.exit_code == 1
        assert "请指定" in result.output

    def test_tailor_shows_next_step(self, tmp_path: Path):
        """After single tailor, should show next step hint."""
        db = _make_test_db(tmp_path)
        tailored_dir = tmp_path / "tailored"
        with (
            patch("jobpilot.cli._get_db", return_value=db),
            patch(
                "jobpilot.ai.tailor.save_tailored_resume",
                return_value=tailored_dir / "output.md",
            ),
        ):
            result = runner.invoke(app, ["tailor", "test_job_001", "-p", "1", "-o", str(tailored_dir)])
        assert result.exit_code == 0
        assert "jobpilot apply" in result.output


class TestPdfCommand:
    def test_pdf_file_not_found(self):
        result = runner.invoke(app, ["pdf", "/nonexistent/file.md"])
        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_pdf_weasyprint_not_installed(self, tmp_path: Path):
        md_file = tmp_path / "resume.md"
        md_file.write_text("# Test Resume\n\nContent here.")

        with patch(
            "jobpilot.resume.generator.markdown_to_pdf",
            side_effect=ImportError("PDF generation requires weasyprint."),
        ):
            result = runner.invoke(app, ["pdf", str(md_file)])

        assert result.exit_code == 1
        assert "weasyprint" in result.output

    def test_pdf_success(self, tmp_path: Path):
        md_file = tmp_path / "resume.md"
        md_file.write_text("# Test Resume")
        pdf_output = tmp_path / "resume.pdf"

        with patch(
            "jobpilot.resume.generator.markdown_to_pdf",
            return_value=pdf_output,
        ):
            result = runner.invoke(app, ["pdf", str(md_file)])

        assert result.exit_code == 0
        assert "PDF generated" in result.output
