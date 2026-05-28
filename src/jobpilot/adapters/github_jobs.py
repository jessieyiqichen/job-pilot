"""
GitHub job search adapter.

Many startups — especially AI/open-source ones — post hiring info as GitHub
issues (e.g. rebase-network/who-is-hiring, company-owned hiring repos, founding-
engineer openings). This adapter searches them via the **official GitHub Search
API** (through the authenticated `gh` CLI), so it is a clean API call — not a
scraper — fitting JobPilot's no-scraping stance.

Flow: `gh search issues` → AI extracts structured jobs from issue title+body.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime

from jobpilot import config
from jobpilot.adapters.base import BaseAdapter, SearchFilters
from jobpilot.adapters.xhs import _generate_xhs_job_id, _parse_salary
from jobpilot.models import Job

logger = logging.getLogger(__name__)

JOB_EXTRACTION_PROMPT = """\
以下是从 GitHub issues 搜到的帖子（很多创业公司在 GitHub 发招聘）。

请完成：
1. 识别哪些是招聘帖（含具体岗位/公司招聘信息）
2. 跳过非招聘帖（如纯讨论、bug、求职经验）
3. 从每个招聘帖提取结构化字段

## 搜索关键词
{query}

## 帖子列表
{issues_text}

## 输出格式（严格 JSON 数组，无其他文字）
[
  {{
    "company": "公司名称",
    "title": "岗位名称",
    "salary": "薪资（如 15-25K），不确定留空",
    "city": "城市",
    "experience": "经验要求",
    "education": "学历要求",
    "jd_text": "岗位描述与要求（保留原文细节，含联系方式）",
    "source_url": "该 issue 的链接"
  }}
]

规则：
- company 和 title 必填，缺失则跳过该条
- source_url 用帖子自带的 url
- 过滤掉纯技术岗（后端/前端/全栈/算法/嵌入式/SRE/DevOps）和硬件岗，只保留产品/运营/分析/研究/商务/战略/市场方向
- 一个帖子含多个岗位则拆成多条
"""


# Tokens that over-narrow a GitHub issue search (AND semantics) — strip them and
# let downstream scoring (job_type/city preferences) do the filtering instead.
_NARROWING_TOKENS = {"实习", "全职", "兼职", "intern", "internship"}

# Curated "mega-thread" hiring repos: one recurring issue whose COMMENTS are the
# actual postings (generic issue search can't see comment bodies). (repo, search_term).
DEFAULT_MEGA_THREADS: tuple[tuple[str, str], ...] = (
    ("ruanyf/weekly", "谁在招人"),
)
# Cap comments pulled per thread to bound prompt size / token cost.
MAX_THREAD_COMMENTS = 30


def broaden_query(query: str) -> str:
    """Drop job-type tokens so the GitHub AND-search isn't over-constrained."""
    terms = [t for t in query.split() if t.lower() not in _NARROWING_TOKENS]
    return " ".join(terms) or query


