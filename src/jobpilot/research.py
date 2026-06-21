"""
求职资料检索 — 让军师按需去小红书 / web 搜面试题、面经、相关帖子。

跟 adapters/*search 的区别：那些是为「入库岗位」抽结构化字段，这里是为「准备面试 /
做功课」提炼可读资料（面试真题、考点、经验帖），不写进 jobs 表。

复用 xhs_search 已经踩通的两块基建：
- ``call_mcp_search`` + ``_parse_notes_text`` —— 小红书笔记抓取与解析
- ``_extract_json_from_text`` —— 带截断恢复的 JSON 解析

降级策略：
- 没有 API key 时，web 检索无法进行（需官方 web_search 工具）→ 返回空；
  小红书仍能抓到笔记，只是不做 AI 提炼 → 原样返回笔记，照样有用。
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime

from jobpilot import config
from jobpilot.adapters.xhs_search import (
    _extract_json_from_text,
    _parse_notes_text,
    call_mcp_search,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResearchResult:
    """一条检索到的资料（面经 / 帖子 / 考点）。"""

    title: str
    summary: str
    url: str = ""
    source: str = ""  # "xhs" | "web"
    author: str = ""


def _to_result(item: dict, source: str) -> ResearchResult | None:
    """dict → ResearchResult；缺 title 返回 None（不猜）。"""
    title = (item.get("title") or "").strip()
    if not title:
        return None
    return ResearchResult(
        title=title,
        summary=(item.get("summary") or item.get("content") or "").strip(),
        url=(item.get("url") or item.get("source_url") or "").strip(),
        source=source,
        author=(item.get("author") or "").strip(),
    )


# ---------------------------------------------------------------------------
# 小红书检索
# ---------------------------------------------------------------------------

# 图片是面经的主要载体（小红书很多帖正文只写"详见图"）。喂给 vision 才能读到真题，
# 但每张图烧 token，必须设硬上限。
MAX_IMAGES_PER_NOTE = 3
MAX_IMAGES_PER_REQUEST = 12

XHS_DISTILL_HEADER = """\
你是求职资料整理助手。下面是从小红书搜到的笔记，用户在准备面试 / 做功课。

## 用户在查
{query}

## 笔记列表（部分笔记附带图片，内容常常在图里）
"""

XHS_DISTILL_TASK = """\

## 任务
1. 只挑出和这条查询真正相关、对求职 / 面试准备有帮助的笔记（面经、真题、考点、经验、避坑）。
2. 跳过广告、无关生活帖、纯引流帖。
3. 对每条提炼：标题、要点摘要（**尤其把图里和文字里具体的面试题、考点、经验列出来**，别只说"分享了面经"）。
4. 文字和图片都要看；图里有题目就把题目转录到 summary 里。
5. 不要编造笔记里没有的内容；笔记信息少就如实简短。

