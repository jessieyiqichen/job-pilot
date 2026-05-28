"""Pipeline & reporting commands: apply, pipeline, pipeline-all, digest, report, stats."""

from __future__ import annotations

import typer
from rich.table import Table

from jobpilot import cli, config
from jobpilot.cli import _setup_logging, app, console
from jobpilot.db import JobPilotDB


@app.command()
def apply(
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID"),
    min_score: float = typer.Option(7.0, "--min-score", "-m", help="Minimum score"),
    limit: int = typer.Option(15, "--limit", "-l", help="Max jobs to show"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Select high-scored jobs to mark as applied."""
    _setup_logging(verbose)
    from jobpilot.tracker import TrackerError, update_status

    db = cli._get_db()
    candidates = db.list_top_scored_jobs(
        profile_id=profile_id, min_score=min_score, limit=limit,
    )

    if not candidates:
        console.print("[yellow]没有符合条件的岗位。先运行 jobpilot score 评分。[/yellow]")
        return

    # Display candidates
    table = Table(title="可投递岗位")
    table.add_column("#", justify="right", style="bold")
    table.add_column("Score", justify="center")
    table.add_column("Title", style="bold")
    table.add_column("Company")
    table.add_column("City")
    table.add_column("Salary")
    table.add_column("Status")

    for idx, (score_obj, job) in enumerate(candidates, 1):
        salary = (
            f"{job.salary_min // 1000}-{job.salary_max // 1000}K"
            if job.salary_max else "面议"
        )
        color = "green" if score_obj.overall_score >= 8 else "yellow"
        table.add_row(
            str(idx),
            f"[{color}]{score_obj.overall_score:.1f}[/{color}]",
            job.title,
            job.company,
            job.city,
            salary,
            job.status,
        )

    console.print(table)

    # Interactive selection
    selection = typer.prompt(
        "选择编号（逗号分隔，q 退出）", default="q"
    )

    if selection.strip().lower() == "q":
        console.print("[dim]已退出[/dim]")
        return

    # Parse selected indices
    selected_indices: list[int] = []
    for part in selection.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part)
            if 1 <= idx <= len(candidates):
                selected_indices.append(idx)
            else:
                console.print(f"[yellow]忽略无效编号: {part}[/yellow]")
        elif part:
            console.print(f"[yellow]忽略无效输入: {part}[/yellow]")

    if not selected_indices:
        console.print("[yellow]未选择任何岗位[/yellow]")
        return

    # Mark selected as applied
    applied_count = 0
    for idx in selected_indices:
        score_obj, job = candidates[idx - 1]
        try:
            update_status(db, job.job_id, "applied")
            console.print(f"  [green]✓ {job.company} - {job.title}[/green]")
            applied_count += 1
        except TrackerError as e:
            console.print(f"  [red]✗ {job.company} - {job.title}: {e}[/red]")

    console.print(f"\n[green]已标记 {applied_count} 个岗位为「已投递」[/green]")


@app.command()
def pipeline(
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Show application pipeline funnel."""
    _setup_logging(verbose)

    db = cli._get_db()

    # Gather counts
    total = db.count_jobs()
    scored_count = db.count_jobs(status="scored")
    tailored_count = db.count_jobs(status="tailored")

    # Count from applications table for later stages
    applied_apps = db.list_applications(status="applied")
    interview_apps = db.list_applications(status="interview")
    offer_apps = db.list_applications(status="offer")
    rejected_apps = db.list_applications(status="rejected")
    replied_apps = db.list_applications(status="replied")

    # High-score count
    high_scores = db.list_scores(profile_id=profile_id, min_score=7.0, limit=9999)
    high_score_count = len(high_scores)

    stages = [
        ("搜索", total),
        ("高分(>=7)", high_score_count),
        ("已评分", scored_count),
        ("已定制", tailored_count),
        ("已投递", len(applied_apps)),
        ("已回复", len(replied_apps)),
        ("面试中", len(interview_apps)),
        ("Offer", len(offer_apps)),
        ("已拒绝", len(rejected_apps)),
    ]

    max_count = max((c for _, c in stages), default=1) or 1
    max_bar = 20

    console.print("\n[bold]📊 求职漏斗[/bold]\n")
    for label, count in stages:
        bar_len = int(count / max_count * max_bar) if max_count > 0 else 0
        bar = "█" * bar_len
        console.print(f"  {label:<10} {bar:<{max_bar}}  {count}")
    console.print()


@app.command(name="pipeline-all")
def pipeline_all(
    keywords: str = typer.Option(
        "", "--keywords", "-k", help="逗号分隔搜索关键词；留空则用偏好的 career_track"
    ),
    city: str = typer.Option(config.DEFAULT_CITY, "--city", "-c"),
    platforms: str = typer.Option(
        "websearch,xhs", "--platforms", help="逗号分隔搜索渠道"
    ),
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID"),
    refine_top: int = typer.Option(20, "--refine", "-r", help="API 精评 top N（0=跳过）"),
    tailor_top: int = typer.Option(5, "--tailor", "-t", help="自动定制 top N 简历（0=跳过）"),
    greeting_top: int = typer.Option(5, "--greeting", "-g", help="生成 top N 打招呼话术（0=跳过）"),
    email: bool = typer.Option(False, "--email", help="跑完把 digest 发邮件（需配置 SMTP）"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """一条命令跑全流程：搜索 → 打分 → 定制简历 → 日报（投递留人工）。"""
    _setup_logging(verbose)
    from jobpilot.ai.scorer import _load_preferences
    from jobpilot.pipeline import build_config, run_pipeline

    prefs = _load_preferences()
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()] or None
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]

    cfg = build_config(
        prefs,
        keywords=kw_list,
        city=city,
        platforms=platform_list,
        profile_id=profile_id,
        refine_top=refine_top,
        tailor_top=tailor_top,
        greeting_top=greeting_top,
    )

    console.print(
        f"[bold]🚀 全流程自动化[/bold]  关键词={list(cfg.keywords)} "
        f"渠道={list(cfg.platforms)} 城市={cfg.city or '默认'}\n"
    )

    db = cli._get_db()
    result = run_pipeline(db, cfg, progress=lambda msg: console.print(f"[dim]{msg}[/dim]"))

    console.print("\n[bold]运行结果[/bold]")
    for st in result.stages:
        mark = "[green]✓[/green]" if st.ok else "[red]✗[/red]"
        console.print(f"  {mark} {st.name}: {st.detail}")

    console.print(
        f"\n[bold]汇总[/bold]  入库 {result.found} · 秒评 {result.scored} · "
        f"精评 {result.refined} · 定制 {result.tailored} 份简历 · 打招呼 {result.greeted} 条"
    )
    if result.report_path:
        console.print(f"[green]日报: {result.report_path}[/green]")

    if email:
        _send_digest_email(db, profile_id)

    console.print("[dim]下一步: jobpilot list --min-score 7 查看高分岗 → jobpilot apply 投递[/dim]")


def _send_digest_email(db: JobPilotDB, profile_id: int) -> None:
    """Generate the digest and email it; report outcome to console."""
    from jobpilot import notify
    from jobpilot.report import generate_digest

    subject, body = generate_digest(db, profile_id)
    try:
        recipient = notify.send_email(subject, body)
        console.print(f"[green]✉️  digest 已发送至 {recipient}[/green]")
    except notify.EmailNotConfigured as e:
        console.print(f"[yellow]未发邮件: {e}[/yellow]")
    except Exception as e:  # noqa: BLE001 - surface SMTP failure without crashing
        console.print(f"[red]邮件发送失败: {e}[/red]")


@app.command()
def digest(
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID"),
    email: bool = typer.Option(False, "--email", help="发邮件（否则仅终端预览）"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """预览/发送每日 digest（新增高分岗 + 待跟进投递）。"""
    _setup_logging(verbose)
    from jobpilot.report import generate_digest

    db = cli._get_db()
    subject, body = generate_digest(db, profile_id)
    console.print(f"[bold]{subject}[/bold]\n")
    console.print(body)
    if email:
        console.print()
        _send_digest_email(db, profile_id)


@app.command()
def report(
    output: str = typer.Option("", "--output", "-o", help="Output file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Generate a daily report."""
    _setup_logging(verbose)
    from jobpilot.report import generate_daily_report, save_report

    db = cli._get_db()

    if output:
        path = save_report(db, output)
        console.print(f"[green]Report saved to {path}[/green]")
    else:
        md = generate_daily_report(db)
        console.print(md)


@app.command()
def stats(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Show database statistics."""
    _setup_logging(verbose)
    db = cli._get_db()
    s = db.get_stats()

    table = Table(title="JobPilot Stats")
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    table.add_row("Profiles", str(s["profiles"]))
    table.add_row("Jobs (total)", str(s["jobs_total"]))
    table.add_row("Jobs (new)", str(s["jobs_new"]))
    table.add_row("Jobs (scored)", str(s["jobs_scored"]))
    table.add_row("Scores", str(s["scores"]))
    table.add_row("Applications", str(s["applications"]))
    table.add_row("Avg Score", str(s["avg_score"]))

    console.print(table)
