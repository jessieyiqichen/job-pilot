"""
AI matching scorer — evaluate how well a job matches a resume profile.

Calls Claude API to produce a multi-dimensional score (1-10) with explanations.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from jobpilot import config
from jobpilot.models import Job, JobScore, Profile, now_iso

logger = logging.getLogger(__name__)

SCORING_PROMPT = """\
你是一个专业的求职顾问。请根据以下候选人简历和职位描述，进行全面的匹配评估。

## 候选人画像
{profile_json}

## 职位信息
- 职位：{job_title}
- 公司：{company}
- 城市：{city}
- 薪资范围：{salary_min}-{salary_max} 元/月
- 经验要求：{experience}
- 学历要求：{education}

## 职位描述
{jd_text}

## 候选人偏好
{preferences_text}

## 评分要求
请从以下维度打分（1-10分），并给出分析：

1. **skill_match**（技能匹配度）：候选人的技术栈与JD要求的匹配程度
2. **experience_match**（经验匹配度）：工作年限、项目经验与岗位要求的匹配程度
3. **salary_match**（薪资匹配度）：候选人预期/当前薪资水平与岗位薪资的匹配程度（如信息不足默认7分）
4. **overall_score**（综合评分）：综合考虑以上因素及候选人偏好的总体匹配度

## 输出格式（严格 JSON）
```json
{{
  "overall_score": 8.0,
  "skill_match": 8.5,
  "experience_match": 7.0,
  "salary_match": 7.5,
  "highlights": ["匹配亮点1", "匹配亮点2"],
  "concerns": ["不匹配点1", "不匹配点2"],
  "suggestion": "一段话的投递建议：要不要投、简历上应该突出什么、面试准备建议"
}}
```