## 输出（严格 JSON 数组，不要其他文字）
[
  {
    "title": "笔记标题",
    "summary": "要点摘要，重点是具体题目/考点/经验（包含从图里读出的）",
    "url": "笔记链接",
    "author": "作者"
  }
]
"""


def _build_distill_content(notes: list[dict], query: str) -> list[dict]:
    """Build multimodal content blocks for one distill request.

    Interleaves text blocks (one per note) with image blocks (each note's images,
    capped per-note and per-request) so the model knows which image belongs where.
    """
    blocks: list[dict] = [{"type": "text", "text": XHS_DISTILL_HEADER.format(query=query)}]
    images_used = 0

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
        blocks.append({"type": "text", "text": "\n".join(parts)})

        note_images = (note.get("images") or [])[:MAX_IMAGES_PER_NOTE]
        for img_url in note_images:
            if images_used >= MAX_IMAGES_PER_REQUEST:
                logger.info(
                    "Image budget %d hit; dropping remaining images",
                    MAX_IMAGES_PER_REQUEST,
                )
                break
            blocks.append({"type": "image", "source": {"type": "url", "url": img_url}})
            images_used += 1

    blocks.append({"type": "text", "text": XHS_DISTILL_TASK})
    return blocks


def _distill_notes_via_ai(notes: list[dict], query: str) -> list[ResearchResult]:
    """Distill XHS notes (text + images) via Claude vision. No key / error → []."""
    if not config.ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY, cannot distill XHS notes")
        return []

    content_blocks = _build_distill_content(notes, query)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": content_blocks}],
        )
    except Exception:
        logger.exception("Anthropic API call failed for XHS distill")
        return []

    text = response.content[0].text.strip()
    items = _extract_json_from_text(text)
    results = [_to_result(it, "xhs") for it in items]
    return [r for r in results if r is not None]


def _notes_to_raw_results(notes: list[dict]) -> list[ResearchResult]:
    """无 API key 时的降级：原样把笔记包成结果，不做提炼。"""
    results = [_to_result(n, "xhs") for n in notes]
    return [r for r in results if r is not None]


def research_xhs(query: str, limit: int = 12, timeout: int = 120) -> list[ResearchResult]:
    """去小红书搜资料。出错优雅降级为 []，无 API key 则返回未提炼的原始笔记。"""
    logger.info("Researching XHS for: %s", query)
    try:
        raw_output = call_mcp_search(query, limit=limit, timeout=timeout)
    except FileNotFoundError as e:
        logger.error("rednote-mcp not available: %s", e)
        return []
    except subprocess.TimeoutExpired:
        logger.error("XHS research timed out")
        return []
    except RuntimeError as e:
        logger.error("XHS research failed: %s", e)
        return []

    if not raw_output.strip():
        logger.warning("XHS research returned no results")
        return []

    notes = _parse_notes_text(raw_output)
    logger.info("Got %d notes from XHS research", len(notes))
    if not notes:
        return []

    if not config.ANTHROPIC_API_KEY:
        return _notes_to_raw_results(notes)

    return _distill_notes_via_ai(notes, query)


# ---------------------------------------------------------------------------
# Web 检索
# ---------------------------------------------------------------------------

WEB_RESEARCH_PROMPT = """\
你是求职资料检索助手。用户在准备面试 / 做功课，请联网搜「{query}」的真实资料。

请在中国主流平台（小红书、牛客、知乎、脉脉、相关公众号、公司官网等）搜真实内容（{year} 年优先）。

要求：
1. 只返回真实存在的资料，**绝对不要编造题目或链接**。
2. summary 重点放**具体的面试题、考点、备考要点、过来人经验**，不要泛泛而谈。
3. 找不到就少返回几条，不要凑数。

## 输出（严格 JSON 数组，不要 markdown 代码块）
[
  {{
    "title": "资料标题",
    "summary": "具体题目/考点/经验",
    "url": "来源链接"
  }}
]
"""


def research_web(query: str) -> list[ResearchResult]:
    """用 Anthropic web_search 工具搜资料。无 API key → []（web 检索必须联网）。"""
    if not config.ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY set, web research skipped")
        return []

    year = str(datetime.now().year)
    prompt = WEB_RESEARCH_PROMPT.format(query=query, year=year)

    try:
        import anthropic

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
        logger.exception("Anthropic API call failed for web research")
        return []

    text_parts = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    ]
    full_text = "\n".join(text_parts)
    if not full_text.strip():
        logger.warning("Web research returned empty response")
        return []

    items = _extract_json_from_text(full_text)
    results = [_to_result(it, "web") for it in items]
    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def research(query: str, channel: str = "both", limit: int = 12) -> list[ResearchResult]:
    """按渠道检索资料。channel: ``xhs`` | ``web`` | ``both``。"""
    results: list[ResearchResult] = []
    if channel in ("xhs", "both"):
        results.extend(research_xhs(query, limit=limit))
    if channel in ("web", "both"):
        results.extend(research_web(query))
    return results
