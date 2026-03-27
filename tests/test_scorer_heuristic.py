"""Tests for the enhanced heuristic scoring logic."""

from unittest.mock import patch

from jobpilot.ai.scorer import (
    _extract_jd_skills,
    _extract_profile_skills,
    _heuristic_score,
    _normalize_skill,
    _parse_education_level,
    _parse_exp_years_required,
    _score_education,
    _score_experience,
    _score_skills,
    _score_title_relevance,
    _skill_matches,
)
from jobpilot.models import Job, JobScore, Profile


def _make_profile(**overrides) -> Profile:
    defaults = dict(
        id=1,
        name="Jane Doe",
        raw_text="Jane Doe\nSUMMARY\nEconomics graduate.\nSKILLS\nPython, R, SQL",
        structured={
            "name": "Jane Doe",
            "title": "Data Analyst",
            "years_of_experience": 1,
            "skills": {
                "programming": ["Python", "R", "SQL", "Stata"],
                "methods": [
                    "Machine Learning",
                    "Causal Inference",
                    "NLP",
                    "Data Visualization",
                ],
            },
            "education": [
                {
                    "school": "University of Chicago",
                    "degree": "Master",
                    "major": "Economics",
                }
            ],
            "experience": [
                {
                    "title": "Research Assistant",
                    "highlights": [
                        "Built predictive models using Python and scikit-learn",
                        "Conducted causal inference analysis on economic data",
                    ],
                }
            ],
            "projects": [
                {
                    "name": "Stock Price Prediction",
                    "description": "LSTM model for stock prediction",
                    "tech_stack": ["Python", "TensorFlow", "Pandas"],
                }
            ],
        },
        updated_at="2026-03-25",
    )
    defaults.update(overrides)
    return Profile(**defaults)


def _make_job(**overrides) -> Job:
    defaults = dict(
        platform="boss",
        job_id="test_001",
        title="数据分析师",
        company="TestCo",
        salary_min=10000,
        salary_max=20000,
        city="上海",
        experience="1-3年",
        education="本科",
        jd_text=(
            "岗位职责：\n"
            "1. 负责业务数据分析，输出数据报告\n"
            "2. 搭建数据看板\n\n"
            "技能要求：Python, SQL, Excel, 数据可视化\n"
            "熟悉机器学习优先"
        ),
        raw_data={},
        discovered_at="2026-03-25",
    )
    defaults.update(overrides)
    return Job(**defaults)


class TestNormalizeSkill:
    def test_strips_proficiency(self):
        assert _normalize_skill("Python (Expert)") == "python"
        assert _normalize_skill("R (Proficient)") == "r"

    def test_lowercases(self):
        assert _normalize_skill("SQL") == "sql"


class TestSkillMatching:
    def test_chinese_jd_skill_extraction(self):
        jd = "技能要求：Python, SQL, Excel, 数据可视化\n熟悉机器学习优先"
        skills = _extract_jd_skills(jd)
        assert "python" in skills
        assert "sql" in skills
        assert "excel" in skills

    def test_english_jd_skill_extraction(self):
        jd = "Requirements: Python, machine learning, SQL, data visualization"
        skills = _extract_jd_skills(jd)
        assert "python" in skills
        assert "sql" in skills
        assert "machine learning" in skills

    def test_skill_alias_matching(self):
        assert _skill_matches("Machine Learning", "机器学习")
        assert _skill_matches("NLP", "自然语言处理")
        assert _skill_matches("Python (Expert)", "python3")

    def test_direct_substring_match(self):
        assert _skill_matches("python", "python")
        assert _skill_matches("sql", "sql")

    def test_profile_skill_extraction(self):
        profile = _make_profile()
        skills = _extract_profile_skills(profile)
        assert "python" in skills
        assert "r" in skills
        assert "sql" in skills

    def test_score_skills_with_matches(self):
        profile = _make_profile()
        job = _make_job()
        score, matched, missing = _score_skills(profile, job)
        assert score > 0
        assert len(matched) > 0
        assert isinstance(score, float)

    def test_score_skills_empty_jd(self):
        profile = _make_profile()
        job = _make_job(jd_text="This is a generic role with no specific skills mentioned.")
        score, matched, missing = _score_skills(profile, job)
        assert 0 <= score <= 10


