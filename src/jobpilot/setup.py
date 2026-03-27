"""
JobPilot setup — interactive preference questionnaire.

Collects 13 questions about the user's job-seeking preferences
and writes them to data/resume_config.yaml.
"""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console

from jobpilot import config

console = Console()

# ------------------------------------------------------------------
# Question option constants
# ------------------------------------------------------------------
CAREER_STAGES = ["在校生", "应届毕业生", "在职跳槽", "自由职业/Gap"]
JOB_TYPES = ["实习", "全职", "兼职/自由职业"]
CAREER_TRACKS = [
    "AI产品经理", "后端工程师", "算法工程师", "产品经理",
    "前端/全栈", "数据分析", "运营/市场",
]
INDUSTRIES = [
    "AI/大模型", "互联网", "金融科技", "创业公司",
    "游戏", "电商", "企业服务", "硬件/IoT",
]
COMPANY_TYPES = ["大厂", "创业公司", "外企", "国企", "中型民企"]
REMOTE_OPTIONS = ["纯远程", "海外可以", "只接受国内线下", "都可以"]
PRIORITIES = ["薪资", "成长空间", "技术深度", "团队氛围", "WLB", "行业前景"]
DEAL_BREAKERS = ["996", "大小周", "单休", "频繁出差", "加班多", "无社保"]
CITY_OPTIONS = ["深圳", "北京", "上海", "杭州", "广州", "成都"]

# Keys that the questionnaire writes — used by merge logic
_QUESTIONNAIRE_KEYS = frozenset({
    "career_stage", "job_type", "career_track", "previous_track",
    "preferred_industries", "preferred_company_size", "preferred_cities",
    "remote_preference", "min_salary", "priorities", "deal_breakers",
    "core_strengths", "learning_goals",
})


# ------------------------------------------------------------------
# Prompt helpers
# ------------------------------------------------------------------
def prompt_single(question: str, options: list[str], step: int, total: int) -> str:
    """Prompt user to pick one option. Returns the chosen label."""
    console.print(f"\n[bold cyan][{step}/{total}][/bold cyan] {question}")
    for i, opt in enumerate(options, 1):
        console.print(f"  {i}. {opt}")
    while True:
        raw = typer.prompt(f"请选择 [1-{len(options)}]")
        if raw.strip().isdigit():
            idx = int(raw.strip())
            if 1 <= idx <= len(options):
                return options[idx - 1]
        console.print("[yellow]请输入有效编号[/yellow]")


def prompt_multi(
    question: str, options: list[str], step: int, total: int, *, allow_custom: bool = False,
) -> list[str]:
    """Prompt user to pick multiple options (comma-separated). Returns list of labels."""
    console.print(f"\n[bold cyan][{step}/{total}][/bold cyan] {question}")
    for i, opt in enumerate(options, 1):
        console.print(f"  {i}. {opt}")
    if allow_custom:
        console.print(f"  {len(options) + 1}. 其他（自定义输入）")
    hint = "输入编号，逗号分隔，可多选"
    raw = typer.prompt(hint)
    chosen: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part)
            if 1 <= idx <= len(options):
                chosen.append(options[idx - 1])
            elif allow_custom and idx == len(options) + 1:
                custom = typer.prompt("请输入自定义内容")
                chosen.extend([c.strip() for c in custom.split(",") if c.strip()])
        elif part:
            chosen.append(part)
    return chosen if chosen else options[:1]


def prompt_ranking(
    question: str, options: list[str], step: int, total: int, top_n: int = 3,
) -> list[str]:
    """Prompt user to rank top N from options. Returns ordered list."""
    console.print(f"\n[bold cyan][{step}/{total}][/bold cyan] {question}")
    for i, opt in enumerate(options, 1):
        console.print(f"  {i}. {opt}")
    raw = typer.prompt(f"按重要性排序输入前 {top_n} 个编号（逗号分隔）")
    result: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part)
            if 1 <= idx <= len(options) and options[idx - 1] not in result:
                result.append(options[idx - 1])
    return result[:top_n] if result else options[:top_n]


