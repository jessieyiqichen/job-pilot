"""Discovery commands: setup, resume, search, score, list, detail, status, import-xhs."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from jobpilot import cli, config
from jobpilot.cli import _setup_logging, app, console
from jobpilot.db import JobPilotDB

# ``_get_db``, ``config`` and ``_do_score`` are referenced through the ``cli``
# module (not bound at import time) so that test patches targeting
# ``jobpilot.cli.<name>`` and ``jobpilot.cli.config`` reach this module.


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

    db = cli._get_db()
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
    from jobpilot.adapters.github_jobs import GitHubAdapter
    from jobpilot.adapters.linkedin_jobspy import LinkedInJobSpyAdapter
    from jobpilot.adapters.websearch import WebSearchAdapter
    from jobpilot.adapters.xhs_search import XHSSearchAdapter

    adapters = {
        "boss": BossAdapter,
        "websearch": WebSearchAdapter,
        "xhs": XHSSearchAdapter,
        "github": GitHubAdapter,
        "linkedin": LinkedInJobSpyAdapter,
    }
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
    if len(jobs) < cli.config.WEBSEARCH_FALLBACK_THRESHOLD and platform != "websearch":
        if cli.config.ANTHROPIC_API_KEY:
            console.print("[yellow]Boss 结果较少，启动 web 搜索...[/yellow]")
            web_adapter = WebSearchAdapter()
            web_jobs = web_adapter.search(query, filters)
            jobs.extend(web_jobs)
            console.print(f"[green]Web 搜索补充 {len(web_jobs)} 条岗位[/green]")

    if not jobs:
        console.print("[yellow]No jobs found.[/yellow]")
        raise typer.Exit(0)

    db = cli._get_db()
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
        cli._do_score(db, verbose)


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
    db = cli._get_db()
    cli._do_score(db, verbose, profile_id, limit, heuristic=heuristic, refine=refine)


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
    db = cli._get_db()

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
    db = cli._get_db()

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

    db = cli._get_db()
    try:
        app_record = update_status(db, job_id, new_status, notes)
        console.print(
            f"[green]Updated: {job_id} → {app_record.status}[/green]"
        )
    except TrackerError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


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

    db = cli._get_db()
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
        cli._do_score(db, verbose)