class TestExperienceMatching:
    def test_intern_position(self):
        profile = _make_profile(
            structured={**_make_profile().structured, "years_of_experience": 0}
        )
        job = _make_job(experience="实习")
        score, explanation = _score_experience(profile, job)
        assert score >= 8.0
        assert "实习" in explanation or "应届" in explanation

    def test_fresh_graduate(self):
        profile = _make_profile(
            structured={**_make_profile().structured, "years_of_experience": 0}
        )
        job = _make_job(experience="应届生")
        score, _ = _score_experience(profile, job)
        assert score >= 8.0

    def test_experience_match(self):
        profile = _make_profile(
            structured={**_make_profile().structured, "years_of_experience": 2}
        )
        job = _make_job(experience="1-3年")
        score, _ = _score_experience(profile, job)
        assert score >= 8.0

    def test_experience_insufficient(self):
        profile = _make_profile(
            structured={**_make_profile().structured, "years_of_experience": 1}
        )
        job = _make_job(experience="5-10年")
        score, _ = _score_experience(profile, job)
        assert score < 7.0

    def test_parse_exp_years(self):
        assert _parse_exp_years_required("1-3年") == (1.0, 3.0)
        assert _parse_exp_years_required("实习") == (0, 0)
        assert _parse_exp_years_required("经验不限") == (0, 99)
        assert _parse_exp_years_required("应届生") == (0, 1)


class TestEducationMatching:
    def test_education_level_parsing(self):
        assert _parse_education_level("本科") == 2
        assert _parse_education_level("硕士") == 3
        assert _parse_education_level("博士") == 4
        assert _parse_education_level("大专") == 1
        assert _parse_education_level("Bachelor") == 2
        assert _parse_education_level("Master") == 3

    def test_education_match(self):
        profile = _make_profile()
        job = _make_job(education="本科")
        score, _ = _score_education(profile, job)
        # Master >= 本科
        assert score >= 8.0

    def test_education_below_requirement(self):
        profile = _make_profile(
            structured={
                **_make_profile().structured,
                "education": [{"school": "X College", "degree": "大专", "major": "CS"}],
            }
        )
        job = _make_job(education="硕士")
        score, _ = _score_education(profile, job)
        assert score < 7.0


class TestTitleRelevance:
    def test_data_analyst_relevance(self):
        profile = _make_profile()
        job = _make_job(title="数据分析师")
        score, explanation = _score_title_relevance(profile, job)
        assert score >= 5.0

    def test_unrelated_title(self):
        profile = _make_profile()
        job = _make_job(title="UI设计师")
        score, _ = _score_title_relevance(profile, job)
        assert score <= 7.0


class TestSuggestionGeneration:
    @patch("jobpilot.ai.scorer.config")
    def test_high_score_suggestion(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = ""
        profile = _make_profile()
        job = _make_job()
        result = _heuristic_score(profile, job)
        if result.overall_score >= 7.0:
            assert "建议投递" in result.suggestion
        elif result.overall_score >= 5.0:
            assert "可考虑" in result.suggestion

    @patch("jobpilot.ai.scorer.config")
    def test_low_score_suggestion(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = ""
        profile = _make_profile(
            structured={
                "name": "Test",
                "skills": {},
                "education": [],
                "experience": [],
                "projects": [],
                "years_of_experience": 0,
            }
        )
        job = _make_job(
            title="高级Java架构师",
            experience="10年以上",
            education="硕士",
            jd_text="技能要求：Java, Spring Boot, Kubernetes, 微服务架构\n10年以上分布式系统经验",
        )
        result = _heuristic_score(profile, job)
        assert result.overall_score < 7.0


class TestOverallScoreReasonable:
    @patch("jobpilot.ai.scorer.config")
    def test_score_range(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = ""
        profile = _make_profile()
        job = _make_job()
        result = _heuristic_score(profile, job)
        assert 1.0 <= result.overall_score <= 10.0
        assert 0.0 <= result.skill_match <= 10.0
        assert 0.0 <= result.experience_match <= 10.0

    @patch("jobpilot.ai.scorer.config")
    def test_good_match_scores_high(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = ""
        profile = _make_profile()
        job = _make_job(
            title="数据分析实习生",
            experience="实习",
            education="本科",
            jd_text="技能要求：Python, SQL, 数据分析\n经济学相关专业优先",
        )
        result = _heuristic_score(profile, job)
        assert result.overall_score >= 6.0


class TestBackwardCompatible:
    @patch("jobpilot.ai.scorer.config")
    def test_returns_jobscore_type(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = ""
        profile = _make_profile()
        job = _make_job()
        result = _heuristic_score(profile, job)
        assert isinstance(result, JobScore)

    @patch("jobpilot.ai.scorer.config")
    def test_has_all_fields(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = ""
        profile = _make_profile()
        job = _make_job()
        result = _heuristic_score(profile, job)
        assert result.job_id == "test_001"
        assert result.profile_id == 1
        assert isinstance(result.overall_score, float)
        assert isinstance(result.skill_match, float)
        assert isinstance(result.experience_match, float)
        assert isinstance(result.salary_match, float)
        assert isinstance(result.highlights, list)
        assert isinstance(result.concerns, list)
        assert isinstance(result.suggestion, str)
        assert result.scored_at != ""