def prompt_text(question: str, step: int, total: int, *, allow_skip: bool = False) -> str:
    """Prompt user for free-text input. Returns string."""
    skip_hint = "（回车跳过）" if allow_skip else ""
    console.print(f"\n[bold cyan][{step}/{total}][/bold cyan] {question}{skip_hint}")
    raw = typer.prompt("", default="" if allow_skip else ...)
    return raw.strip()


def prompt_number(question: str, step: int, total: int) -> int:
    """Prompt user for a number. Returns int."""
    console.print(f"\n[bold cyan][{step}/{total}][/bold cyan] {question}")
    while True:
        raw = typer.prompt("请输入数字")
        if raw.strip().isdigit():
            return int(raw.strip())
        console.print("[yellow]请输入有效数字[/yellow]")


# ------------------------------------------------------------------
# Questionnaire flow
# ------------------------------------------------------------------
def run_questionnaire() -> dict:
    """Run the full 13-question questionnaire. Returns preferences dict."""
    total = 13

    career_stage = prompt_single("你目前的职业身份？", CAREER_STAGES, 1, total)
    job_type = prompt_single("你在找什么类型的工作？", JOB_TYPES, 2, total)
    career_track = prompt_multi(
        "你想做什么方向？（可多选）", CAREER_TRACKS, 3, total, allow_custom=True,
    )
    previous_track = prompt_text(
        "如果你在转行，你之前的方向是什么？", 4, total, allow_skip=True,
    )
    preferred_industries = prompt_multi(
        "你感兴趣的行业？（可多选）", INDUSTRIES, 5, total, allow_custom=True,
    )
    preferred_company_size = prompt_multi(
        "你偏好的公司类型？（可多选）", COMPANY_TYPES, 6, total,
    )
    preferred_cities = prompt_multi(
        "你偏好的工作城市？（可多选，支持自由输入）",
        CITY_OPTIONS, 7, total, allow_custom=True,
    )
    remote_preference = prompt_single(
        "是否接受远程/海外工作？", REMOTE_OPTIONS, 8, total,
    )
    min_salary = prompt_number("你能接受的最低月薪？（实习可填 0）", 9, total)
    priorities = prompt_ranking(
        "你最看重什么？（排序前 3）", PRIORITIES, 10, total, top_n=3,
    )
    deal_breakers = prompt_multi(
        "有什么绝对不能接受的？（可多选）", DEAL_BREAKERS, 11, total,
    )
    core_strengths = prompt_text("你最擅长的 3 个技能/工具？", 12, total)
    learning_goals = prompt_text("你正在学习或想发展的方向？", 13, total)

    return {
        "career_stage": career_stage,
        "job_type": job_type,
        "career_track": career_track,
        "previous_track": previous_track,
        "preferred_industries": preferred_industries,
        "preferred_company_size": preferred_company_size,
        "preferred_cities": preferred_cities,
        "remote_preference": remote_preference,
        "min_salary": min_salary,
        "priorities": priorities,
        "deal_breakers": deal_breakers,
        "core_strengths": core_strengths,
        "learning_goals": learning_goals,
    }


# ------------------------------------------------------------------
# Persistence
# ------------------------------------------------------------------
def load_existing_preferences() -> dict:
    """Load existing preferences from resume_config.yaml, or empty dict."""
    cfg_path = Path(config.DATA_DIR) / "resume_config.yaml"
    if not cfg_path.exists():
        return {}
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("preferences", {})


def save_preferences(new_prefs: dict) -> Path:
    """Merge questionnaire preferences into data/resume_config.yaml.

    Only updates keys that the questionnaire produces (_QUESTIONNAIRE_KEYS).
    Preserves any extra keys (e.g. role_fit) already in preferences.
    """
    cfg_path = Path(config.DATA_DIR) / "resume_config.yaml"
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    existing_prefs = data.get("preferences", {})
    # Merge: update only questionnaire keys, keep the rest
    merged = {k: v for k, v in existing_prefs.items() if k not in _QUESTIONNAIRE_KEYS}
    merged.update(new_prefs)
    data["preferences"] = merged

    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return cfg_path
