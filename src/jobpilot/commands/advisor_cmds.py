"""Advisory commands: advisor, chat, plan, ask."""

from __future__ import annotations

from pathlib import Path

import typer

from jobpilot import cli, config
from jobpilot.cli import _setup_logging, app, console


@app.command()
def advisor(
    profile_id: int = typer.Option(config.DEFAULT_PROFILE_ID, "--profile", "-p", help="Profile ID"),
    output: str = typer.Option("", "--output", "-o", help="保存到 Markdown 文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """求职策略军师：诊断你的真实求职数据，给本周可执行建议。"""
    _setup_logging(verbose)
    from jobpilot.advisor import (
        AdvisorError,
        build_advisor_prompt,
        diagnose,
        format_diagnosis_markdown,
        generate_advice,
    )

    db = cli._get_db()
    profile = db.get_profile(profile_id)
    if not profile:
        console.print("[red]No profile found. Run 'jobpilot resume <file>' first.[/red]")
        raise typer.Exit(1)

    d = diagnose(db, profile_id)
    # Deterministic diagnosis first — it works with zero API access.
    diag_md = format_diagnosis_markdown(d)
    console.print(diag_md)

    # No API key: export the prompt for a manual Claude.ai workflow.
    if not cli.config.ANTHROPIC_API_KEY:
        prompt = build_advisor_prompt(d, profile)
        console.print(
            "[yellow]未配置 API key，以上为规则诊断；导出军师 prompt 供 Claude.ai：[/yellow]\n"
        )
        if output:
            Path(output).expanduser().write_text(
                diag_md + "\n\n---\n\n" + prompt, encoding="utf-8"
            )
            console.print(f"[green]已保存: {output}[/green]")
        else:
            console.print(prompt)
        return

    console.print("生成军师建议...")
    try:
        advice = generate_advice(d, profile)
    except AdvisorError as e:
        console.print(f"[red]生成失败: {e}[/red]")
        raise typer.Exit(1)

    console.print()
    console.print(advice)
    if output:
        Path(output).expanduser().write_text(
            diag_md + "\n\n## 军师建议\n\n" + advice, encoding="utf-8"
        )
        console.print(f"[green]已保存: {output}[/green]")


@app.command()
def chat(
    profile_id: int = typer.Option(config.DEFAULT_PROFILE_ID, "--profile", "-p", help="Profile ID"),
    job_id: str = typer.Option("", "--job", "-j", help="围绕某个具体岗位聊（注入 JD+评分）"),
    new: bool = typer.Option(False, "--new", help="开始全新对话（不接续上次历史）"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """实时对话军师：多轮聊天、记得上文，懂你全部求职数据（默认接着上次聊；输入 exit / q 退出）。"""
    _setup_logging(verbose)
    from jobpilot.chat import ChatError, run_chat

    db = cli._get_db()
    try:
        run_chat(
            db,
            profile_id,
            job_id or None,
            resume=not new,
            output_fn=lambda s: console.print(s),
        )
    except ChatError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def plan(
    profile_id: int = typer.Option(config.DEFAULT_PROFILE_ID, "--profile", "-p", help="Profile ID"),
    target: int = typer.Option(0, "--target", "-t", help="本周投递目标数（0=用默认配置）"),
    output: str = typer.Option("", "--output", "-o", help="保存到 Markdown 文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """本周投递计划：列出该投哪几个高分岗 + 哪些投递该跟进（确定性，不烧 API）。"""
    _setup_logging(verbose)
    from jobpilot.planner import build_weekly_plan, format_plan_markdown

    db = cli._get_db()
    weekly_plan = build_weekly_plan(db, profile_id, target=target or None)
    md = format_plan_markdown(weekly_plan)
    console.print(md)
    if output:
        Path(output).expanduser().write_text(md, encoding="utf-8")
        console.print(f"[green]已保存: {output}[/green]")


@app.command()
def ask(
    question: str = typer.Argument(..., help="求职问题，如 '这个 offer 接不接'"),
    job_id: str = typer.Option("", "--job", "-j", help="针对某个具体岗位提问（注入 JD+评分）"),
    profile_id: int = typer.Option(config.DEFAULT_PROFILE_ID, "--profile", "-p", help="Profile ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """求职答疑：结合你的真实处境+偏好回答求职问题（offer/薪资/HR 应对等）。"""
    _setup_logging(verbose)
    from jobpilot.ask import AskError, answer_question, build_ask_prompt, gather_context

    db = cli._get_db()
    profile = db.get_profile(profile_id)
    if not profile:
        console.print("[red]No profile found. Run 'jobpilot resume <file>' first.[/red]")
        raise typer.Exit(1)

    pinned = job_id or None

    # No API key: export the prompt for a manual Claude.ai workflow.
    if not cli.config.ANTHROPIC_API_KEY:
        context = gather_context(db, profile_id, pinned)
        prompt = build_ask_prompt(question, profile, context)
        console.print("[yellow]未配置 API key，导出 prompt 供 Claude.ai 手动使用：[/yellow]\n")
        console.print(prompt)
        return

    console.print("思考中...")
    try:
        answer = answer_question(question, profile, db, pinned)
    except AskError as e:
        console.print(f"[red]回答失败: {e}[/red]")
        raise typer.Exit(1)

    console.print()
    console.print(answer)
