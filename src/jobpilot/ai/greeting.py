"""
Greeting (打招呼话术) generator — channel-aware, config-driven.

Three channels, different forms (all rules live in resume_config.yaml's
`greeting` block — tweak preferences by editing config, not code):
  - boss : short greeting + a "简历截图" caption. HRBP screening layer.
  - xhs  : DM, slightly more natural but still composed.
  - email: formal email with subject + structure + signature.

Fact anchoring: the self-intro facts come from the fixed `base_template`
(boss/xhs) or are pinned in the email prompt — only the per-JD hook varies.
You send everything yourself; JobPilot never contacts recruiters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from jobpilot import config
from jobpilot.models import Job, JobScore

logger = logging.getLogger(__name__)


class GreetingError(RuntimeError):
    """Raised when a greeting cannot be generated."""


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

# Hard style failures: 老气书面 + 过随意口语 + 客套
_BANNED_WORDS = (
    "届时", "特此", "顺颂商祺", "贵司", "贵公司", "鄙人",
    "挺像的", "这套", "唠嗑",
)

DEFAULT_FORMALITY = (
    "商务正式但自然，像一个清楚自己在说什么的人，不像 AI 模板。"
    "不要太随意，也不要太老气。"
)

# Injected into prompts so the model AVOIDS these (self-check catches leftovers)
_AVOID_LINE = (
    "- 以下词一个都不能出现：届时、特此、顺颂商祺、贵司、贵公司、鄙人、"
    "挺像的、这套、唠嗑（公司直接称名字或'你们/团队'）"
)

# Non-personal channel defaults; resume_config.yaml overrides/extends these
CHANNEL_DEFAULTS: dict[str, dict] = {
    "boss": {"tone": "短、克制、专业", "hook_max_chars": 80, "reply_rate": ""},
    "xhs": {"tone": "稍自然但得体", "hook_max_chars": 130, "reply_rate": ""},
    "email": {"structure": "自我介绍 → 看到招聘并表达兴趣 → 相关经历 → 随附简历 → 期待沟通",
              "reply_rate": ""},
}


@dataclass(frozen=True)
class GreetingResult:
    """A generated greeting plus channel-specific extras."""

    channel: str
    body: str
    subject: str = ""          # email only
    attachment_note: str = ""  # boss only

    def save_text(self) -> str:
        parts: list[str] = []
        if self.subject:
            parts.append(f"主题：{self.subject}")
        parts.append(self.body)
        if self.attachment_note:
            parts.append(f"[发完紧跟简历截图，配文] {self.attachment_note}")
        return "\n\n".join(parts)


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------


def _load_greeting_config() -> dict:
    cfg_path = Path(config.DATA_DIR) / "resume_config.yaml"
    if not cfg_path.exists():
        return {}
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("greeting", {}) or {}


def _channel_cfg(channel: str, gcfg: dict) -> dict:
    merged = dict(CHANNEL_DEFAULTS.get(channel, {}))
    merged.update((gcfg.get("channels", {}) or {}).get(channel, {}) or {})
    return merged


def interaction_tips(gcfg: dict | None = None) -> list[str]:
    """HR-interaction rules to surface to the user (not part of generation)."""
    gcfg = gcfg if gcfg is not None else _load_greeting_config()
    return list(gcfg.get("interaction_rules", []) or [])


# ----------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------


def _format_products(products: list[dict]) -> str:
    return "\n".join(
        f"- {p.get('desc', '')} {p.get('name', '')}"
        f"｜用于：{p.get('use_for', '')}｜可写素材：{p.get('hook_detail', '')}"
        for p in products
    )


_HOOK_RULES = """\
## 钩子句生成策略
1. 读 JD，找出 1-2 个跟候选人优势最匹配的关键词
2. **只用一个最相关的产品**打钩子（按 use_for 判断），绝不同时讲两个
3. 如果 JD 出现这些词，钩子里原样 echo 当"暗号"：{echo_list}
4. 钩子必须落到**具体行为**，不空喊。反例"很契合"；正例"自建了 eval 框架，用 YAML 定义测试集跑 A/B 实验"

## 硬性风格规则（违反任一即失败）
- 正式度：{formality}
- 不用长破折号 ——；不用中文括号（）做注释，展开成同位语；不用嵌套引号
{avoid_line}
- 不把 "vibe coding" 当自我标签（隐含"AI 替我想"），用"AI 辅助开发"这类含人主导语义的说法；例外：JD 明确用 vibe coding 时可 echo
- 第一人称，体现判断逻辑（讲为什么这么做，不是罗列做了什么）"""


def build_hook_prompt(
    jd_text: str, products: list[dict], channel_cfg: dict, formality: str, voice: str = ""
) -> str:
    """Hook prompt for boss/xhs (fixed intro + this hook). Pure, testable.

    `voice` is an optional few-shot block of the user's real writing (see
    voice.py) so the hook comes out in their voice and needs less rewriting.
    """
    max_chars = channel_cfg.get("hook_max_chars", 110)
    tone = channel_cfg.get("tone", "")
    voice_block = f"\n{voice}\n" if voice else ""
    return f"""\
