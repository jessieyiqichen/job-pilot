"""
Conversational chat advisor (jobpilot chat).

A real multi-turn chat with a job-hunt 军师 that remembers the conversation and
knows the user's actual situation — diagnosis, preferences, high-score jobs are
loaded once into the system prompt, then the dialogue accrues turn by turn.

Unlike `ask` (one-shot Q&A), this keeps history, so "那个字节的岗位" resolves
against earlier turns. Chat needs an API key — there's no offline fallback for a
live conversation.
"""

from __future__ import annotations

import logging
from typing import Callable

from jobpilot import config, followup
from jobpilot.advisor import _format_preferences
from jobpilot.ask import AskContext, gather_context
from jobpilot.chat_store import load_history, save_history
from jobpilot.db import JobPilotDB
from jobpilot.followup_store import add_commitments, load_commitments, save_commitments
from jobpilot.models import Profile

logger = logging.getLogger(__name__)

_QUIT_WORDS = frozenset({"exit", "quit", "q", "bye", "退出", "再见"})

# Message = {"role": "user"|"assistant", "content": str}
Message = dict[str, str]


class ChatError(RuntimeError):
    """Raised when chat cannot run (e.g. no API key) or the API call fails."""


def _format_top_jobs(top_jobs: tuple[tuple[str, float], ...]) -> str:
    if not top_jobs:
        return "(暂无高分岗)"
    return "\n".join(f"  - [{score:.1f}] {label}" for label, score in top_jobs)


SYSTEM_PROMPT = """\
你是用户的私人求职军师，长期陪伴一名在校生冲刺 AI 产品经理实习。
你了解 ta 的全部求职数据（下面给出），像一个带过很多人、真正懂 ta 处境的学长。

## ta 的当前处境（来自系统记录，不是估算）
{headline}
- 高分岗（>= {min_score:.0f}）：{high_score_total} 个，已投 {high_score_applied} 个
- 投递总数：{total_applications}（回复 {replied} / 面试 {interview} / Offer {offer} / 被拒 {rejected}）

## ta 的高分岗（可在对话中具体引用）
{top_jobs}

## ta 的偏好
{preferences}

## 你的对话风格
- 这是多轮对话，记得上文。ta 说"那个岗位/上面说的"时，结合前面聊过的内容理解。
- 讲人话，像聊天不像写报告。不堆名词、不灌鸡汤、不说正确的废话。
- 紧扣 ta 的真实数据和偏好，能引用具体岗位/数字就引用。
- 不知道的（公司内部情况、ta 没说过的事）就说不知道，别编。
- 给可执行的下一步；信息不够时主动反问澄清，而不是猜。
- 回答简洁，一次别倒太多，留出来回空间。
"""


def build_system_prompt(profile: Profile, context: AskContext) -> str:
    """Build the chat system prompt that grounds the 军师 in the user's data."""
    d = context.diagnosis
    return SYSTEM_PROMPT.format(
        headline=d.headline,
        min_score=config.MIN_RECOMMEND_SCORE,
        high_score_total=d.high_score_total,
        high_score_applied=d.high_score_applied,
        total_applications=d.total_applications,
        replied=d.replied_count,
        interview=d.interview_count,
        offer=d.offer_count,
        rejected=d.rejected_count,
        top_jobs=_format_top_jobs(context.top_jobs),
        preferences=_format_preferences(profile),
    )


def generate_reply(history: list[Message], system: str) -> str:
    """Send the conversation to Claude and return the assistant's reply.

    Raises:
        ChatError: on API failure (caller checks the key before looping).
    """
    import anthropic

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system,
            messages=history,
        )
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        logger.exception("Chat API call failed")
        raise ChatError(f"API 调用失败: {exc}") from exc

    return message.content[0].text.strip()


