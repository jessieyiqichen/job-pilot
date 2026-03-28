"""
Web search adapter using Anthropic API with web_search tool.

Fallback adapter: when boss-cli returns too few results, this adapter
searches the internet for real job postings on Chinese recruitment sites.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime

import anthropic

from jobpilot import config
from jobpilot.adapters.base import BaseAdapter, SearchFilters
from jobpilot.models import Job

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
你是一个招聘信息搜索助手。请搜索以下岗位的真实招聘信息：

搜索关键词：{query}
城市：{city}

请在中国主流招聘网站（Boss直聘、拉勾、猎聘、智联招聘、公司官网等）搜索真实在招岗位。

要求：
1. 只返回真实存在的、当前仍在招聘的岗位，绝对不要捏造
2. 优先搜索近期（{year}年）发布的岗位，跳过明显过期的招聘信息
3. 如果 JD 中写了截止日期且已过期，不要返回该岗位
4. 每个岗位尽量包含完整信息
5. 以 JSON 数组格式返回，每条包含以下字段：
   - company: 公司名称
   - title: 岗位名称
   - salary: 薪资范围（如 "15-25K"），不确定则留空字符串
   - city: 工作城市
   - experience: 经验要求（如 "3-5年"），不确定则留空字符串
   - education: 学历要求（如 "本科"），不确定则留空字符串
   - jd_text: 岗位描述/职责要求（尽量详细）
   - source_url: 信息来源 URL

请直接返回 JSON 数组，不要添加 markdown 代码块标记。
"""


def _generate_job_id(company: str, title: str) -> str:
    """Generate a deterministic job ID from company + title."""
    raw = f"{company}:{title}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _parse_salary(salary_str: str) -> tuple[int, int]:
    """Parse salary string like '15-25K' into (min, max) in yuan/month."""
    if not salary_str:
        return 0, 0
    m = re.match(r"(\d+)[_\-~](\d+)\s*[kK]", salary_str)
    if m:
        return int(m.group(1)) * 1000, int(m.group(2)) * 1000
    m = re.match(r"(\d+)[_\-~](\d+)", salary_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def _extract_json_from_text(text: str) -> list[dict]:
    """Extract a JSON array from Claude's response text.

    Handles both raw JSON and markdown code-block wrapped JSON.
    """
    # Try direct parse first
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1).strip())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Try finding a JSON array in the text
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return []


class WebSearchAdapter(BaseAdapter):
    """Adapter that uses Anthropic API with web_search tool to find jobs."""

    @property
    def platform_name(self) -> str:
        return "websearch"

    def search(self, query: str, filters: SearchFilters | None = None) -> list[Job]:
        """Search for jobs using Anthropic API with web_search tool."""
        if not config.ANTHROPIC_API_KEY:
            logger.warning("No ANTHROPIC_API_KEY set, web search skipped")
            return []

        filters = filters or SearchFilters()
        city = filters.city or config.DEFAULT_CITY

        # Auto-append current year to reduce stale postings
        year = str(datetime.now().year)
        search_query = query if year in query else f"{query} {year}"

        prompt = EXTRACTION_PROMPT.format(query=search_query, city=city, year=year)

        try:
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=4096,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                }],
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            logger.exception("Anthropic API call failed for web search")
            return []

        # Extract text from response content blocks
        text_parts = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)

        full_text = "\n".join(text_parts)
        if not full_text.strip():
            logger.warning("Web search returned empty response")
            return []

        raw_jobs = _extract_json_from_text(full_text)
        if not raw_jobs:
            logger.warning("Could not extract job JSON from web search response")
            return []

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        jobs: list[Job] = []
        for item in raw_jobs:
            company = item.get("company", "").strip()
            title = item.get("title", "").strip()
            if not company or not title:
                continue

            sal_min, sal_max = _parse_salary(item.get("salary", ""))
            source_url = item.get("source_url", "")

            raw_data = dict(item)
            if source_url:
                raw_data["source_url"] = source_url

            jobs.append(Job(
                platform="websearch",
                job_id=_generate_job_id(company, title),
                title=title,
                company=company,
                salary_min=sal_min,
                salary_max=sal_max,
                city=item.get("city", city),
                experience=item.get("experience", ""),
                education=item.get("education", ""),
                jd_text=item.get("jd_text", ""),
                raw_data=raw_data,
                discovered_at=now,
                status="new",
            ))

        return jobs

    def get_job_detail(self, job_id: str) -> None:
        """Web search jobs already have full JD from initial search."""
        return None
