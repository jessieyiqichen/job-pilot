"""
XHS (小红书) search adapter via rednote-mcp.

Searches XHS for job posts using rednote-mcp's search_notes tool,
then uses Anthropic API to identify and extract structured job info.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from jobpilot import config
from jobpilot.adapters.base import BaseAdapter, SearchFilters
from jobpilot.adapters.xhs import parse_xhs_jobs
from jobpilot.models import Job

logger = logging.getLogger(__name__)

JOB_EXTRACTION_PROMPT = """\
你是一个招聘信息识别专家。以下是从小红书搜索到的笔记列表。

请完成以下任务：
1. 识别哪些笔记是招聘/求职相关的帖子（包含岗位信息、公司招聘等）
2. 跳过不是招聘帖的笔记（如求职经验分享、面试技巧等不含具体岗位的内容）
3. 从每个招聘帖中提取结构化字段

## 搜索关键词
{query}

## 笔记列表
{notes_text}

## 输出格式（严格 JSON 数组）
对每个识别出的招聘帖，输出：
```json
[
  {{
    "company": "公司名称",
    "title": "岗位名称",
    "salary": "薪资范围（如 15-25K），不确定则留空",
    "city": "工作城市",
    "experience": "经验要求",
    "education": "学历要求",
    "jd_text": "完整的岗位描述和要求（尽量保留原文细节）",
    "source_url": "笔记链接"
  }}
]
```

规则：
- 只返回确实包含岗位信息的笔记，不要猜测
- company 和 title 是必填字段，缺失则跳过该条
- jd_text 尽量保留原文中的职责描述和要求细节
- 如果一条笔记包含多个岗位，拆成多条
- 过滤掉纯技术岗（后端/前端/全栈/算法工程师/嵌入式/SRE/DevOps）和硬件岗（芯片/FPGA/驱动开发），只保留产品/运营/分析/研究/商务/战略/市场方向的岗位

只输出 JSON 数组，不要其他文字。"""


def _build_mcp_script(mcp_dir: str, keywords: str, limit: int, timeout_ms: int = 120000) -> str:
    """Build the Node.js script to call rednote-mcp search_notes."""
    sdk_base = f"{mcp_dir}/node_modules/@modelcontextprotocol/sdk"
    cli_path = f"{mcp_dir}/dist/cli.js"
    return f"""\
