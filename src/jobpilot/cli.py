"""JobPilot CLI — typer-based command-line interface."""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from jobpilot import __version__, config
from jobpilot.db import JobPilotDB

app = typer.Typer(
    name="jobpilot",
    help="JobPilot — AI-powered job hunting assistant",
    no_args_is_help=True,
)
console = Console()


def _get_db() -> JobPilotDB:
    return JobPilotDB()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def setup(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Interactive preference questionnaire — configure job matching preferences."""
    _setup_logging(verbose)
    from rich.panel import Panel

    from jobpilot.setup import load_existing_preferences, run_questionnaire, save_preferences

    existing = load_existing_preferences()
    if existing:
        console.print("[yellow]已有偏好配置。重新运行将更新（不会丢失其他字段）。[/yellow]")
        if not typer.confirm("继续？", default=True):
            raise typer.Exit(0)

    console.print(Panel(
        "[bold]回答以下问题帮助我们了解你的求职偏好[/bold]\n完成后将自动更新评分配置",
        title="JobPilot 求职偏好设置",
        border_style="cyan",
    ))

    preferences = run_questionnaire()
    cfg_path = save_preferences(preferences)

    # Print summary table
    console.print()
    table = Table(title="偏好设置摘要")
    table.add_column("配置项", style="bold")
    table.add_column("值")

    for key, value in preferences.items():
        display_val = ", ".join(value) if isinstance(value, list) else str(value)
        table.add_row(key, display_val)

    console.print(table)
    console.print(f"\n[green]偏好已保存到: {cfg_path}[/green]")
    console.print("[dim]提示: 运行 jobpilot score 重新评分已有岗位[/dim]")


@app.command()
def resume(
    path: str = typer.Argument(..., help="Path to resume file (PDF/DOCX/MD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Parse a resume and store the structured profile."""
    _setup_logging(verbose)
    from jobpilot.ai.parser import parse_resume

    resume_path = Path(path).expanduser().resolve()
    if not resume_path.exists():
        console.print(f"[red]File not found: {resume_path}[/red]")
        raise typer.Exit(1)

    console.print(f"Parsing resume: {resume_path.name}...")
    profile = parse_resume(resume_path)

    db = _get_db()
    profile_id = db.upsert_profile(profile)
    console.print(f"[green]Profile saved (id={profile_id}): {profile.name}[/green]")

    # Show structured data summary
    s = profile.structured
    if s:
        console.print(f"\n  Name: {s.get('name', 'N/A')}")
        console.print(f"  Title: {s.get('title', 'N/A')}")
        console.print(f"  Experience: {s.get('years_of_experience', 'N/A')} years")
        skills = s.get("skills", {})
        all_skills = []
        for v in skills.values():
            if isinstance(v, list):
                all_skills.extend(v)
        if all_skills:
            console.print(f"  Skills: {', '.join(all_skills[:15])}")
        edu = s.get("education", [])
        if edu:
            latest = edu[0]
            console.print(
                f"  Education: {latest.get('school', '')} "
                f"({latest.get('degree', '')}, {latest.get('major', '')})"
            )


@app.command()
def search(
    query: str = typer.Argument(..., help="Search keywords (e.g. 'Python开发')"),
    city: str = typer.Option(config.DEFAULT_CITY, "--city", "-c"),
    experience: str = typer.Option("", "--experience", "-e", help="e.g. '3-5年'"),
    salary: str = typer.Option("", "--salary", "-s", help="e.g. '15-25K'"),
    platform: str = typer.Option(config.DEFAULT_PLATFORM, "--platform", "-p"),
    score: bool = typer.Option(False, "--score", help="Auto-score results"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Search for jobs on recruitment platforms."""
    _setup_logging(verbose)
    from jobpilot.adapters.base import SearchFilters
    from jobpilot.adapters.boss import BossAdapter
    from jobpilot.adapters.websearch import WebSearchAdapter
    from jobpilot.adapters.xhs_search import XHSSearchAdapter

    adapters = {"boss": BossAdapter, "websearch": WebSearchAdapter, "xhs": XHSSearchAdapter}
    adapter_cls = adapters.get(platform)
    if not adapter_cls:
        console.print(f"[red]Unknown platform: {platform}. Available: {list(adapters.keys())}[/red]")
        raise typer.Exit(1)

    adapter = adapter_cls()
    filters = SearchFilters(city=city, experience=experience, salary_range=salary)

    # Auto-append job_type keyword if not already in query
    from jobpilot.ai.scorer import _load_preferences

    _prefs = _load_preferences()
    _job_type = _prefs.get("job_type", "")
    if _job_type:
        _JT_KW_MAP = {"实习": "实习", "全职": "全职", "兼职/自由职业": "兼职"}
        _kw = _JT_KW_MAP.get(_job_type, "")
        if _kw and _kw not in query and "intern" not in query.lower():
            query = f"{query} {_kw}"
            console.print(f"[dim]自动追加关键词: {_kw}（偏好: {_job_type}）[/dim]")

    console.print(f"Searching '{query}' on {platform} (city={city})...")
    jobs = adapter.search(query, filters)

    # Fallback: use web search when boss returns too few results
    if len(jobs) < config.WEBSEARCH_FALLBACK_THRESHOLD and platform != "websearch":
        if config.ANTHROPIC_API_KEY:
            console.print("[yellow]Boss 结果较少，启动 web 搜索...[/yellow]")
            web_adapter = WebSearchAdapter()
            web_jobs = web_adapter.search(query, filters)
            jobs.extend(web_jobs)
            console.print(f"[green]Web 搜索补充 {len(web_jobs)} 条岗位[/green]")

    if not jobs:
        console.print("[yellow]No jobs found.[/yellow]")
        raise typer.Exit(0)

    db = _get_db()
    count = db.upsert_jobs(jobs)
    console.print(f"[green]Found {count} jobs, saved to database.[/green]\n")

    # Display results
    table = Table(title=f"Search Results: {query}")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Title", style="bold")
    table.add_column("Company")
    table.add_column("Salary")
    table.add_column("City")
    table.add_column("Exp")

    for job in jobs:
        salary_str = (
            f"{job.salary_min // 1000}-{job.salary_max // 1000}K"
            if job.salary_max
            else "面议"
        )
        table.add_row(
            job.job_id[:12],
            job.title,
            job.company,
            salary_str,
            job.city,
            job.experience,
        )

    console.print(table)

    # Auto-score if requested
    if score:
        _do_score(db, verbose)


@app.command()
def score(
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID to match against"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max jobs to score"),
    heuristic: bool = typer.Option(False, "--heuristic", help="强制启发式评分（跳过 API，免费秒评）"),
    refine: int = typer.Option(0, "--refine", "-r", help="对已评分 top N 岗位用 API 精评"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """AI-score unscored jobs against your profile."""
    _setup_logging(verbose)
    db = _get_db()
    _do_score(db, verbose, profile_id, limit, heuristic=heuristic, refine=refine)


def _do_score(
    db: JobPilotDB,
    verbose: bool = False,
    profile_id: int = 1,
    limit: int = 50,
    *,
    heuristic: bool = False,
    refine: int = 0,
) -> None:
    """Internal scoring logic shared by search --score and score command."""
    from jobpilot.ai.scorer import score_jobs

    profile = db.get_profile(profile_id)
    if not profile:
        console.print("[red]No profile found. Run 'jobpilot resume <file>' first.[/red]")
        raise typer.Exit(1)

    if refine > 0:
        # Refine mode: re-score top N already-scored jobs with API
        scored_pairs = db.list_scores_with_jobs(profile_id=profile_id, limit=refine)
        if not scored_pairs:
            console.print("[yellow]没有已评分岗位可精评。先运行 jobpilot score --heuristic[/yellow]")
            return
        jobs_to_refine = [job for _, job in scored_pairs]
        console.print(f"对 top {len(jobs_to_refine)} 岗位用 API 精评...")
        scores = score_jobs(profile, jobs_to_refine, force_heuristic=False)
        for s in scores:
            db.upsert_score(s)
        console.print(f"[green]精评完成: {len(scores)} 个岗位已更新。[/green]\n")
    else:
        # Default mode: score unscored jobs
        new_jobs = db.list_jobs(status="new", limit=limit)
        if not new_jobs:
            console.print("[yellow]No unscored jobs found.[/yellow]")
            return

        mode_label = "启发式" if heuristic else "AI"
        console.print(f"[{mode_label}] Scoring {len(new_jobs)} jobs against profile '{profile.name}'...")
        scores = score_jobs(profile, new_jobs, force_heuristic=heuristic)

        # Save scores and update status
        for s in scores:
            db.upsert_score(s)
            db.update_job_status(s.job_id, "scored")

        console.print(f"[green]Scored {len(scores)} jobs.[/green]\n")

    # Display top results
    table = Table(title="Top Matches")
    table.add_column("Score", justify="center")
    table.add_column("Title", style="bold")
    table.add_column("Company")
    table.add_column("Skills", style="dim")
    table.add_column("Suggestion", max_width=40)

    for s in scores[:10]:
        job = db.get_job(s.job_id)
        color = "green" if s.overall_score >= 7 else "yellow" if s.overall_score >= 5 else "red"
        table.add_row(
            f"[{color}]{s.overall_score:.1f}[/{color}]",
            job.title if job else s.job_id,
            job.company if job else "",
            f"{s.skill_match:.1f}",
            s.suggestion[:40] + "..." if len(s.suggestion) > 40 else s.suggestion,
        )

    console.print(table)


@app.command(name="list")
def list_jobs(
    status: str = typer.Option("", "--status", "-s", help="Filter by status"),
    min_score: float = typer.Option(0.0, "--min-score", "-m", help="Minimum score"),
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID for score filtering"),
    limit: int = typer.Option(20, "--limit", "-l"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """List jobs with their scores."""
    _setup_logging(verbose)
    db = _get_db()

    if min_score > 0:
        results = db.list_scores_with_jobs(profile_id=profile_id, min_score=min_score, limit=limit)
        table = Table(title=f"Jobs (score >= {min_score})")
        table.add_column("Score", justify="center")
        table.add_column("Title", style="bold")
        table.add_column("Company")
        table.add_column("City")
        table.add_column("Salary")
        table.add_column("Status")

        for score_obj, job in results:
            salary = f"{job.salary_min // 1000}-{job.salary_max // 1000}K" if job.salary_max else "面议"
            color = "green" if score_obj.overall_score >= 7 else "yellow"
            table.add_row(
                f"[{color}]{score_obj.overall_score:.1f}[/{color}]",
                job.title,
                job.company,
                job.city,
                salary,
                job.status,
            )
        console.print(table)
    else:
        jobs = db.list_jobs(status=status or None, limit=limit)
        table = Table(title="Jobs")
        table.add_column("ID", style="dim", max_width=12)
        table.add_column("Title", style="bold")
        table.add_column("Company")
        table.add_column("City")
        table.add_column("Status")

        for job in jobs:
            table.add_row(job.job_id[:12], job.title, job.company, job.city, job.status)
        console.print(table)


@app.command()
def detail(
    job_id: str = typer.Argument(..., help="Job ID to show details for"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Show detailed info for a specific job."""
    _setup_logging(verbose)
    db = _get_db()

    job = db.get_job(job_id)
    if not job:
        console.print(f"[red]Job not found: {job_id}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]{job.title}[/bold] @ {job.company}")
    console.print(f"  City: {job.city}")
    salary = f"{job.salary_min // 1000}-{job.salary_max // 1000}K" if job.salary_max else "面议"
    console.print(f"  Salary: {salary}")
    console.print(f"  Experience: {job.experience}")
    console.print(f"  Education: {job.education}")
    console.print(f"  Status: {job.status}")
    console.print(f"  Platform: {job.platform}")
    console.print(f"  Discovered: {job.discovered_at}")
    console.print(f"\n[bold]Job Description:[/bold]")
    console.print(job.jd_text or "(no JD available)")

    score_obj = db.get_score(job_id)
    if score_obj:
        console.print(f"\n[bold]AI Score:[/bold] {score_obj.overall_score:.1f}/10")
        console.print(f"  Skill Match: {score_obj.skill_match:.1f}")
        console.print(f"  Experience Match: {score_obj.experience_match:.1f}")
        console.print(f"  Salary Match: {score_obj.salary_match:.1f}")
        if score_obj.highlights:
            console.print(f"\n  [green]Highlights:[/green]")
            for h in score_obj.highlights:
                console.print(f"    + {h}")
        if score_obj.concerns:
            console.print(f"\n  [yellow]Concerns:[/yellow]")
            for c in score_obj.concerns:
                console.print(f"    - {c}")
        if score_obj.suggestion:
            console.print(f"\n  [blue]Suggestion:[/blue] {score_obj.suggestion}")


@app.command()
def status(
    job_id: str = typer.Argument(..., help="Job ID"),
    new_status: str = typer.Argument(..., help="New status"),
    notes: str = typer.Option("", "--notes", "-n", help="Add notes"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Update application status for a job."""
    _setup_logging(verbose)
    from jobpilot.tracker import TrackerError, update_status

    db = _get_db()
    try:
        app_record = update_status(db, job_id, new_status, notes)
        console.print(
            f"[green]Updated: {job_id} → {app_record.status}[/green]"
        )
    except TrackerError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


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

    db = _get_db()
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
            if i < len(candidates) and config.ANTHROPIC_API_KEY:
                time.sleep(1)
        except Exception as e:
            console.print(f"[red]FAIL: {e}[/red]")

    console.print(f"\n[green]完成: {success}/{len(candidates)} 份简历已定制[/green]")
    console.print("[dim]下一步: jobpilot apply 选择岗位投递[/dim]")


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

    db = _get_db()
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

    db = _get_db()

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
    )

    console.print(
        f"[bold]🚀 全流程自动化[/bold]  关键词={list(cfg.keywords)} "
        f"渠道={list(cfg.platforms)} 城市={cfg.city or '默认'}\n"
    )

    db = _get_db()
    result = run_pipeline(db, cfg, progress=lambda msg: console.print(f"[dim]{msg}[/dim]"))

    console.print("\n[bold]运行结果[/bold]")
    for st in result.stages:
        mark = "[green]✓[/green]" if st.ok else "[red]✗[/red]"
        console.print(f"  {mark} {st.name}: {st.detail}")

    console.print(
        f"\n[bold]汇总[/bold]  入库 {result.found} · 秒评 {result.scored} · "
        f"精评 {result.refined} · 定制 {result.tailored} 份简历"
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

    db = _get_db()
    subject, body = generate_digest(db, profile_id)
    console.print(f"[bold]{subject}[/bold]\n")
    console.print(body)
    if email:
        console.print()
        _send_digest_email(db, profile_id)


@app.command(name="import-xhs")
def import_xhs(
    json_file: str = typer.Argument(..., help="Path to JSON file with XHS job data"),
    score: bool = typer.Option(False, "--score", help="Auto-score imported jobs"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Import jobs from XHS (小红书) favorites JSON file."""
    import json

    _setup_logging(verbose)
    from jobpilot.adapters.xhs import parse_xhs_jobs

    file_path = Path(json_file).expanduser().resolve()
    if not file_path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1)

    if not isinstance(data, list):
        console.print("[red]JSON file must contain an array of job objects.[/red]")
        raise typer.Exit(1)

    jobs = parse_xhs_jobs(data)
    if not jobs:
        console.print("[yellow]No valid job entries found in JSON.[/yellow]")
        raise typer.Exit(0)

    db = _get_db()
    count = db.upsert_jobs(jobs)
    console.print(f"[green]Imported {count} jobs from XHS.[/green]\n")

    # Display results
    table = Table(title="XHS Imported Jobs")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Title", style="bold")
    table.add_column("Company")
    table.add_column("Salary")
    table.add_column("City")

    for job in jobs:
        salary_str = (
            f"{job.salary_min // 1000}-{job.salary_max // 1000}K"
            if job.salary_max
            else "面议"
        )
        table.add_row(
            job.job_id[:12],
            job.title,
            job.company,
            salary_str,
            job.city,
        )

    console.print(table)

    if score:
        _do_score(db, verbose)


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
def report(
    output: str = typer.Option("", "--output", "-o", help="Output file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Generate a daily report."""
    _setup_logging(verbose)
    from jobpilot.report import generate_daily_report, save_report

    db = _get_db()

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
    db = _get_db()
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


@app.command()
def version() -> None:
    """Show version."""
    console.print(f"JobPilot v{__version__}")


if __name__ == "__main__":
    app()
