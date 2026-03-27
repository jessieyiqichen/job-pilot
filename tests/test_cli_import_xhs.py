"""Tests for the import-xhs CLI command."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from jobpilot.cli import app

runner = CliRunner()


class TestImportXhsCommand:
    def _write_json(self, data: list[dict], path: Path) -> Path:
        """Write test JSON data to a temp file."""
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    @patch("jobpilot.cli._get_db")
    def test_import_valid_jobs(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.upsert_jobs.return_value = 2
        mock_get_db.return_value = mock_db

        data = [
            {"company": "字节跳动", "title": "AI工程师", "salary": "30-50K", "city": "上海"},
            {"company": "阿里巴巴", "title": "算法工程师", "salary": "25-40K", "city": "杭州"},
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            result = runner.invoke(app, ["import-xhs", f.name])

        assert result.exit_code == 0
        assert "Imported 2 jobs" in result.output
        assert "字节跳动" in result.output
        assert "阿里巴巴" in result.output
        mock_db.upsert_jobs.assert_called_once()

    @patch("jobpilot.cli._get_db")
    def test_import_skips_invalid(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.upsert_jobs.return_value = 1
        mock_get_db.return_value = mock_db

        data = [
            {"company": "字节跳动", "title": "AI工程师"},
            {"company": "", "title": "无效岗位"},
            {"title": "也无效"},
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            result = runner.invoke(app, ["import-xhs", f.name])

        assert result.exit_code == 0
        assert "Imported 1 jobs" in result.output
        # Only the valid job (字节跳动) was passed to upsert
        call_args = mock_db.upsert_jobs.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0].company == "字节跳动"

    def test_import_file_not_found(self):
        result = runner.invoke(app, ["import-xhs", "/nonexistent/file.json"])
        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_import_invalid_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
            result = runner.invoke(app, ["import-xhs", f.name])

        assert result.exit_code == 1
        assert "Invalid JSON" in result.output

    def test_import_not_array(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"company": "test"}, f)
            f.flush()
            result = runner.invoke(app, ["import-xhs", f.name])

        assert result.exit_code == 1
        assert "array" in result.output

    @patch("jobpilot.cli._get_db")
    def test_import_empty_valid(self, mock_get_db):
        """All entries invalid → exit 0 with warning."""
        data = [
            {"company": "", "title": ""},
            {"title": "no company"},
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            result = runner.invoke(app, ["import-xhs", f.name])

        assert result.exit_code == 0
        assert "No valid job" in result.output

    @patch("jobpilot.cli._do_score")
    @patch("jobpilot.cli._get_db")
    def test_import_with_score_flag(self, mock_get_db, mock_do_score):
        mock_db = MagicMock()
        mock_db.upsert_jobs.return_value = 1
        mock_get_db.return_value = mock_db

        data = [{"company": "A公司", "title": "开发", "salary": "15-25K"}]

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            result = runner.invoke(app, ["import-xhs", f.name, "--score"])

        assert result.exit_code == 0
        assert "Imported 1 jobs" in result.output
        mock_do_score.assert_called_once()

    @patch("jobpilot.cli._get_db")
    def test_import_displays_salary(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.upsert_jobs.return_value = 1
        mock_get_db.return_value = mock_db

        data = [{"company": "Test", "title": "Dev", "salary": "20-35K", "city": "深圳"}]

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            result = runner.invoke(app, ["import-xhs", f.name])

        assert result.exit_code == 0
        assert "20-35K" in result.output
        assert "深圳" in result.output

    @patch("jobpilot.cli._get_db")
    def test_import_no_salary_shows_negotiable(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.upsert_jobs.return_value = 1
        mock_get_db.return_value = mock_db

        data = [{"company": "Test", "title": "Dev"}]

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            result = runner.invoke(app, ["import-xhs", f.name])

        assert result.exit_code == 0
        assert "面议" in result.output