def call_gh_search(query: str, limit: int = 30, timeout: int = 60) -> list[dict]:
    """Search GitHub issues via the gh CLI. Returns a list of issue dicts.

    Raises:
        FileNotFoundError: gh not installed.
        RuntimeError: gh command failed.
    """
    search_q = f"{query} 招聘"
    cmd = [
        "gh", "search", "issues", search_q,
        "--sort", "updated", "--limit", str(limit),
        "--json", "title,body,url,repository,updatedAt",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise FileNotFoundError("gh CLI 未安装。安装: https://cli.github.com/") from e

    if result.returncode != 0:
        raise RuntimeError(f"gh search 失败: {result.stderr.strip()}")

    try:
        return json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        logger.warning("gh search returned non-JSON output")
        return []


def _latest_thread_number(repo: str, term: str, timeout: int = 60) -> int | None:
    """Find the most recent issue number matching `term` in `repo` (e.g. 谁在招人)."""
    cmd = [
        "gh", "search", "issues", term, "--repo", repo,
        "--match", "title",  # match the monthly thread title, not issues merely mentioning it
        "--sort", "created", "--limit", "1", "--json", "number",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        data = json.loads(result.stdout)
        return data[0]["number"] if data else None
    except (json.JSONDecodeError, KeyError, IndexError):
        return None


def call_gh_issue_comments(
    repo: str, number: int, limit: int = MAX_THREAD_COMMENTS, timeout: int = 60
) -> list[str]:
    """Fetch comment bodies of an issue via the GitHub API (gh api). One page (<=100)."""
    cmd = ["gh", "api", f"repos/{repo}/issues/{number}/comments?per_page=100"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        comments = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    bodies = [c.get("body", "") for c in comments if isinstance(c, dict) and c.get("body")]
    return bodies[:limit]


def _gather_thread_posts(threads: tuple[tuple[str, str], ...]) -> list[dict]:
    """Pull the latest mega-thread's comments as unified post dicts."""
    posts: list[dict] = []
    for repo, term in threads:
        try:
            number = _latest_thread_number(repo, term)
            if not number:
                continue
            url = f"https://github.com/{repo}/issues/{number}"
            for body in call_gh_issue_comments(repo, number):
                posts.append(
                    {"title": "", "body": body, "url": url,
                     "repository": {"nameWithOwner": repo}}
                )
        except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired) as e:
            logger.warning("mega-thread %s failed: %s", repo, e)
    return posts


def _format_issues(issues: list[dict]) -> str:
    parts: list[str] = []
    for i, it in enumerate(issues, 1):
        repo = (it.get("repository") or {}).get("nameWithOwner", "")
        body = (it.get("body") or "")[:2000]  # cap to control prompt size
        parts.append(
            f"### 帖子 {i}\n仓库: {repo}\n标题: {it.get('title', '')}\n"
            f"链接: {it.get('url', '')}\n正文:\n{body}"
        )
    return "\n\n".join(parts)


def _extract_jobs_via_ai(issues: list[dict], query: str) -> list[dict]:
    if not config.ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY, cannot extract jobs from GitHub issues")
        return []

    prompt = JOB_EXTRACTION_PROMPT.format(query=query, issues_text=_format_issues(issues))
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception:
        logger.exception("Anthropic API call failed for GitHub job extraction")
        return []

    return _extract_json_array(response.content[0].text.strip())


def _extract_json_array(text: str) -> list[dict]:
    import re

    text = text.strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        pass
    for pat in (r"```(?:json)?\s*\n?(.*?)\n?```", r"(\[.*\])"):
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue
    return []


def _parse_github_jobs(items: list[dict]) -> list[Job]:
    jobs: list[Job] = []
    for item in items:
        company = str(item.get("company", "")).strip()
        title = str(item.get("title", "")).strip()
        if not company or not title:
            continue
        source_url = str(item.get("source_url", "") or item.get("url", "")).strip()
        sal_min, sal_max = _parse_salary(str(item.get("salary", "")))
        jobs.append(
            Job(
                platform="github",
                job_id=_generate_xhs_job_id(company, title, source_url),
                title=title,
                company=company,
                salary_min=sal_min,
                salary_max=sal_max,
                city=str(item.get("city", "")).strip(),
                experience=str(item.get("experience", "")).strip(),
                education=str(item.get("education", "")).strip(),
                jd_text=str(item.get("jd_text", "")).strip(),
                raw_data=dict(item),
                discovered_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status="new",
            )
        )
    return jobs


class GitHubAdapter(BaseAdapter):
    """Search GitHub issues for startup/AI hiring posts via the official API."""

    @property
    def platform_name(self) -> str:
        return "github"

    def search(self, query: str, filters: SearchFilters | None = None) -> list[Job]:
        # GitHub issue search is AND-based; drop job-type tokens and DON'T append
        # city (hiring posts are often multi-city/remote). Let scoring filter.
        keyword = broaden_query(query)

        logger.info("Searching GitHub issues for: %s", keyword)
        try:
            issues = call_gh_search(keyword, limit=30)
        except FileNotFoundError as e:
            logger.error("gh not available: %s", e)
            return []
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            logger.error("GitHub search failed: %s", e)
            issues = []

        # Mega-thread comments (where the actual postings live, e.g. 谁在招人)
        thread_posts = _gather_thread_posts(DEFAULT_MEGA_THREADS)
        posts = list(issues) + thread_posts

        if not posts:
            logger.warning("GitHub search + threads returned nothing")
            return []

        logger.info(
            "Got %d issues + %d thread comments; extracting via AI",
            len(issues), len(thread_posts),
        )
        job_dicts = _extract_jobs_via_ai(posts, query)
        return _parse_github_jobs(job_dicts)

    def get_job_detail(self, job_id: str) -> Job | None:
        return None
