"""Advisory commands: advisor, chat, plan, ask."""

from __future__ import annotations

from pathlib import Path

import typer

from jobpilot import cli, config
from jobpilot.cli import _setup_logging, app, console
from jobpilot.cognitive import format_cognitive_prompt, load_cognitive_profile


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
        prompt = build_advisor_prompt(d, profile, format_cognitive_prompt(load_cognitive_profile()))
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
        prompt = build_ask_prompt(
            question, profile, context, format_cognitive_prompt(load_cognitive_profile())
        )
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


@app.command()
def research(
    query: str = typer.Argument(..., help="要查的资料，如 'AI产品实习面试题'"),
    channel: str = typer.Option("both", "--channel", "-c", help="xhs | web | both"),
    limit: int = typer.Option(12, "--limit", "-l", help="小红书抓取笔记数"),
    output: str = typer.Option("", "--output", "-o", help="保存到 Markdown 文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """军师查资料：按需去小红书 / web 搜面试题、面经、相关帖子（不写进岗位库）。"""
    _setup_logging(verbose)
    from jobpilot.research import research as do_research

    if channel not in ("xhs", "web", "both"):
        console.print(f"[red]未知渠道: {channel}。可选: xhs | web | both[/red]")
        raise typer.Exit(1)

    if channel in ("web", "both") and not cli.config.ANTHROPIC_API_KEY:
        console.print("[yellow]未配置 API key，web 检索跳过（仅小红书可用）。[/yellow]")

    console.print(f"军师查资料: '{query}' (渠道={channel})...")
    results = do_research(query, channel=channel, limit=limit)
    if not results:
        console.print("[yellow]没查到相关资料。换个关键词，或确认 rednote-mcp 已登录。[/yellow]")
        raise typer.Exit(0)

    lines: list[str] = [f"# 资料检索: {query}\n"]
    for i, r in enumerate(results, 1):
        tag = "小红书" if r.source == "xhs" else "web"
        author = f" · {r.author}" if r.author else ""
        lines.append(f"## {i}. [{tag}] {r.title}{author}")
        if r.summary:
            lines.append(r.summary)
        if r.url:
            lines.append(f"链接: {r.url}")
        lines.append("")

    md = "\n".join(lines)
    console.print(md)
    console.print(f"[green]共 {len(results)} 条资料。[/green]")
    if output:
        Path(output).expanduser().write_text(md, encoding="utf-8")
        console.print(f"[green]已保存: {output}[/green]")


@app.command()
def followup(
    profile_id: int = typer.Option(config.DEFAULT_PROFILE_ID, "--profile", "-p", help="Profile ID"),
    done: str = typer.Option("", "--done", help="标记某条承诺为完成（传列表里的 id）"),
    drop: str = typer.Option("", "--drop", help="放弃某条承诺（传列表里的 id）"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """待跟进：军师从 chat 里记下的、你说要做但还没完成的事（投了的自动闭环）。"""
    _setup_logging(verbose)
    from jobpilot import followup as fu
    from jobpilot.followup_store import (
        load_commitments,
        save_commitments,
        update_status,
    )

    if done:
        update_status(profile_id, done, "done")
        console.print(f"[green]已标记完成: {done}[/green]")
        return
    if drop:
        update_status(profile_id, drop, "dropped")
        console.print(f"[yellow]已放弃: {drop}[/yellow]")
        return

    db = cli._get_db()
    commitments = load_commitments(profile_id)
    reconciled, closed = fu.reconcile_with_applications(commitments, db)
    if closed:
        save_commitments(profile_id, reconciled)  # auto-close already-applied

    open_items = [c for c in reconciled if c.status == "open"]
    if not open_items:
        console.print("✅ 没有待跟进的承诺。在 jobpilot chat 里聊到要做的事，军师会自动记下。")
        return

    console.print(f"📌 待跟进（{len(open_items)} 件）：")
    for c in open_items:
        due = f" · {c.due_hint}" if c.due_hint else ""
        job = f" [岗位 {c.job_id}]" if c.job_id else ""
        console.print(f"  [{c.id}] {c.text}{due}{job}")
    if closed:
        console.print(f"\n（已自动闭环 {len(closed)} 件——对应岗位已投递）")
    console.print("\n完成：jobpilot followup --done <id>　放弃：--drop <id>")
