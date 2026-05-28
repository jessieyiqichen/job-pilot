"""Application-kit commands: tailor, interview, greeting, pdf."""

from __future__ import annotations

from pathlib import Path

import typer

from jobpilot import cli, config
from jobpilot.cli import _setup_logging, app, console
from jobpilot.db import JobPilotDB


@app.command()
def tailor(
    job_id: str = typer.Argument(None, help="Job ID to tailor resume for"),
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID"),
    output: str = typer.Option("", "--output", "-o", help="Output directory"),
    from_text: str = typer.Option("", "--from-text", help="Import tailored text from file (for no-API workflow)"),
    top: int = typer.Option(0, "--top", "-t", help="Batch tailor top N scored jobs"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Tailor your resume for a specific job posting."""
    _setup_logging(verbose)

    db = cli._get_db()
    output_dir = Path(output) if output else None

    if top > 0:
        # Batch tailor mode
        _batch_tailor(db, profile_id, top, output_dir, verbose)
        return

    if not job_id:
        console.print("[red]请指定 job_id 或使用 --top N 批量定制[/red]")
        raise typer.Exit(1)

    if from_text:
        # --from-text mode: only need job, no profile
        from jobpilot.ai.tailor import tailor_from_text

        job = db.get_job(job_id)
        if not job:
            console.print(f"[red]Job not found: {job_id}[/red]")
            raise typer.Exit(1)

        text_path = Path(from_text).expanduser().resolve()
        if not text_path.exists():
            console.print(f"[red]File not found: {text_path}[/red]")
            raise typer.Exit(1)

        text = text_path.read_text(encoding="utf-8")
        console.print(f"Importing tailored text for: [bold]{job.title}[/bold] @ {job.company}...")
        result_path = tailor_from_text(text, job, output_dir)
    else:
        # Standard AI-powered tailor flow (original check order preserved)
        from jobpilot.ai.tailor import save_tailored_resume

        profile = db.get_profile(profile_id)
        if not profile:
            console.print("[red]No profile found. Run 'jobpilot resume <file>' first.[/red]")
            raise typer.Exit(1)

        job = db.get_job(job_id)
        if not job:
            console.print(f"[red]Job not found: {job_id}[/red]")
            raise typer.Exit(1)

        console.print(f"Tailoring resume for: [bold]{job.title}[/bold] @ {job.company}...")
        result_path = save_tailored_resume(profile, job, output_dir)

    db.update_job_status(job_id, "tailored")
    console.print(f"[green]Tailored resume saved: {result_path}[/green]")
    console.print(f"[green]Job status updated to 'tailored'[/green]")
    console.print("[dim]下一步: jobpilot apply 选择岗位投递[/dim]")


def _batch_tailor(
    db: JobPilotDB,
    profile_id: int,
    top_n: int,
    output_dir: Path | None,
    verbose: bool,
) -> None:
    """Batch tailor top N scored but untailored jobs."""
    import time

    from jobpilot.ai.tailor import save_tailored_resume

    profile = db.get_profile(profile_id)
    if not profile:
        console.print("[red]No profile found. Run 'jobpilot resume <file>' first.[/red]")
        raise typer.Exit(1)

    candidates = db.list_top_untailored(profile_id, limit=top_n)
    if not candidates:
        console.print("[yellow]没有待定制的已评分岗位。[/yellow]")
        return

    console.print(f"批量定制 {len(candidates)} 个岗位简历...\n")
    success = 0
    for i, (score_obj, job) in enumerate(candidates, 1):
        console.print(
            f"[{i}/{len(candidates)}] {job.company} - {job.title} "
            f"(score: {score_obj.overall_score:.1f})...",
            end=" ",
        )
        try:
            save_tailored_resume(profile, job, output_dir)
            db.update_job_status(job.job_id, "tailored")
            console.print("[green]OK[/green]")
            success += 1
            if i < len(candidates) and cli.config.ANTHROPIC_API_KEY:
                time.sleep(1)
        except Exception as e:
            console.print(f"[red]FAIL: {e}[/red]")

    console.print(f"\n[green]完成: {success}/{len(candidates)} 份简历已定制[/green]")
    console.print("[dim]下一步: jobpilot apply 选择岗位投递[/dim]")


@app.command()
def interview(
    job_id: str = typer.Argument(..., help="Job ID 或数字 id"),
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID"),
    output: str = typer.Option("", "--output", "-o", help="保存到 Markdown 文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """为指定岗位生成面试准备（大概率问题 + 对标简历的 STAR 要点）。"""
    _setup_logging(verbose)
    from jobpilot.ai.interview import (
        InterviewPrepError,
        build_interview_prompt,
        format_markdown,
        generate_interview_prep,
    )

    db = cli._get_db()
    profile = db.get_profile(profile_id)
    if not profile:
        console.print("[red]No profile found. Run 'jobpilot resume <file>' first.[/red]")
        raise typer.Exit(1)

    job = db.get_job(job_id)
    if not job:
        console.print(f"[red]Job not found: {job_id}[/red]")
        raise typer.Exit(1)

    score = db.get_score(job_id)

    # No API key: export the prompt for a manual Claude.ai workflow.
    if not cli.config.ANTHROPIC_API_KEY:
        prompt = build_interview_prompt(profile, job, score)
        console.print("[yellow]未配置 API key，导出 prompt 供 Claude.ai 手动使用：[/yellow]\n")
        if output:
            Path(output).expanduser().write_text(prompt, encoding="utf-8")
            console.print(f"[green]Prompt 已保存: {output}[/green]")
        else:
            console.print(prompt)
        return

    console.print(f"为 [bold]{job.title}[/bold] @ {job.company} 生成面试准备...")
    try:
        prep = generate_interview_prep(profile, job, score)
    except InterviewPrepError as e:
        console.print(f"[red]生成失败: {e}[/red]")
        raise typer.Exit(1)

    md = format_markdown(prep)
    console.print()
    console.print(md)
    if output:
        Path(output).expanduser().write_text(md, encoding="utf-8")
        console.print(f"[green]已保存: {output}[/green]")


@app.command()
def greeting(
    job_id: str = typer.Argument(..., help="Job ID"),
    channel: str = typer.Option("boss", "--channel", "-c", help="渠道: boss / xhs / email"),
    output: str = typer.Option("", "--output", "-o", help="保存到文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """为指定岗位生成渠道差异化打招呼话术（boss/xhs/email；你来发，不自动触达）。"""
    _setup_logging(verbose)
    from jobpilot.ai.greeting import (
        GreetingError,
        check_style_violations,
        generate_greeting,
        interaction_tips,
    )

    db = cli._get_db()
    job = db.get_job(job_id)
    if not job:
        console.print(f"[red]Job not found: {job_id}[/red]")
        raise typer.Exit(1)
    score = db.get_score(job_id)

    console.print(f"为 [bold]{job.title}[/bold] @ {job.company} 生成 [{channel}] 话术...\n")
    try:
        result = generate_greeting(job, score, channel=channel)
    except GreetingError as e:
        console.print(f"[red]生成失败: {e}[/red]")
        raise typer.Exit(1)

    if result.subject:
        console.print(f"[bold cyan]主题：{result.subject}[/bold cyan]\n")
    console.print(f"[green]{result.body}[/green]\n")
    if result.attachment_note:
        console.print(f"[blue]↳ 发完紧跟简历截图，配文：{result.attachment_note}[/blue]\n")

    console.print(f"[dim]字数: {len(result.body)}[/dim]")
    violations = check_style_violations(result.body, job.jd_text or "")
    if violations:
        console.print("[yellow]风格自检（建议手改）: " + "; ".join(violations) + "[/yellow]")

    tips = interaction_tips()
    if tips:
        console.print("\n[bold]HR 互动规则[/bold]")
        for t in tips:
            console.print(f"  · {t}")

    if output:
        Path(output).expanduser().write_text(result.save_text(), encoding="utf-8")
        console.print(f"\n[dim]已保存: {output}[/dim]")
    console.print("[dim]复制后到平台手动发给 HR（JobPilot 不自动触达招聘方）[/dim]")


@app.command()
def pdf(
    md_path: str = typer.Argument(..., help="Path to Markdown resume"),
    output: str = typer.Option("", "--output", "-o", help="Output PDF path"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Convert a Markdown resume to PDF."""
    _setup_logging(verbose)

    md_file = Path(md_path).expanduser().resolve()
    if not md_file.exists():
        console.print(f"[red]File not found: {md_file}[/red]")
        raise typer.Exit(1)

    output_path = Path(output).expanduser().resolve() if output else None

    try:
        from jobpilot.resume.generator import markdown_to_pdf

        result_path = markdown_to_pdf(md_file, output_path)
        console.print(f"[green]PDF generated: {result_path}[/green]")
    except ImportError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def voice(
    text: str = typer.Argument("", help="一段你的真实文字（话术/文案），作为语言风格样本"),
    file: str = typer.Option("", "--file", "-f", help="从文件读入样本"),
    revised: bool = typer.Option(False, "--revised", help="标记为「改后回灌」样本（你改完话术后回灌）"),
    profile_id: int = typer.Option(config.DEFAULT_PROFILE_ID, "--profile", "-p", help="Profile ID"),
    list_only: bool = typer.Option(False, "--list", "-l", help="列出已有样本"),
) -> None:
    """语言风格样本：军师生成话术时会模仿这些你的真实文字，让你少改。

    冷启动先贴几段你满意的话术；以后改完话术用 --revised 回灌，越用越像你。
    """
    from jobpilot.voice import VoiceSample, add_sample, load_samples

    if list_only or (not text and not file):
        samples = load_samples(profile_id)
        if not samples:
            console.print(
                '还没有语言样本。用 jobpilot voice "<你的真实话术>" 加几段，'
                "军师生成话术时就会学你的语气。"
            )
            return
        console.print(f"语言样本（{len(samples)} 条）：")
        for i, s in enumerate(samples, 1):
            preview = s.text[:60] + ("…" if len(s.text) > 60 else "")
            console.print(f"  {i}. [{s.source}] {preview}")
        return

    content = text
    if file:
        content = Path(file).expanduser().read_text(encoding="utf-8").strip()
    if not content:
        console.print("[red]样本内容为空。[/red]")
        raise typer.Exit(1)

    sample = VoiceSample.new(content, source="revised" if revised else "manual")
    if add_sample(profile_id, sample):
        console.print(f"[green]已加入语言样本（{sample.source}）。下次生成话术会模仿你的语气。[/green]")
    else:
        console.print("[yellow]这段样本已存在，跳过。[/yellow]")
