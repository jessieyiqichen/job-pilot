"""Unit tests for the tailor module's new light-touch logic."""

from pathlib import Path
from unittest.mock import patch

import yaml

from jobpilot.ai.tailor import (
    _format_skills_text,
    _load_skills_config,
    _basic_tailor,
    tailor_from_text,
)
from jobpilot.models import Job, Profile


def _make_profile() -> Profile:
    return Profile(
        name="Test User",
        raw_text="Jane Doe\nSUMMARY\nGraduate student.\nSKILLS\nPython, R, SQL",
        structured={
            "name": "Test User",
            "skills": {"languages": ["Python", "R"], "tools": ["Git"]},
        },
        updated_at="2026-03-25",
    )


def _make_job() -> Job:
    return Job(
        platform="boss",
        job_id="j001",
        title="Data Analyst",
        company="TestCo",
        salary_min=10000,
        salary_max=20000,
        city="Shanghai",
        jd_text="Requires Python and SQL",
        raw_data={},
        discovered_at="2026-03-25",
    )


class TestFormatSkillsText:
    def test_from_config(self):
        config = {
            "skills": [
                {"category": "Programming", "items": ["Python", "R"]},
                {"category": "Tools", "items": ["Git", "Docker"]},
            ]
        }
        result = _format_skills_text(config, _make_profile())
        assert "Programming: Python, R" in result
        assert "Tools: Git, Docker" in result

    def test_fallback_to_profile(self):
        result = _format_skills_text({}, _make_profile())
        assert "Python" in result
        assert "R" in result

    def test_empty_config_and_profile(self):
        empty_profile = Profile(
            name="X", raw_text="", structured={}, updated_at="2026-03-25",
        )
        result = _format_skills_text({}, empty_profile)
        assert result == ""


class TestLoadSkillsConfig:
    def test_missing_file(self, tmp_path: Path):
        with patch("jobpilot.ai.tailor.RESUME_CONFIG_PATH", tmp_path / "nope.yaml"):
            result = _load_skills_config()
        assert result == {}

    def test_valid_file(self, tmp_path: Path):
        cfg_path = tmp_path / "resume_config.yaml"
        cfg_path.write_text(yaml.dump({"skills": [{"category": "Lang", "items": ["Python"]}]}))
        with patch("jobpilot.ai.tailor.RESUME_CONFIG_PATH", cfg_path):
            result = _load_skills_config()
        assert len(result["skills"]) == 1


class TestBasicTailor:
    def test_prepends_target_line(self, tmp_path: Path):
        profile = _make_profile()
        job = _make_job()
        with patch("jobpilot.ai.tailor.config.TAILORED_DIR", tmp_path):
            result = _basic_tailor(profile, job)
        assert result.startswith("TARGET: Data Analyst @ TestCo")
        assert "Jane Doe" in result

    def test_preserves_original_text(self, tmp_path: Path):
        profile = _make_profile()
        job = _make_job()
        with patch("jobpilot.ai.tailor.config.TAILORED_DIR", tmp_path):
            result = _basic_tailor(profile, job)
        assert profile.raw_text in result

    def test_exports_prompt_file(self, tmp_path: Path):
        """When API is unavailable, _basic_tailor should export a prompt file."""
        profile = _make_profile()
        job = _make_job()
        with patch("jobpilot.ai.tailor.config.TAILORED_DIR", tmp_path):
            _basic_tailor(profile, job)
        prompt_files = list(tmp_path.glob("*_prompt.txt"))
        assert len(prompt_files) == 1
        content = prompt_files[0].read_text(encoding="utf-8")
        # Prompt should contain the resume text and job info
        assert "Jane Doe" in content
        assert "Data Analyst" in content
        assert "TestCo" in content

    def test_prompt_file_contains_full_prompt(self, tmp_path: Path):
        """Exported prompt should contain the full tailor methodology."""
        profile = _make_profile()
        job = _make_job()
        with patch("jobpilot.ai.tailor.config.TAILORED_DIR", tmp_path):
            _basic_tailor(profile, job)
        prompt_files = list(tmp_path.glob("*_prompt.txt"))
        content = prompt_files[0].read_text(encoding="utf-8")
        assert "Tailoring Philosophy" in content
        assert "Strict Accuracy" in content


class TestFormatContactInfo:
    def test_with_github(self):
        from jobpilot.ai.tailor import _format_contact_info
        config = {
            "name": "Jessie Chen",
            "email": "jane@example.com",
            "phone": "123-456-7890",
            "location": "Chicago, IL",
            "github": "https://github.com/janedoe",
        }
        result = _format_contact_info(config)
        assert "Jessie Chen" in result
        assert "jane@example.com" in result
        assert "https://github.com/janedoe" in result

    def test_without_github(self):
        from jobpilot.ai.tailor import _format_contact_info
        config = {
            "name": "Jessie Chen",
            "email": "jane@example.com",
        }
        result = _format_contact_info(config)
        assert "GitHub" not in result
        assert "Jessie Chen" in result

    def test_empty_config(self):
        from jobpilot.ai.tailor import _format_contact_info
        result = _format_contact_info({})
        assert result == "(no contact info configured)"

    def test_prompt_includes_contact(self):
        """TAILOR_PROMPT should have a contact info placeholder."""
        from jobpilot.ai.tailor import TAILOR_PROMPT
        assert "{contact_info}" in TAILOR_PROMPT


class TestInjectGithubLink:
    def test_inject_into_contact_line(self):
        """_inject_github_link should add GitHub URL to a contact paragraph."""
        from unittest.mock import MagicMock
        from jobpilot.ai.tailor import _inject_github_link

        # Mock a document with a contact paragraph
        run = MagicMock()
        run.text = "jane@example.com | 123-456-7890"
        para = MagicMock()
        para.text = "jane@example.com | 123-456-7890"
        para.runs = [run]

        doc = MagicMock()
        doc.paragraphs = [para]

        _inject_github_link(doc, "https://github.com/janedoe")
        assert "GitHub: https://github.com/janedoe" in run.text

    def test_no_duplicate_injection(self):
        """Should not inject if github is already present."""
        from unittest.mock import MagicMock
        from jobpilot.ai.tailor import _inject_github_link

        run = MagicMock()
        run.text = "jane@example.com | GitHub: https://github.com/janedoe"
        para = MagicMock()
        para.text = "jane@example.com | GitHub: https://github.com/janedoe"
        para.runs = [run]

        doc = MagicMock()
        doc.paragraphs = [para]

        original_text = run.text
        _inject_github_link(doc, "https://github.com/janedoe")
        assert run.text == original_text


class TestTailorFromText:
    def test_creates_txt_when_no_docx(self, tmp_path: Path):
        """tailor_from_text should create .txt when no source docx is available."""
        job = _make_job()
        tailored_text = "Tailored resume content here.\nWith multiple lines."
        with patch("jobpilot.ai.tailor._find_source_docx", return_value=None):
            result_path = tailor_from_text(tailored_text, job, output_dir=tmp_path)
        assert result_path.exists()
        assert result_path.suffix == ".txt"
        assert result_path.read_text(encoding="utf-8") == tailored_text

    def test_output_filename_contains_company_and_title(self, tmp_path: Path):
        """Output file should be named with company and title."""
        job = _make_job()
        with patch("jobpilot.ai.tailor._find_source_docx", return_value=None):
            result_path = tailor_from_text("content", job, output_dir=tmp_path)
        assert "TestCo" in result_path.name
        assert "Data Analyst" in result_path.name