const {{ Client }} = require("{sdk_base}/dist/cjs/client/index.js");
const {{ StdioClientTransport }} = require("{sdk_base}/dist/cjs/client/stdio.js");
(async () => {{
    const transport = new StdioClientTransport({{
        command: "node",
        args: ["{cli_path}", "--stdio"],
    }});
    const client = new Client({{ name: "jobpilot", version: "1.0.0" }});
    await client.connect(transport);
    const result = await client.callTool({{
        name: "search_notes",
        arguments: {{ keywords: {json.dumps(keywords, ensure_ascii=False)}, limit: {limit} }},
    }}, undefined, {{ timeout: {timeout_ms} }});
    for (const item of result.content || []) {{
        if (item.type === "text") process.stdout.write(item.text);
    }}
    await client.close();
}})().catch(e => {{
    process.stderr.write("MCP_ERROR:" + e.message);
    process.exit(1);
}});"""


def call_mcp_search(keywords: str, limit: int = 10, timeout: int = 120) -> str:
    """Call rednote-mcp search_notes and return raw text output.

    Args:
        keywords: Search keywords
        limit: Max notes to return
        timeout: Subprocess timeout in seconds

    Returns:
        Raw text output from search_notes

    Raises:
        FileNotFoundError: rednote-mcp not installed
        RuntimeError: MCP call failed
        subprocess.TimeoutExpired: Search timed out
    """
    mcp_dir = Path(config.REDNOTE_MCP_PATH)
    if not (mcp_dir / "dist" / "cli.js").exists():
        raise FileNotFoundError(
            f"rednote-mcp not found at {mcp_dir}. "
            "Install with: npm install -g rednote-mcp"
        )

    sdk_path = mcp_dir / "node_modules" / "@modelcontextprotocol" / "sdk"
    if not sdk_path.exists():
        raise FileNotFoundError(
            f"MCP SDK not found at {sdk_path}. "
            "Try reinstalling: npm install -g rednote-mcp"
        )

    script = _build_mcp_script(str(mcp_dir), keywords, limit, timeout_ms=timeout * 1000)

    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        err = result.stderr.strip()
        raise RuntimeError(f"rednote-mcp search failed: {err}")

    return result.stdout


def _parse_notes_text(raw: str) -> list[dict]:
    """Parse rednote-mcp search_notes output into note dicts.

    The output format is:
        标题: ...
        作者: ...
        内容: ...
        点赞: N
        评论: N
        链接: https://...
        ---
    """
    notes: list[dict] = []
    current: dict[str, str] = {}

    for line in raw.splitlines():
        line = line.rstrip()
        if line == "---":
            if current:
                notes.append(current)
                current = {}
            continue
        # Handle "---标题: ..." where separator and next title are joined
        if line.startswith("---标题: "):
            if current:
                notes.append(current)
                current = {}
            current["title"] = line[7:].strip()
            continue
        if line.startswith("标题: "):
            current["title"] = line[4:].strip()
        elif line.startswith("作者: "):
            current["author"] = line[4:].strip()
        elif line.startswith("内容: "):
            current["content"] = line[4:].strip()
        elif line.startswith("链接: "):
            current["url"] = line[4:].strip()
        elif line.startswith("点赞: "):
            current["likes"] = line[4:].strip()
        elif line.startswith("评论: "):
            current["comments"] = line[4:].strip()
        elif "content" in current:
            # Continuation of content
            current["content"] += "\n" + line

    if current:
        notes.append(current)

    return notes


def _extract_jobs_via_ai(notes: list[dict], query: str) -> list[dict]:
    """Use Anthropic API to identify job posts and extract structured fields."""
    if not config.ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY, cannot extract jobs from XHS notes")
        return []

    # Format notes for the prompt
    notes_parts: list[str] = []
    for i, note in enumerate(notes, 1):
        parts = [f"### 笔记 {i}"]
        if note.get("title"):
            parts.append(f"标题: {note['title']}")
        if note.get("author"):
            parts.append(f"作者: {note['author']}")
        if note.get("content"):
            parts.append(f"内容:\n{note['content']}")
        if note.get("url"):
            parts.append(f"链接: {note['url']}")
        notes_parts.append("\n".join(parts))

    notes_text = "\n\n".join(notes_parts)
    prompt = JOB_EXTRACTION_PROMPT.format(query=query, notes_text=notes_text)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception:
        logger.exception("Anthropic API call failed for XHS job extraction")
        return []

    text = response.content[0].text.strip()
    return _extract_json_from_text(text)


def _extract_json_from_text(text: str) -> list[dict]:
    """Extract a JSON array from AI response text."""
    import re

    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        pass

    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1).strip())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Handle truncated JSON: find opening '[', try closing incomplete objects
    m = re.search(r"\[", text)
    if m:
        fragment = text[m.start():]
        # Try progressively trimming to find last complete object
        for suffix in ("]", "}]"):
            # Find last complete "}" and close the array
            last_brace = fragment.rfind("}")
            if last_brace > 0:
                candidate = fragment[: last_brace + 1] + "]"
                try:
                    data = json.loads(candidate)
                    if isinstance(data, list):
                        logger.info(
                            "Recovered %d items from truncated JSON", len(data)
                        )
                        return data
                except json.JSONDecodeError:
                    continue

    return []


class XHSSearchAdapter(BaseAdapter):
    """Adapter that searches XHS via rednote-mcp for job posts."""

    @property
    def platform_name(self) -> str:
        return "xhs"

    def search(self, query: str, filters: SearchFilters | None = None) -> list[Job]:
        """Search XHS for job posts.

        1. Call rednote-mcp search_notes to get raw XHS notes
        2. Use Anthropic API to identify job posts and extract structured fields
        3. Convert to Job objects via parse_xhs_jobs
        """
        filters = filters or SearchFilters()
        city = filters.city or ""

        # Build search keywords
        keywords = query
        if city and city not in query:
            keywords = f"{query} {city}"

        logger.info("Searching XHS for: %s", keywords)

        try:
            raw_output = call_mcp_search(keywords, limit=15, timeout=120)
        except FileNotFoundError as e:
            logger.error("rednote-mcp not available: %s", e)
            return []
        except subprocess.TimeoutExpired:
            logger.error("XHS search timed out")
            return []
        except RuntimeError as e:
            logger.error("XHS search failed: %s", e)
            return []

        if not raw_output.strip():
            logger.warning("XHS search returned no results")
            return []

        notes = _parse_notes_text(raw_output)
        logger.info("Got %d notes from XHS search", len(notes))

        if not notes:
            return []

        # Use AI to extract job posts
        job_dicts = _extract_jobs_via_ai(notes, query)
        logger.info("AI extracted %d job posts from %d notes", len(job_dicts), len(notes))

        if not job_dicts:
            return []

        # Inject source_url from notes if not present
        for jd in job_dicts:
            if not jd.get("source_url"):
                # Try matching by title
                for note in notes:
                    if note.get("url") and note.get("title", "") in str(jd.get("title", "")):
                        jd["source_url"] = note["url"]
                        break

        return parse_xhs_jobs(job_dicts)

    def get_job_detail(self, job_id: str) -> Job | None:
        """XHS search jobs already have JD from initial extraction."""
        return None
