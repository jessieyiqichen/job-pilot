"""
Resume parser — extract structured profile from PDF/DOCX/Markdown.

Uses PyMuPDF for PDF, python-docx for DOCX, and plain text for Markdown.
Then calls Claude API to extract structured data from the raw text.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from jobpilot import config
from jobpilot.models import Profile, now_iso

logger = logging.getLogger(__name__)

# Structured profile JSON schema (for AI prompt)
PROFILE_SCHEMA = """\
{
  "name": "姓名",
  "title": "当前职位/头衔",
  "years_of_experience": 5,
  "education": [
    {"school": "学校名", "degree": "学位", "major": "专业", "year": 2020}
  ],
  "skills": {
    "languages": ["Python", "Java"],
    "frameworks": ["Django", "Spring"],
    "tools": ["Docker", "Git"],
    "other": ["项目管理", "团队领导"]
  },
  "experience": [
    {
      "company": "公司名",
      "title": "职位",
      "duration": "2020-2023",
      "highlights": ["完成了...的开发", "优化了...的性能"]
    }
  ],
  "projects": [
    {
      "name": "项目名",
      "description": "简短描述",
      "tech_stack": ["Python", "Redis"],
      "highlights": ["亮点1", "亮点2"]
    }
  ],
  "languages": ["中文-母语", "英语-流利"],
  "summary": "一句话概括候选人的核心竞争力"
}"""


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF parsing. Install with: pip install pymupdf"
        )
    doc = fitz.open(str(path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def extract_text_from_docx(path: Path) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "python-docx is required for DOCX parsing. Install with: pip install python-docx"
        )
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_markdown(path: Path) -> str:
    """Read a Markdown file as plain text."""
    return path.read_text(encoding="utf-8")


def extract_text(path: Path) -> str:
    """Extract text from a resume file (PDF, DOCX, or Markdown)."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(path)
    elif suffix in (".md", ".markdown", ".txt"):
        return extract_text_from_markdown(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use PDF, DOCX, or Markdown.")


def parse_resume_with_ai(raw_text: str) -> dict[str, Any]:
    """Use Claude API to parse raw resume text into structured JSON.

    Returns:
        Structured profile dict matching PROFILE_SCHEMA
    """
    if not config.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set. Using basic text extraction.")
        return _basic_parse(raw_text)

    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic package is required. Install with: pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": (
                    "请解析以下简历文本，提取结构化信息。\n\n"
                    "要求：\n"
                    "1. 严格按照以下 JSON schema 输出\n"
                    "2. 如果某个字段信息不存在，保留字段但值为空字符串或空数组\n"
                    "3. skills 要尽可能全面提取\n"
                    "4. 只输出 JSON，不要其他文字\n\n"
                    f"JSON Schema:\n{PROFILE_SCHEMA}\n\n"
                    f"简历文本：\n{raw_text}"
                ),
            }
        ],
    )

    response_text = message.content[0].text.strip()
    # Extract JSON from response (handle markdown code blocks)
    if response_text.startswith("```"):
        lines = response_text.splitlines()
        json_lines = []
        inside = False
        for line in lines:
            if line.startswith("```") and not inside:
                inside = True
                continue
            elif line.startswith("```") and inside:
                break
            elif inside:
                json_lines.append(line)
        response_text = "\n".join(json_lines)

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse AI response as JSON: %s", response_text[:200])
        return _basic_parse(raw_text)


def _basic_parse(raw_text: str) -> dict[str, Any]:
    """Basic fallback parser when AI is not available."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    name = lines[0] if lines else "Unknown"
    return {
        "name": name,
        "title": "",
        "years_of_experience": 0,
        "education": [],
        "skills": {"languages": [], "frameworks": [], "tools": [], "other": []},
        "experience": [],
        "projects": [],
        "languages": [],
        "summary": raw_text[:200] if raw_text else "",
    }


def parse_resume(path: str | Path) -> Profile:
    """Parse a resume file and return a Profile.

    Full pipeline: extract text → AI parse → create Profile.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    logger.info("Extracting text from %s", path.name)
    raw_text = extract_text(path)

    logger.info("Parsing resume with AI (%d chars)...", len(raw_text))
    structured = parse_resume_with_ai(raw_text)

    name = structured.get("name", path.stem)
    return Profile(
        name=name,
        raw_text=raw_text,
        structured=structured,
        updated_at=now_iso(),
    )