只输出 JSON，不要其他文字。"""


def score_job(profile: Profile, job: Job) -> JobScore:
    """Score how well a job matches a profile using AI.

    Args:
        profile: The candidate's profile
        job: The job to evaluate

    Returns:
        JobScore with all dimensions filled
    """
    profile_json = json.dumps(profile.structured, ensure_ascii=False, indent=2)
    preferences = _load_preferences()
    if preferences:
        pref_lines = []
        for k, v in preferences.items():
            if isinstance(v, list):
                pref_lines.append(f"- {k}: {', '.join(str(x) for x in v)}")
            else:
                pref_lines.append(f"- {k}: {v}")
        preferences_text = "\n".join(pref_lines)
    else:
        preferences_text = "（无特殊偏好）"

    prompt = SCORING_PROMPT.format(
        profile_json=profile_json,
        preferences_text=preferences_text,
        job_title=job.title,
        company=job.company,
        city=job.city,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        experience=job.experience,
        education=job.education,
        jd_text=job.jd_text,
    )

    if not config.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set. Using heuristic scoring.")
        return _heuristic_score(profile, job)

    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic package is required. Install with: pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    result = _extract_json(response_text)

    return JobScore(
        job_id=job.job_id,
        profile_id=profile.id or 1,
        overall_score=float(result.get("overall_score", 5.0)),
        skill_match=float(result.get("skill_match", 5.0)),
        experience_match=float(result.get("experience_match", 5.0)),
        salary_match=float(result.get("salary_match", 5.0)),
        highlights=result.get("highlights", []),
        concerns=result.get("concerns", []),
        suggestion=result.get("suggestion", ""),
        scored_at=now_iso(),
    )


def score_jobs(profile: Profile, jobs: list[Job]) -> list[JobScore]:
    """Score multiple jobs against a profile.

    Returns:
        List of JobScores sorted by overall_score descending
    """
    scores = []
    for i, job in enumerate(jobs, 1):
        logger.info("Scoring job %d/%d: %s @ %s", i, len(jobs), job.title, job.company)
        try:
            score = score_job(profile, job)
            scores.append(score)
        except Exception as e:
            logger.error("Failed to score job %s: %s", job.job_id, e)
            continue
    return sorted(scores, key=lambda s: s.overall_score, reverse=True)


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from AI response text."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code block
    if "```" in text:
        lines = text.splitlines()
        json_lines = []
        inside = False
        for line in lines:
            if line.strip().startswith("```") and not inside:
                inside = True
                continue
            elif line.strip().startswith("```") and inside:
                break
            elif inside:
                json_lines.append(line)
        try:
            return json.loads("\n".join(json_lines))
        except json.JSONDecodeError:
            pass
    logger.error("Could not parse scoring response as JSON")
    return {}


# ---------------------------------------------------------------------------
# Skill name aliases for Chinese/English matching
# ---------------------------------------------------------------------------
_SKILL_ALIASES: dict[str, list[str]] = {
    "python": ["python3", "python2"],
    "机器学习": ["machine learning", "ml"],
    "深度学习": ["deep learning", "dl"],
    "自然语言处理": ["nlp", "natural language processing"],
    "数据分析": ["data analysis"],
    "数据可视化": ["data visualization"],
    "计算机视觉": ["computer vision", "cv"],
    "sql": ["mysql", "postgresql", "sqlite"],
    "javascript": ["js", "typescript", "ts"],
    "react": ["reactjs", "react.js"],
    "vue": ["vuejs", "vue.js"],
    "java": ["jdk"],
    "c++": ["cpp"],
    "数据挖掘": ["data mining"],
    "因果推断": ["causal inference"],
    "计量经济": ["econometrics", "econometric"],
    "时间序列": ["time series"],
    "ab测试": ["a/b testing", "a/b test", "ab testing"],
    "网页爬虫": ["web scraping", "爬虫", "crawler"],
    "excel": ["spreadsheet"],
    "r": ["r语言", "rstudio"],
    "stata": [],
    "matlab": [],
    "xgboost": [],
    "随机森林": ["random forest"],
    "lstm": [],
}


def _normalize_skill(skill: str) -> str:
    """Normalize a skill name for comparison."""
    s = skill.lower().strip()
    # Remove proficiency markers like "(Expert)", "(Proficient)"
    s = re.sub(r"\s*\(.*?\)\s*$", "", s)
    return s.strip()


def _extract_profile_skills(profile: Profile) -> list[str]:
    """Extract all skill keywords from profile (skills, experience, projects)."""
    result: list[str] = []
    s = profile.structured

    # From skills dict
    skills = s.get("skills", {})
    if isinstance(skills, dict):
        for v in skills.values():
            if isinstance(v, list):
                result.extend([_normalize_skill(sk) for sk in v])
    elif isinstance(skills, list):
        for item in skills:
            if isinstance(item, str):
                result.append(_normalize_skill(item))

    # From experience highlights
    for exp in s.get("experience", []):
        if isinstance(exp, dict):
            for h in exp.get("highlights", []):
                result.append(h.lower())

    # From projects tech_stack
    for proj in s.get("projects", []):
        if isinstance(proj, dict):
            for tech in proj.get("tech_stack", []):
                result.append(_normalize_skill(tech))

    return result


def _extract_jd_skills(jd_text: str) -> list[str]:
    """Extract skill keywords from JD text.

    Handles Boss format like "技能要求：Python, SQL, ..." and general keyword extraction.
    """
    jd_lower = jd_text.lower()
    skills: list[str] = []

    # Boss-style skill tags: "技能要求：xxx, yyy" or "技能标签：xxx"
    for pattern in [
        r"技能(?:要求|标签)[：:]\s*(.+?)(?:\n|$)",
        r"技术(?:要求|栈)[：:]\s*(.+?)(?:\n|$)",
        r"岗位要求[：:]\s*(.+?)(?:\n|$)",
    ]:
        m = re.search(pattern, jd_lower)
        if m:
            tags = re.split(r"[,，、/|]", m.group(1))
            skills.extend([t.strip() for t in tags if t.strip()])

    # Also search for well-known skill names in the full JD
    known_skills = [
        "python", "java", "c++", "javascript", "typescript", "go", "rust",
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "react", "vue", "angular", "node", "django", "flask", "spring",
        "docker", "kubernetes", "aws", "gcp", "azure",
        "机器学习", "深度学习", "自然语言处理", "计算机视觉",
        "数据分析", "数据挖掘", "数据可视化",
        "hadoop", "spark", "flink", "kafka", "hive",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "excel", "tableau", "power bi", "spss", "stata", "matlab", "r",
        "git", "linux", "shell",
        "nlp", "machine learning", "deep learning",
        "causal inference", "econometric", "time series",
        "a/b testing", "web scraping", "xgboost", "random forest", "lstm",
    ]
    for sk in known_skills:
        if sk in jd_lower:
            skills.append(sk)

    return list(set(skills))


def _skill_matches(profile_skill: str, jd_skill: str) -> bool:
    """Check if a profile skill matches a JD skill, considering aliases."""
    ps = _normalize_skill(profile_skill)
    js = jd_skill.lower().strip()

    # Direct substring match
    if ps in js or js in ps:
        return True

    # Check alias table
    for canonical, aliases in _SKILL_ALIASES.items():
        all_forms = [canonical] + aliases
        ps_match = any(ps == f or f in ps or ps in f for f in all_forms)
        js_match = any(js == f or f in js or js in f for f in all_forms)
        if ps_match and js_match:
            return True

    return False


def _score_skills(profile: Profile, job: Job) -> tuple[float, list[str], list[str]]:
    """Score skill matching (weight: 40%).

    Returns (score_0_to_10, matched_list, missing_list).
    """
    profile_skills = _extract_profile_skills(profile)
    jd_skills = _extract_jd_skills(job.jd_text)

    if not jd_skills:
        # No skills extracted from JD — fall back to simple keyword match
        jd_lower = job.jd_text.lower()
        matched = [s for s in profile_skills if s in jd_lower and len(s) > 1]
        matched = list(dict.fromkeys(matched))[:10]  # dedupe, cap at 10
        return (min(10.0, len(matched) * 1.5) if profile_skills else 5.0, matched, [])

    matched: list[str] = []
    missing: list[str] = []

    for js in jd_skills:
        found = False
        for ps in profile_skills:
            if _skill_matches(ps, js):
                matched.append(js)
                found = True
                break
        if not found:
            missing.append(js)

    matched = list(dict.fromkeys(matched))
    missing = list(dict.fromkeys(missing))

    total = max(len(jd_skills), 1)
    raw = len(matched) / total * 10.0
    score = min(10.0, round(raw, 1))

    return (score, matched, missing)


def _parse_exp_years_required(experience: str) -> tuple[float, float]:
    """Parse experience requirement string into (min_years, max_years).

    Examples: "1-3年" → (1, 3), "3-5年经验" → (3, 5), "实习" → (0, 0),
              "应届生" → (0, 0), "经验不限" → (0, 99)
    """
    if not experience:
        return (0, 99)

    exp_lower = experience.lower().strip()

    if any(kw in exp_lower for kw in ["实习", "intern"]):
        return (0, 0)
    if any(kw in exp_lower for kw in ["应届", "毕业生", "fresh", "graduate"]):
        return (0, 1)
    if any(kw in exp_lower for kw in ["不限", "不要求", "无要求"]):
        return (0, 99)

    m = re.search(r"(\d+)\s*[-–~到]\s*(\d+)", exp_lower)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    m = re.search(r"(\d+)\s*年", exp_lower)
    if m:
        n = float(m.group(1))
        return (n, n + 2)

    return (0, 99)


def _score_experience(profile: Profile, job: Job) -> tuple[float, str]:
    """Score experience matching (weight: 25%).

    Returns (score_0_to_10, explanation_str).
    """
    exp_years = profile.structured.get("years_of_experience", 0) or 0
    min_req, max_req = _parse_exp_years_required(job.experience)

    # Intern/fresh graduate positions
    if max_req <= 1:
        if exp_years <= 2:
            return (9.0, "应届/实习岗位，经验匹配")
        return (7.0, f"候选人有{exp_years}年经验，岗位为实习/应届")

    # "不限" experience
    if max_req >= 99:
        return (8.0, "经验要求不限")

    if min_req <= exp_years <= max_req:
        return (9.0, f"经验{exp_years}年，完全匹配要求{job.experience}")
    elif exp_years > max_req:
        return (7.0, f"经验{exp_years}年，超出要求{job.experience}")
    else:
        ratio = exp_years / max(min_req, 1)
        score = max(3.0, round(ratio * 8.0, 1))
        return (min(score, 8.0), f"经验{exp_years}年，低于要求{job.experience}")


def _parse_education_level(text: str) -> int:
    """Convert education text to a numeric level for comparison.

    Returns: 0=unknown, 1=大专, 2=本科, 3=硕士, 4=博士
    """
    if not text:
        return 0
    t = text.lower()
    if any(kw in t for kw in ["博士", "phd", "doctorate"]):
        return 4
    if any(kw in t for kw in ["硕士", "研究生", "master"]):
        return 3
    if any(kw in t for kw in ["本科", "学士", "bachelor", "undergraduate"]):
        return 2
    if any(kw in t for kw in ["大专", "专科", "college", "associate"]):
        return 1
    return 0


def _score_education(profile: Profile, job: Job) -> tuple[float, str]:
    """Score education matching (weight: 15%).

    Returns (score_0_to_10, explanation_str).
    """
    edu_list = profile.structured.get("education", [])
    if not edu_list:
        return (5.0, "简历中未找到学历信息")

    # Get highest education from profile
    profile_level = 0
    profile_school = ""
    for edu in edu_list:
        if isinstance(edu, dict):
            degree = edu.get("degree", "")
            level = _parse_education_level(degree)
            if level > profile_level:
                profile_level = level
                profile_school = edu.get("school", "")

    jd_edu = job.education or ""
    req_level = _parse_education_level(jd_edu)

    # 985/211 bonus check
    is_elite = any(kw in jd_edu for kw in ["985", "211", "双一流", "top"])

    if req_level == 0:
        return (8.0, "学历要求不限")

    if profile_level >= req_level:
        score = 9.0
        explanation = f"学历匹配（{profile_school}）"
        if is_elite:
            score = 7.5
            explanation += "，但岗位要求985/211"
        return (score, explanation)
    else:
        gap = req_level - profile_level
        score = max(3.0, 7.0 - gap * 2.0)
        return (round(score, 1), f"学历低于要求（要求{jd_edu}）")


def _score_title_relevance(profile: Profile, job: Job) -> tuple[float, str]:
    """Score job title relevance to profile (weight: 20%).

    Checks if job title keywords appear in profile experience/projects.
    Returns (score_0_to_10, explanation_str).
    """
    title_lower = job.title.lower()
    s = profile.structured

    # Build a text corpus from profile experience + projects
    corpus_parts: list[str] = []
    for exp in s.get("experience", []):
        if isinstance(exp, dict):
            corpus_parts.append(exp.get("title", "").lower())
            corpus_parts.append(exp.get("description", "").lower())
            for h in exp.get("highlights", []):
                corpus_parts.append(h.lower())
    for proj in s.get("projects", []):
        if isinstance(proj, dict):
            corpus_parts.append(proj.get("name", "").lower())
            corpus_parts.append(proj.get("description", "").lower())
            for tech in proj.get("tech_stack", []):
                corpus_parts.append(tech.lower())

    # Also include skills
    skills = s.get("skills", {})
    if isinstance(skills, dict):
        for v in skills.values():
            if isinstance(v, list):
                for sk in v:
                    corpus_parts.append(sk.lower())

    corpus = " ".join(corpus_parts)

    # Define title keyword mapping
    title_keywords: dict[str, list[str]] = {
        "数据分析": ["数据分析", "data analysis", "sql", "excel", "tableau", "数据"],
        "数据": ["数据", "data", "sql", "分析", "analysis"],
        "产品": ["产品", "product", "需求", "用户"],
        "后端": ["后端", "backend", "java", "python", "go", "api"],
        "前端": ["前端", "frontend", "react", "vue", "javascript"],
        "算法": ["算法", "algorithm", "机器学习", "machine learning", "深度学习"],
        "运营": ["运营", "operation", "用户", "活动"],
        "测试": ["测试", "test", "qa", "quality"],
        "研究": ["研究", "research", "论文", "paper"],
        "analyst": ["data", "analysis", "sql", "excel", "analytics", "python"],
        "engineer": ["engineering", "develop", "code", "build", "system"],
        "scientist": ["research", "model", "machine learning", "statistics"],
        "intern": ["intern", "实习"],
    }

    matched_keywords: list[str] = []
    checked = 0

    for key, related in title_keywords.items():
        if key in title_lower:
            checked += len(related)
            for kw in related:
                if kw in corpus:
                    matched_keywords.append(kw)

    # Also do direct title word check
    title_words = re.split(r"[\s/\-_]+", title_lower)
    for word in title_words:
        if len(word) > 1 and word in corpus:
            matched_keywords.append(word)

    matched_keywords = list(dict.fromkeys(matched_keywords))

    if not matched_keywords and checked == 0:
        return (6.0, "无法判断岗位与简历的相关度")

    if matched_keywords:
        ratio = len(matched_keywords) / max(checked, len(title_words), 1)
        score = min(10.0, round(4.0 + ratio * 6.0, 1))
        return (score, f"岗位关键词匹配: {', '.join(matched_keywords[:5])}")
    else:
        return (4.0, f"岗位'{job.title}'与简历经历关联度较低")


def _load_preferences() -> dict:
    """Load preferences from resume_config.yaml if present."""
    cfg_path = Path(config.DATA_DIR) / "resume_config.yaml"
    if not cfg_path.exists():
        return {}
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("preferences", {})


def _score_preference(job: Job, preferences: dict) -> tuple[float, list[str], list[str]]:
    """Score job against user preferences.

    Returns (score_0_to_10, positives, negatives).

    Dimensions:
    - Industry match (25%): JD/company contains preferred_industries
    - City match (20%): precise district > same city > different city
    - Career track (25%): title alignment with career_track
    - Deal-breaker (20%): JD contains deal_breakers keywords
    - Salary floor (10%): salary_min >= min_salary
    """
    positives: list[str] = []
    negatives: list[str] = []

    jd_lower = (job.jd_text or "").lower()
    company_lower = (job.company or "").lower()
    title_lower = (job.title or "").lower()
    city_lower = (job.city or "").lower()
    combined_text = f"{jd_lower} {company_lower} {title_lower}"

    # 1. Industry match (25%)
    preferred_industries = preferences.get("preferred_industries", [])
    if preferred_industries:
        matched_ind = [ind for ind in preferred_industries if ind.lower() in combined_text]
        if matched_ind:
            industry_score = 10.0
            positives.append(f"行业匹配: {', '.join(matched_ind)}")
        else:
            industry_score = 3.0
    else:
        industry_score = 6.0

    # 2. City match (20%)
    preferred_cities = preferences.get("preferred_cities", [])
    if preferred_cities:
        exact_match = any(c.lower() == city_lower for c in preferred_cities)
        partial_match = any(c.lower() in city_lower or city_lower in c.lower()
                           for c in preferred_cities)
        if exact_match:
            city_score = 10.0
            positives.append(f"城市精确匹配: {job.city}")
        elif partial_match:
            city_score = 7.0
            positives.append(f"同城: {job.city}")
        else:
            city_score = 2.0
            negatives.append(f"城市不匹配: {job.city}")
    else:
        city_score = 6.0

    # 3. Career track (25%)
    career_tracks = preferences.get("career_track", [])
    if career_tracks:
        exact_track = any(ct.lower() in title_lower for ct in career_tracks)
        related_track = any(ct.lower() in combined_text for ct in career_tracks)
        if exact_track:
            track_score = 10.0
            positives.append(f"职业路径匹配: {job.title}")
        elif related_track:
            track_score = 6.0
        else:
            track_score = 3.0
            negatives.append(f"岗位'{job.title}'偏离目标职业路径")
    else:
        track_score = 6.0

    # 4. Deal-breaker (20%)
    deal_breakers = preferences.get("deal_breakers", [])
    if deal_breakers:
        found_db = [db for db in deal_breakers if db.lower() in jd_lower]
        if found_db:
            deal_score = 0.0
            negatives.append(f"触发 deal-breaker: {', '.join(found_db)}")
        else:
            deal_score = 8.0
    else:
        deal_score = 6.0

    # 5. Salary floor (10%)
    min_salary = preferences.get("min_salary", 0)
    if min_salary and min_salary > 0:
        if job.salary_min >= min_salary:
            salary_pref_score = 9.0
        elif job.salary_max and job.salary_max >= min_salary:
            salary_pref_score = 6.0
        elif job.salary_max and job.salary_max < min_salary:
            salary_pref_score = 2.0
            negatives.append(f"薪资低于底线: {job.salary_max} < {min_salary}")
        else:
            salary_pref_score = 5.0
    else:
        salary_pref_score = 6.0

    # Weighted sum
    overall = round(
        industry_score * 0.25
        + city_score * 0.20
        + track_score * 0.25
        + deal_score * 0.20
        + salary_pref_score * 0.10,
        2,
    )
    return (overall, positives, negatives)


def _heuristic_score(profile: Profile, job: Job) -> JobScore:
    """Enhanced heuristic scoring when AI is not available.

    Ability dimensions and weights:
    - Skill match: 40%
    - Experience match: 25%
    - Education match: 15%
    - Title relevance: 20%

    When preferences are configured:
    - overall = ability * 0.4 + preference * 0.6
    Otherwise:
    - overall = ability
    """
    # 1. Skill matching (40%)
    skill_score, matched_skills, missing_skills = _score_skills(profile, job)

    # 2. Experience matching (25%)
    exp_score, exp_explanation = _score_experience(profile, job)

    # 3. Education matching (15%)
    edu_score, edu_explanation = _score_education(profile, job)

    # 4. Title relevance (20%)
    title_score, title_explanation = _score_title_relevance(profile, job)

    # Use 2-decimal precision for sub-scores
    skill_score = round(skill_score, 2)
    exp_score = round(exp_score, 2)
    edu_score = round(edu_score, 2)
    title_score = round(title_score, 2)

    # Ability composite
    ability = round(
        skill_score * 0.40
        + exp_score * 0.25
        + edu_score * 0.15
        + title_score * 0.20,
        2,
    )

    # Preference scoring
    preferences = _load_preferences()
    pref_positives: list[str] = []
    pref_negatives: list[str] = []
    if preferences:
        pref_score, pref_positives, pref_negatives = _score_preference(job, preferences)
        overall = round(ability * 0.4 + pref_score * 0.6, 2)
    else:
        overall = ability

    overall = min(10.0, max(1.0, overall))

    # Build highlights
    highlights: list[str] = []
    if matched_skills:
        highlights.append(f"匹配技能: {', '.join(matched_skills[:6])}")
    if exp_score >= 8.0:
        highlights.append(exp_explanation)
    if edu_score >= 8.0:
        highlights.append(edu_explanation)
    if title_score >= 7.0:
        highlights.append(title_explanation)
    highlights.extend(pref_positives)

    # Build concerns
    concerns: list[str] = []
    if missing_skills:
        concerns.append(f"JD要求但简历未体现: {', '.join(missing_skills[:5])}")
    if exp_score < 6.0:
        concerns.append(exp_explanation)
    if edu_score < 6.0:
        concerns.append(edu_explanation)
    if title_score < 5.0:
        concerns.append(title_explanation)
    concerns.extend(pref_negatives)

    # Build suggestion
    if overall >= 7.0:
        suggestion = (
            f"综合匹配度较高（{overall}/10），建议投递。"
            f"简历中可突出: {', '.join(matched_skills[:3]) if matched_skills else '相关经历'}。"
        )
    elif overall >= 5.0:
        suggestion = (
            f"综合匹配度中等（{overall}/10），可考虑投递。"
            f"{'建议补充: ' + ', '.join(missing_skills[:3]) + '。' if missing_skills else ''}"
        )
    else:
        suggestion = (
            f"综合匹配度较低（{overall}/10），建议优先投递更匹配的岗位。"
        )

    if not config.ANTHROPIC_API_KEY:
        suggestion += "（启发式评分，配置 API KEY 可获得更精准的AI评估）"

    return JobScore(
        job_id=job.job_id,
        profile_id=profile.id or 1,
        overall_score=overall,
        skill_match=skill_score,
        experience_match=exp_score,
        salary_match=7.0,
        highlights=highlights,
        concerns=concerns,
        suggestion=suggestion,
        scored_at=now_iso(),
    )
