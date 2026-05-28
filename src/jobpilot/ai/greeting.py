"""
Greeting (打招呼语) generator.

Given a job + the user's resume, produce a short, personalized opening message
to send to the HR — the kind Boss 直聘 / 小红书 私信 expects. The user sends it
themselves; JobPilot never contacts recruiters automatically.

Honesty rule (same as tailoring/interview): reference only the candidate's real
experience, never fabricate.
"""

from __future__ import annotations

import logging

from jobpilot import config
from jobpilot.models import Job, JobScore, Profile

logger = logging.getLogger(__name__)


class GreetingError(RuntimeError):
    """Raised when a greeting cannot be generated (e.g. no API key)."""


GREETING_PROMPT = """\
你是一位求职沟通教练。基于以下岗位和候选人简历，写一条发给 HR 的「打招呼开场白」。

## 目标岗位
- 职位：{job_title}
- 公司：{company}
- JD：
{jd_text}

## 候选人简历
{resume_text}
{score_context}
## 要求
- **硬性长度上限：最多 2 句话、总字数不超过 80 字**。这是 HR 私信第一句，不是自我介绍，超长即失败。
- **结构**：第 1 句 = 我是谁(姓名+一个最匹配的点+一个简历里的真实数字)；第 2 句 = 软收（如"方便的话想聊聊"）
- 只对标 JD 最核心的 1 个点，其余一概不写
- 口语、真诚；不用 emoji，不用"贵公司""贵司""鄙人""您好打扰了"这类客套
- **只举一个项目、一个数字**，不堆工具名和细节
- **事实零漂移**：姓名、学校、专业、学位与简历**逐字一致**，不得改写推测；只引用简历里确实存在的经历和数据
- 直接输出正文，不要任何解释、标题或引号

## 长度与风格范例（严格仿照这个长度，不要更长）
你好，我是张三，XX大学YY专业在读。做过一个[最相关项目]，[一个关键数字结果]，对这个岗位的[核心点]很感兴趣，方便的话想聊聊。
"""


def _format_score_context(score: JobScore | None) -> str:
    if not score or not score.highlights:
        return ""
    return "\n## 可强调的匹配亮点\n" + "；".join(score.highlights) + "\n"


def build_greeting_prompt(
    profile: Profile, job: Job, score: JobScore | None = None
) -> str:
    """Build the greeting prompt (pure, testable, no API call)."""
    return GREETING_PROMPT.format(
        job_title=job.title,
        company=job.company,
        jd_text=job.jd_text or "(无 JD)",
        resume_text=profile.raw_text or "(无简历文本)",
        score_context=_format_score_context(score),
    )


def generate_greeting(
    profile: Profile, job: Job, score: JobScore | None = None
) -> str:
    """Generate a greeting via Claude API.

    Raises:
        GreetingError: when no API key is configured (use build_greeting_prompt
            for a manual Claude.ai workflow instead).
    """
    if not config.ANTHROPIC_API_KEY:
        raise GreetingError(
            "未配置 ANTHROPIC_API_KEY。可用 build_greeting_prompt 导出 prompt "
            "到 Claude.ai 手动生成。"
        )

    prompt = build_greeting_prompt(profile, job, score)

    import anthropic

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        logger.exception("Greeting API call failed")
        raise GreetingError(f"API 调用失败: {exc}") from exc

    return message.content[0].text.strip().strip('"').strip()
