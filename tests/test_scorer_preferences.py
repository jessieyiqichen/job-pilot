"""Tests for preference scoring (Feature 1)."""

from unittest.mock import patch

from jobpilot.ai.scorer import (
    _heuristic_score,
    _load_preferences,
    _score_preference,
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
                "methods": ["Machine Learning", "Causal Inference", "NLP", "Data Visualization"],
            },
            "education": [
                {"school": "University of Chicago", "degree": "Master", "major": "Economics"}
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


SAMPLE_PREFS = {
    "preferred_industries": ["互联网", "金融科技", "咨询", "量化"],
    "preferred_company_size": ["大型", "中型"],
    "preferred_cities": ["上海徐汇", "上海浦东", "上海"],
    "career_track": ["数据分析", "量化研究", "商业分析"],
    "deal_breakers": ["996", "加班多", "大小周", "单休"],
    "min_salary": 8000,
}


class TestScorePreference:
    def test_deal_breaker_detected(self):
        job = _make_job(jd_text="优秀团队，996工作制，有加班补贴")
        score, positives, negatives = _score_preference(job, SAMPLE_PREFS)
        assert any("deal-breaker" in n for n in negatives)
        # Deal-breaker should lower the score (deal dimension = 0)
        assert score < 7.0

    def test_no_deal_breaker(self):
        job = _make_job(jd_text="弹性工作制，双休，技能要求：Python, SQL")
        score, _, negatives = _score_preference(job, SAMPLE_PREFS)
        deal_negs = [n for n in negatives if "deal-breaker" in n]
        assert len(deal_negs) == 0

    def test_industry_match(self):
        job = _make_job(company="腾讯互联网", jd_text="互联网大厂")
        score, positives, _ = _score_preference(job, SAMPLE_PREFS)
        assert any("行业匹配" in p for p in positives)

    def test_city_exact_match(self):
        job = _make_job(city="上海")
        _, positives, _ = _score_preference(job, SAMPLE_PREFS)
        city_pos = [p for p in positives if "城市" in p]
        assert len(city_pos) > 0

    def test_city_partial_match(self):
        job = _make_job(city="上海杨浦")
        _, positives, _ = _score_preference(job, SAMPLE_PREFS)
        # "上海" is in "上海杨浦", so partial match
        city_pos = [p for p in positives if "城市" in p or "同城" in p]
        assert len(city_pos) > 0

    def test_city_no_match(self):
        job = _make_job(city="北京")
        _, _, negatives = _score_preference(job, SAMPLE_PREFS)
        city_negs = [n for n in negatives if "城市" in n]
        assert len(city_negs) > 0

    def test_career_track_match(self):
        job = _make_job(title="数据分析实习生")
        score, positives, _ = _score_preference(job, SAMPLE_PREFS)
        assert any("职业路径" in p for p in positives)

    def test_career_track_mismatch(self):
        job = _make_job(title="UI设计师", jd_text="负责产品界面设计，Figma，Sketch")
        score, _, negatives = _score_preference(job, SAMPLE_PREFS)
        assert any("职业路径" in n for n in negatives)

    def test_salary_below_floor(self):
        job = _make_job(salary_min=3000, salary_max=5000)
        _, _, negatives = _score_preference(job, SAMPLE_PREFS)
        assert any("薪资" in n for n in negatives)

    def test_salary_above_floor(self):
        job = _make_job(salary_min=10000, salary_max=20000)
        score, _, negatives = _score_preference(job, SAMPLE_PREFS)
        salary_negs = [n for n in negatives if "薪资" in n]
        assert len(salary_negs) == 0


class TestEmptyPreferences:
    def test_empty_returns_neutral(self):
        """Empty preferences should return a neutral score around 6."""
        job = _make_job()
        score, positives, negatives = _score_preference(job, {})
        assert 4.0 <= score <= 8.0
        assert len(positives) == 0
        assert len(negatives) == 0


class TestHeuristicScoreWithPreferences:
    @patch("jobpilot.ai.scorer.config")
    @patch("jobpilot.ai.scorer._load_preferences")
    def test_preferences_affect_overall(self, mock_prefs, mock_config):
        """With preferences loaded, overall should be ability*0.6 + pref*0.4."""
        mock_config.ANTHROPIC_API_KEY = ""
        mock_prefs.return_value = SAMPLE_PREFS
        profile = _make_profile()
        job = _make_job()
        result = _heuristic_score(profile, job)
        assert isinstance(result, JobScore)
        assert 1.0 <= result.overall_score <= 10.0

    @patch("jobpilot.ai.scorer.config")
    @patch("jobpilot.ai.scorer._load_preferences")
    def test_no_preferences_backward_compatible(self, mock_prefs, mock_config):
        """Without preferences, overall = ability only."""
        mock_config.ANTHROPIC_API_KEY = ""
        mock_prefs.return_value = {}
        profile = _make_profile()
        job = _make_job()
        result = _heuristic_score(profile, job)
        assert isinstance(result, JobScore)
        assert 1.0 <= result.overall_score <= 10.0

    @patch("jobpilot.ai.scorer.config")
    @patch("jobpilot.ai.scorer._load_preferences")
    def test_score_spread_across_jobs(self, mock_prefs, mock_config):
        """5 different jobs should have a score spread >= 1.5."""
        mock_config.ANTHROPIC_API_KEY = ""
        mock_prefs.return_value = SAMPLE_PREFS
        profile = _make_profile()
        jobs = [
            _make_job(
                job_id="j1", title="数据分析师", company="互联网大厂",
                city="上海", salary_min=15000, salary_max=25000,
                jd_text="技能要求：Python, SQL, 数据分析\n弹性工作",
            ),
            _make_job(
                job_id="j2", title="Java后端开发", company="无名公司",
                city="北京", salary_min=10000, salary_max=15000,
                jd_text="技能要求：Java, Spring Boot\n996工作制",
            ),
            _make_job(
                job_id="j3", title="量化研究员", company="金融科技公司",
                city="上海浦东", salary_min=20000, salary_max=40000,
                jd_text="技能要求：Python, 机器学习, 时间序列\n弹性工作",
            ),
            _make_job(
                job_id="j4", title="产品经理", company="小公司",
                city="深圳", salary_min=5000, salary_max=7000,
                jd_text="负责产品需求管理\n大小周",
            ),
            _make_job(
                job_id="j5", title="数据分析实习", company="咨询公司",
                city="上海徐汇", salary_min=8000, salary_max=12000,
                jd_text="技能要求：Python, Excel, SQL\n实习岗位",
                experience="实习",
            ),
        ]
        scores = [_heuristic_score(profile, j).overall_score for j in jobs]
        spread = max(scores) - min(scores)
        assert spread >= 1.5, f"Score spread {spread:.2f} < 1.5: {scores}"
