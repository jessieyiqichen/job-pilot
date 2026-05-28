"""
Greeting (打招呼话术) generator — personal-style version.

Architecture: the self-intro is a FIXED template from resume_config.yaml
(zero fact drift), and only the **hook** (钩子句) is generated per-JD by the
LLM following an explicit strategy + hard style rules. The composed greeting
is what you copy and send yourself — JobPilot never contacts recruiters.

Config (resume_config.yaml):
  greeting:
    base_template: "...{hook}，希望能进一步沟通。"
    products: [{name, desc, use_for, hook_detail}, ...]
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from jobpilot import config
from jobpilot.models import Job, JobScore

logger = logging.getLogger(__name__)


class GreetingError(RuntimeError):
    """Raised when a greeting cannot be generated."""


# JD keywords worth echoing verbatim as a "暗号" (signal you read the JD)
ECHO_KEYWORDS: tuple[str, ...] = (
    "vibe coding",
    "harness first",
    "harness-first",
    "ai memory",
    "agent",
    "数字员工",
    "多 agent",
    "prompt",
    "eval",
)

# Words/patterns that are hard failures of the user's style spec
_BANNED_WORDS = ("届时", "特此", "顺颂商祺", "贵司", "贵公司", "鄙人")

HOOK_PROMPT = """\
你在为求职者写一条打招呼话术里的「钩子句」。自我介绍部分是固定的，你**只写钩子句**这一段。

## 候选人的三个产品（钩子只能用这些真实项目，不得编造）
{products_text}

## 目标岗位 JD
{jd_text}

## 钩子句生成策略
1. 读 JD，找出 1-2 个跟候选人优势最匹配的关键词
2. 用最相关的那个产品打钩子（按上面每个产品的 use_for 判断该用哪个）
3. 如果 JD 出现这些词，钩子里就原样 echo 它们当"暗号"：{echo_list}
4. 钩子必须落到**具体行为**，不能空喊。
   反例（空）："这跟岗位很契合"
   正例（具体）："MusiClaw 我自建了 eval 框架，用 YAML 定义测试集跑 A/B 实验"

## 硬性风格规则（违反任何一条都算失败）
- 不用长破折号 ——
- 不用中文括号（）做注释，展开成同位语。错："JobPilot（多渠道求职 Agent）"；对："多渠道求职 Agent JobPilot"
- 不用嵌套引号
- 不把 "vibe coding" 当自我标签（它隐含"AI 替我想"），要用"AI 辅助开发"这类含人主导语义的说法。例外：JD 明确用 vibe coding 当关键词时，钩子可原样 echo
- 不用老气书面词：届时、特此、顺颂商祺
- 不堆 buzzword、不堆数据、不写三段平行排比（太像 AI 生成）
- 不用黑话：ground truth 说成"基准"，"按渠道隔离失败"这种说成大白话
- 第一人称，体现判断逻辑（讲为什么这么做，而不是罗列做了什么）

## 输出
只输出钩子句正文，80-130 字，第一人称。
**不要**句尾标点（后面会自动接"，希望能进一步沟通。"）。
不要任何解释、标题或引号。
"""


def _load_greeting_config() -> dict:
    cfg_path = Path(config.DATA_DIR) / "resume_config.yaml"
    if not cfg_path.exists():
        return {}
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("greeting", {}) or {}


def _format_products(products: list[dict]) -> str:
    lines = []
    for p in products:
        lines.append(
            f"- {p.get('desc', '')} {p.get('name', '')}"
            f"｜用于：{p.get('use_for', '')}"
            f"｜可写素材：{p.get('hook_detail', '')}"
        )
    return "\n".join(lines)


def build_hook_prompt(jd_text: str, products: list[dict]) -> str:
    """Build the hook-generation prompt (pure, testable)."""
    return HOOK_PROMPT.format(
        products_text=_format_products(products),
        jd_text=jd_text or "(无 JD)",
        echo_list="、".join(ECHO_KEYWORDS),
    )


def check_style_violations(text: str, jd_text: str = "") -> list[str]:
    """Return a list of detectable hard-style violations (for review warnings)."""
    violations: list[str] = []
    if "——" in text or "—" in text:
        violations.append("出现长破折号 ——")
    if "（" in text or "）" in text:
        violations.append("出现中文括号（）注释")
    if text.count('"') > 2 or text.count("“") + text.count("”") > 2:
        violations.append("疑似嵌套引号")
    for w in _BANNED_WORDS:
        if w in text:
            violations.append(f"出现禁用词「{w}」")
    if "vibe coding" in text.lower() and "vibe coding" not in (jd_text or "").lower():
        violations.append("把 vibe coding 当自我标签（JD 未出现该词）")
    return violations


def compose_greeting(base_template: str, hook: str) -> str:
    """Insert the hook into the fixed self-intro template."""
    hook = hook.strip().strip('"').strip("“”").rstrip("。，,. ")
    if "{hook}" in base_template:
        return base_template.replace("{hook}", hook)
    # Fallback: append before a trailing closer if no placeholder
    return f"{base_template} {hook}，希望能进一步沟通。"


def generate_greeting(job: Job, score: JobScore | None = None) -> str:
    """Generate the full personal-style greeting (fixed intro + LLM hook).

    Raises:
        GreetingError: when no greeting config or no API key.
    """
    gcfg = _load_greeting_config()
    base_template = gcfg.get("base_template", "")
    products = gcfg.get("products", []) or []
    if not base_template:
        raise GreetingError(
            "resume_config.yaml 缺少 greeting.base_template，无法生成个人风格话术。"
        )
    if not config.ANTHROPIC_API_KEY:
        raise GreetingError(
            "未配置 ANTHROPIC_API_KEY。可用 build_hook_prompt 导出 prompt 到 Claude.ai 生成钩子。"
        )

    prompt = build_hook_prompt(job.jd_text or "", products)

    import anthropic

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Greeting hook API call failed")
        raise GreetingError(f"API 调用失败: {exc}") from exc

    hook = message.content[0].text.strip()
    return compose_greeting(base_template, hook)
