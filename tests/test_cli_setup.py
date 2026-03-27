"""Tests for the setup CLI command (interactive preference questionnaire)."""

from pathlib import Path
from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from jobpilot.cli import app
from jobpilot.setup import (
    CAREER_STAGES,
    prompt_multi,
    prompt_number,
    prompt_ranking,
    prompt_single,
    prompt_text,
    run_questionnaire,
    save_preferences,
)

runner = CliRunner()

# Patch target for typer.prompt is in the setup module
_TYPER_PROMPT = "jobpilot.setup.typer.prompt"
_SETUP_CONFIG = "jobpilot.setup.config"


# ------------------------------------------------------------------
# save_preferences
# ------------------------------------------------------------------
class TestSavePreferences:
    def test_creates_new_file(self, tmp_path: Path):
        prefs = {"career_stage": "在校生", "min_salary": 5000}
        with patch(_SETUP_CONFIG) as mock_config:
            mock_config.DATA_DIR = tmp_path
            path = save_preferences(prefs)
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["preferences"]["career_stage"] == "在校生"
        assert data["preferences"]["min_salary"] == 5000

    def test_preserves_existing_fields(self, tmp_path: Path):
        cfg_path = tmp_path / "resume_config.yaml"
        cfg_path.write_text(
            yaml.dump(
                {"name": "Test User", "skills": [{"category": "SW", "items": ["Python"]}]},
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        with patch(_SETUP_CONFIG) as mock_config:
            mock_config.DATA_DIR = tmp_path
            save_preferences({"career_stage": "在职跳槽"})

        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert data["name"] == "Test User"
        assert data["skills"][0]["items"] == ["Python"]
        assert data["preferences"]["career_stage"] == "在职跳槽"

    def test_merge_preserves_extra_keys(self, tmp_path: Path):
        """Non-questionnaire keys like role_fit are preserved."""
        cfg_path = tmp_path / "resume_config.yaml"
        cfg_path.write_text(
            yaml.dump(
                {"preferences": {"role_fit": "AI产品", "min_salary": 999}},
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        with patch(_SETUP_CONFIG) as mock_config:
            mock_config.DATA_DIR = tmp_path
            save_preferences({"min_salary": 8000, "career_stage": "在校生"})

        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert data["preferences"]["min_salary"] == 8000
        assert data["preferences"]["career_stage"] == "在校生"
        assert data["preferences"]["role_fit"] == "AI产品"

    def test_questionnaire_keys_overwritten(self, tmp_path: Path):
        """Questionnaire keys are overwritten with new values."""
        cfg_path = tmp_path / "resume_config.yaml"
        cfg_path.write_text(
            yaml.dump(
                {"preferences": {"min_salary": 999, "career_stage": "old"}},
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        with patch(_SETUP_CONFIG) as mock_config:
            mock_config.DATA_DIR = tmp_path
            save_preferences({"min_salary": 8000})

        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert data["preferences"]["min_salary"] == 8000
        # career_stage was a questionnaire key but not in new_prefs → removed
        assert "career_stage" not in data["preferences"]


# ------------------------------------------------------------------
# Prompt helpers (unit tests with mock typer.prompt)
# ------------------------------------------------------------------
class TestPromptSingle:
    def test_valid_choice(self):
        with patch(_TYPER_PROMPT, return_value="2"):
            result = prompt_single("Q?", ["A", "B", "C"], 1, 5)
        assert result == "B"

    def test_first_choice(self):
        with patch(_TYPER_PROMPT, return_value="1"):
            result = prompt_single("Q?", CAREER_STAGES, 1, 13)
        assert result == "在校生"

    def test_retries_on_invalid(self):
        with patch(_TYPER_PROMPT, side_effect=["x", "0", "2"]):
            result = prompt_single("Q?", ["A", "B"], 1, 5)
        assert result == "B"


class TestPromptMulti:
    def test_single_selection(self):
        with patch(_TYPER_PROMPT, return_value="1"):
            result = prompt_multi("Q?", ["A", "B", "C"], 1, 5)
        assert result == ["A"]

    def test_multiple_selections(self):
        with patch(_TYPER_PROMPT, return_value="1,3"):
            result = prompt_multi("Q?", ["A", "B", "C"], 1, 5)
        assert result == ["A", "C"]

    def test_custom_input_with_allow_custom(self):
        with patch(_TYPER_PROMPT, side_effect=["4", "自定义内容"]):
            result = prompt_multi("Q?", ["A", "B", "C"], 1, 5, allow_custom=True)
        assert "自定义内容" in result

    def test_fallback_to_first_on_empty(self):
        with patch(_TYPER_PROMPT, return_value=""):
            result = prompt_multi("Q?", ["A", "B"], 1, 5)
        assert result == ["A"]

    def test_free_text_in_input(self):
        with patch(_TYPER_PROMPT, return_value="1,杭州"):
            result = prompt_multi("Q?", ["深圳", "北京"], 1, 5)
        assert "深圳" in result
        assert "杭州" in result


class TestPromptRanking:
    def test_normal_ranking(self):
        with patch(_TYPER_PROMPT, return_value="3,1,2"):
            result = prompt_ranking("Q?", ["A", "B", "C", "D"], 1, 5, top_n=3)
        assert result == ["C", "A", "B"]

    def test_caps_at_top_n(self):
        with patch(_TYPER_PROMPT, return_value="1,2,3,4"):
            result = prompt_ranking("Q?", ["A", "B", "C", "D"], 1, 5, top_n=2)
        assert len(result) == 2

    def test_deduplicates(self):
        with patch(_TYPER_PROMPT, return_value="1,1,2"):
            result = prompt_ranking("Q?", ["A", "B", "C"], 1, 5, top_n=3)
        assert result == ["A", "B"]

    def test_fallback_on_empty(self):
        with patch(_TYPER_PROMPT, return_value=""):
            result = prompt_ranking("Q?", ["A", "B", "C"], 1, 5, top_n=2)
        assert result == ["A", "B"]


class TestPromptNumber:
    def test_valid_number(self):
        with patch(_TYPER_PROMPT, return_value="8000"):
            result = prompt_number("Q?", 1, 5)
        assert result == 8000

    def test_zero(self):
        with patch(_TYPER_PROMPT, return_value="0"):
            result = prompt_number("Q?", 1, 5)
        assert result == 0

    def test_retries_on_invalid(self):
        with patch(_TYPER_PROMPT, side_effect=["abc", "100"]):
            result = prompt_number("Q?", 1, 5)
        assert result == 100


class TestPromptText:
    def test_normal_text(self):
        with patch(_TYPER_PROMPT, return_value="Python, SQL"):
            result = prompt_text("Q?", 1, 5)
        assert result == "Python, SQL"

    def test_skip_with_allow_skip(self):
        with patch(_TYPER_PROMPT, return_value=""):
            result = prompt_text("Q?", 1, 5, allow_skip=True)
        assert result == ""


# ------------------------------------------------------------------
# Full questionnaire flow
# ------------------------------------------------------------------
class TestRunQuestionnaire:
    def test_full_flow(self):
        """Simulate answering all 13 questions."""
        prompts = [
            "1",         # career_stage: 在校生
            "2",         # job_type: 全职
            "1,6",       # career_track: AI产品经理, 数据分析
            "经济学",     # previous_track
            "1,4",       # preferred_industries: AI/大模型, 创业公司
            "1,2",       # preferred_company_size: 大厂, 创业公司
            "1,3",       # preferred_cities: 深圳, 上海
            "4",         # remote_preference: 都可以
            "5000",      # min_salary
            "2,1,3",     # priorities: 成长空间, 薪资, 技术深度
            "1,2",       # deal_breakers: 996, 大小周
            "Python, R, SQL",  # core_strengths
            "AI产品管理",       # learning_goals
        ]
        with patch(_TYPER_PROMPT, side_effect=prompts):
            prefs = run_questionnaire()

        assert prefs["career_stage"] == "在校生"
        assert prefs["job_type"] == "全职"
        assert "AI产品经理" in prefs["career_track"]
        assert "数据分析" in prefs["career_track"]
        assert prefs["previous_track"] == "经济学"
        assert "AI/大模型" in prefs["preferred_industries"]
        assert "创业公司" in prefs["preferred_industries"]
        assert "大厂" in prefs["preferred_company_size"]
        assert "深圳" in prefs["preferred_cities"]
        assert "上海" in prefs["preferred_cities"]
        assert prefs["remote_preference"] == "都可以"
        assert prefs["min_salary"] == 5000
        assert prefs["priorities"] == ["成长空间", "薪资", "技术深度"]
        assert "996" in prefs["deal_breakers"]
        assert prefs["core_strengths"] == "Python, R, SQL"
        assert prefs["learning_goals"] == "AI产品管理"


# ------------------------------------------------------------------
# CLI integration (setup command)
# ------------------------------------------------------------------
class TestSetupCommand:
    def test_setup_saves_yaml(self, tmp_path: Path):
        """Full integration: setup command saves preferences to YAML."""
        prompts = [
            "1", "2", "1,6", "", "1,4", "1,2", "1,3",
            "4", "5000", "2,1,3", "1,2", "Python", "AI",
        ]
        with (
            patch(_TYPER_PROMPT, side_effect=prompts),
            patch(_SETUP_CONFIG) as mock_config,
        ):
            mock_config.DATA_DIR = tmp_path
            result = runner.invoke(app, ["setup"])

        assert result.exit_code == 0
        assert "偏好已保存到" in result.output
        assert "偏好设置摘要" in result.output

        cfg_path = tmp_path / "resume_config.yaml"
        assert cfg_path.exists()
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert "preferences" in data
        assert data["preferences"]["career_stage"] == "在校生"
        assert data["preferences"]["min_salary"] == 5000

    def test_setup_shows_summary_table(self, tmp_path: Path):
        prompts = [
            "1", "1", "1", "", "1", "1", "1",
            "1", "0", "1,2,3", "1", "X", "Y",
        ]
        with (
            patch(_TYPER_PROMPT, side_effect=prompts),
            patch(_SETUP_CONFIG) as mock_config,
        ):
            mock_config.DATA_DIR = tmp_path
            result = runner.invoke(app, ["setup"])

        assert result.exit_code == 0
        assert "偏好设置摘要" in result.output
        assert "career_stage" in result.output
        assert "jobpilot score" in result.output

    def test_setup_confirm_on_existing(self, tmp_path: Path):
        """When preferences exist, shows confirmation prompt."""
        cfg_path = tmp_path / "resume_config.yaml"
        cfg_path.write_text(
            yaml.dump({"preferences": {"min_salary": 999}}, allow_unicode=True),
            encoding="utf-8",
        )
        with (
            patch(_SETUP_CONFIG) as mock_config,
            patch("jobpilot.cli.typer.confirm", return_value=False),
            patch("jobpilot.setup.load_existing_preferences", return_value={"min_salary": 999}),
        ):
            mock_config.DATA_DIR = tmp_path
            result = runner.invoke(app, ["setup"])

        # Should exit without running questionnaire
        assert result.exit_code == 0

    def test_setup_confirm_yes_runs_questionnaire(self, tmp_path: Path):
        """When user confirms, questionnaire runs."""
        prompts = [
            "1", "1", "1", "", "1", "1", "1",
            "1", "0", "1,2,3", "1", "X", "Y",
        ]
        with (
            patch(_TYPER_PROMPT, side_effect=prompts),
            patch(_SETUP_CONFIG) as mock_config,
            patch("jobpilot.setup.load_existing_preferences", return_value={"min_salary": 999}),
            patch("jobpilot.cli.typer.confirm", return_value=True),
        ):
            mock_config.DATA_DIR = tmp_path
            result = runner.invoke(app, ["setup"])

        assert result.exit_code == 0
        assert "偏好已保存到" in result.output


# ------------------------------------------------------------------
# Scorer integration with new fields
# ------------------------------------------------------------------
class TestScorerNewFields:
    """Test that _score_preference handles new fields from setup."""

    def _make_job(self, **overrides) -> "Job":
        from jobpilot.models import Job
        defaults = dict(
            platform="boss", job_id="test_001", title="AI产品实习生",
            company="创业公司A", salary_min=5000, salary_max=10000,
            city="深圳", experience="实习", education="本科",
            jd_text="远程办公，AI产品经理实习，负责大模型产品需求分析",
            raw_data={}, discovered_at="2026-03-26", status="new",
        )
        defaults.update(overrides)
        return Job(**defaults)

    def test_job_type_intern_match(self):
        from jobpilot.ai.scorer import _score_preference

        prefs = {
            "preferred_industries": ["AI"],
            "preferred_cities": ["深圳"],
            "career_track": ["AI产品经理"],
            "deal_breakers": [],
            "min_salary": 0,
            "job_type": "实习",
        }
        job = self._make_job()
        score, positives, negatives = _score_preference(job, prefs)
        assert score > 5.0
        assert any("工作类型" in p for p in positives)

    def test_job_type_fulltime_mismatch_with_intern_jd(self):
        from jobpilot.ai.scorer import _score_preference

        prefs = {
            "preferred_industries": [],
            "preferred_cities": [],
            "career_track": [],
            "deal_breakers": [],
            "min_salary": 0,
            "job_type": "全职",
        }
        job = self._make_job(title="AI产品实习生", jd_text="实习岗位，负责产品需求分析")
        score, positives, negatives = _score_preference(job, prefs)
        assert any("实习" in n for n in negatives)

    def test_remote_preference_match(self):
        from jobpilot.ai.scorer import _score_preference

        prefs = {
            "preferred_industries": [],
            "preferred_cities": [],
            "career_track": [],
            "deal_breakers": [],
            "min_salary": 0,
            "remote_preference": "纯远程",
        }
        job = self._make_job(jd_text="支持远程办公，AI产品经理")
        score, positives, negatives = _score_preference(job, prefs)
        assert any("远程" in p for p in positives)

    def test_remote_only_domestic_with_overseas_jd(self):
        from jobpilot.ai.scorer import _score_preference

        prefs = {
            "preferred_industries": [],
            "preferred_cities": [],
            "career_track": [],
            "deal_breakers": [],
            "min_salary": 0,
            "remote_preference": "只接受国内线下",
        }
        job = self._make_job(jd_text="海外团队，负责全球产品")
        score, positives, negatives = _score_preference(job, prefs)
        assert any("海外" in n for n in negatives)

    def test_legacy_prefs_backward_compatible(self):
        """Old prefs without job_type/remote_preference still work."""
        from jobpilot.ai.scorer import _score_preference

        prefs = {
            "preferred_industries": ["AI"],
            "preferred_cities": ["深圳"],
            "career_track": ["AI产品经理"],
            "deal_breakers": [],
            "min_salary": 0,
        }
        job = self._make_job()
        score, positives, negatives = _score_preference(job, prefs)
        assert 1.0 <= score <= 10.0