你在为求职者写打招呼话术里的「钩子句」。自我介绍是固定的，你**只写钩子句**。

## 候选人的产品（钩子只能用这些真实项目，不得编造）
{_format_products(products)}

## 目标岗位 JD
{jd_text or "(无 JD)"}

{_HOOK_RULES.format(echo_list="、".join(ECHO_KEYWORDS), formality=formality, avoid_line=_AVOID_LINE)}

## 本渠道语气
{tone}
{voice_block}
## 输出
只输出钩子句正文，第一人称，**只讲一个产品、不超过 {max_chars} 字**。
不要句尾标点（后面会自动接"，希望能进一步沟通。"）。不要解释、标题或引号。
"""


def build_email_prompt(
    jd_text: str, job_title: str, company: str, products: list[dict],
    intro_facts: str, structure: str, formality: str, voice: str = "",
) -> str:
    """Email body prompt — formal, structured, facts pinned. Pure, testable.

    `voice` is an optional few-shot block of the user's real writing.
    """
    voice_block = f"\n{voice}\n" if voice else ""
    return f"""\
你在为求职者写一封**求职邮件正文**（不含主题行和落款，那两部分会自动加）。

## 必须逐字使用的事实（不得改写或推测）
{intro_facts}

## 候选人的产品（用一个最相关的打钩子，真实素材如下）
{_format_products(products)}

## 目标岗位
- 职位：{job_title}｜公司：{company}
- JD：
{jd_text or "(无 JD)"}

## 邮件结构（按此顺序）
{structure}

## 硬性风格规则（违反任一即失败）
- 正式度：{formality}
- 称谓后用全角冒号"："
- 不用长破折号 ——；不用中文括号（）注释；不用嵌套引号
{_AVOID_LINE}
- 相关经历只讲一个产品、落到具体行为，不堆数据不写三段排比
- 第一人称，体现判断逻辑
{voice_block}
## 输出
只输出邮件正文（从称谓到"期待与您进一步沟通"这类结尾），不要主题行、不要落款签名、不要解释。
"""


# ----------------------------------------------------------------------
# Style check
# ----------------------------------------------------------------------


def check_style_violations(text: str, jd_text: str = "") -> list[str]:
    """Detectable hard-style violations, for pre-send review warnings."""
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


# ----------------------------------------------------------------------
# Compose / generate
# ----------------------------------------------------------------------


def compose_greeting(base_template: str, hook: str) -> str:
    """Insert the hook into the fixed self-intro template."""
    hook = hook.strip().strip('"').strip("“”").rstrip("。，,. ")
    if "{hook}" in base_template:
        return base_template.replace("{hook}", hook)
    return f"{base_template} {hook}，希望能进一步沟通。"


def _call_llm(prompt: str, max_tokens: int) -> str:
    import anthropic

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Greeting API call failed")
        raise GreetingError(f"API 调用失败: {exc}") from exc
    return message.content[0].text.strip()


def generate_greeting(
    job: Job, score: JobScore | None = None, channel: str = "boss"
) -> GreetingResult:
    """Generate a channel-specific greeting (boss / xhs / email).

    Raises:
        GreetingError: on missing config / API key / unknown channel.
    """
    if channel not in CHANNEL_DEFAULTS:
        raise GreetingError(f"未知渠道: {channel}（可选 boss/xhs/email）")

    gcfg = _load_greeting_config()
    products = gcfg.get("products", []) or []
    formality = gcfg.get("formality", DEFAULT_FORMALITY)
    ch = _channel_cfg(channel, gcfg)

    if not config.ANTHROPIC_API_KEY:
        raise GreetingError("未配置 ANTHROPIC_API_KEY，无法生成话术。")

    # Few-shot the user's real writing so the output sounds like them, not AI.
    from jobpilot.voice import build_voice_block, load_samples

    voice = build_voice_block(load_samples())

    if channel == "email":
        base_template = gcfg.get("base_template", "")
        if not base_template:
            raise GreetingError("resume_config.yaml 缺少 greeting.base_template。")
        # Pin the self-intro facts by feeding the fixed template (sans {hook}) as facts
        intro_facts = base_template.replace("{hook}，", "").replace("{hook}", "")
        body = _call_llm(
            build_email_prompt(
                job.jd_text or "", job.title, job.company, products,
                intro_facts, ch.get("structure", ""), formality, voice,
            ),
            max_tokens=1200,
        )
        subject = (ch.get("subject_format", "") or "").replace("{job_title}", job.title)
        signature = ch.get("signature", "")
        full_body = f"{body}\n\n{signature}" if signature else body
        return GreetingResult(channel="email", body=full_body, subject=subject)

    # boss / xhs: fixed intro + LLM hook
    base_template = gcfg.get("base_template", "")
    if not base_template:
        raise GreetingError("resume_config.yaml 缺少 greeting.base_template。")
    hook = _call_llm(
        build_hook_prompt(job.jd_text or "", products, ch, formality, voice), max_tokens=600
    )
    body = compose_greeting(base_template, hook)
    attachment_note = ch.get("attachment_note", "") if channel == "boss" else ""
    return GreetingResult(channel=channel, body=body, attachment_note=attachment_note)
