"""
Resume PDF generator — convert Markdown resume to PDF.

Phase 2 feature. Uses weasyprint (optional dependency).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def markdown_to_pdf(md_path: Path, output_path: Path | None = None) -> Path:
    """Convert a Markdown resume to PDF.

    Requires weasyprint: pip install jobpilot[pdf]

    Args:
        md_path: Path to Markdown file
        output_path: Where to save PDF. Default: same dir, .pdf extension

    Returns:
        Path to the generated PDF
    """
    if output_path is None:
        output_path = md_path.with_suffix(".pdf")

    try:
        import markdown
        from weasyprint import HTML
    except ImportError:
        raise ImportError(
            "PDF generation requires weasyprint. "
            "Install with: pip install jobpilot[pdf]"
        )

    md_content = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(md_content, extensions=["tables", "fenced_code"])

    html_full = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
    padding: 40px;
  }}
  h1 {{ font-size: 22pt; color: #1a1a2e; margin-bottom: 5px; }}
  h2 {{ font-size: 14pt; color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 3px; }}
  h3 {{ font-size: 12pt; color: #333; }}
  ul {{ padding-left: 20px; }}
  li {{ margin-bottom: 3px; }}
  strong {{ color: #1a1a2e; }}
  p {{ margin: 5px 0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=html_full).write_pdf(str(output_path))
    logger.info("PDF generated: %s", output_path)
    return output_path