def _greet_commitments(
    db: JobPilotDB,
    profile_id: int,
    system: str,
    output_fn: Callable[[str], None],
) -> str:
    """Reconcile + proactively surface open commitments at chat start.

    Returns the system prompt, augmented with any still-open commitments so the
    军师 is aware of them mid-conversation. This is the "主动" part: it brings up
    what you said you'd do instead of waiting to be asked.
    """
    commitments = load_commitments(profile_id)
    if not commitments:
        return system
    reconciled, closed = followup.reconcile_with_applications(commitments, db)
    if closed:
        save_commitments(profile_id, reconciled)  # auto-closed already-applied ones
    open_items = [c for c in reconciled if c.status == "open"]
    if not open_items:
        return system
    output_fn("📌 上次你提到要做这几件事：")
    for c in open_items[:5]:
        due = f"（{c.due_hint}）" if c.due_hint else ""
        output_fn(f"   - {c.text}{due}")
    output_fn("   做了吗？没做的话今天推进一下。")
    return (
        system
        + "\n\n## 待跟进（用户之前说要做、但还没完成的事）\n"
        + "\n".join(f"- {c.text}" for c in open_items)
    )


def _capture_commitments(
    profile_id: int,
    history: list[Message],
    output_fn: Callable[[str], None],
) -> None:
    """On exit, extract action intentions from the conversation and store them."""
    if not (config.ANTHROPIC_API_KEY and history):
        return
    try:
        extracted = followup.extract_commitments(history)
    except followup.FollowupError:
        return
    added = add_commitments(profile_id, extracted)
    if added:
        output_fn(f"🧭 已记下 {len(added)} 件你提到要做的事，下次我会跟进。")


def run_chat(
    db: JobPilotDB,
    profile_id: int = config.DEFAULT_PROFILE_ID,
    job_id: str | None = None,
    *,
    resume: bool = True,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run the interactive chat REPL.

    With resume=True (default) the saved transcript is loaded so the 军师 picks
    up where it left off. The full history is persisted after every turn; only
    the most recent CHAT_MAX_CONTEXT_MESSAGES are sent to the API to bound cost.
    input_fn/output_fn are injectable for testing.

    Raises:
        ChatError: when no API key is configured.
    """
    if not config.ANTHROPIC_API_KEY:
        raise ChatError(
            "未配置 ANTHROPIC_API_KEY。实时对话需要 API；可改用 jobpilot ask 导出 prompt。"
        )

    profile = db.get_profile(profile_id) or Profile(id=profile_id)
    context = gather_context(db, profile_id, job_id)
    system = build_system_prompt(profile, context)

    history: list[Message] = load_history(profile_id) if resume else []

    output_fn("🧭 求职军师已就位，问我任何求职问题（输入 exit / q 退出）。")
    if history:
        output_fn(f"   接着上次聊（已载入 {len(history) // 2} 轮历史）。")
    output_fn(f"   我知道你的处境：{context.diagnosis.headline}")

    # Proactively bring up open commitments from past sessions.
    system = _greet_commitments(db, profile_id, system, output_fn)

    while True:
        try:
            user_text = input_fn("你> ")
        except (EOFError, KeyboardInterrupt):
            output_fn("\n👋 先聊到这，加油。")
            break

        stripped = user_text.strip()
        if stripped.lower() in _QUIT_WORDS:
            output_fn("👋 先聊到这，加油。")
            break
        if not stripped:
            continue

        history.append({"role": "user", "content": stripped})
        window = history[-config.CHAT_MAX_CONTEXT_MESSAGES:]
        try:
            reply = generate_reply(window, system)
        except ChatError as exc:
            output_fn(f"[出错] {exc}")
            history.pop()  # drop the unanswered turn so history stays consistent
            continue
        history.append({"role": "assistant", "content": reply})
        save_history(profile_id, history)  # persist full transcript each turn
        output_fn(f"军师> {reply}")

    # On exit, quietly capture what the user said they'd do, for next time.
    _capture_commitments(profile_id, history, output_fn)
