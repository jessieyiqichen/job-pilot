"""Quality / evaluation commands: label, eval."""

from __future__ import annotations

import typer
from rich.table import Table

from jobpilot import cli
from jobpilot.cli import _setup_logging, app, console


@app.command()
def label(
    min_score: float = typer.Option(0.0, "--min-score", "-m", help="只标注 >= 此分的岗位"),
    limit: int = typer.Option(30, "--limit", "-l", help="本次最多标注几个"),
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID"),
    labels_path: str = typer.Option("data/eval_labels.json", "--labels", help="标注文件路径"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """交互式给岗位打标签（想投/不想），用于 eval 与评分校准。"""
    _setup_logging(verbose)
    from jobpilot.eval import read_labels_file, write_labels_file

    db = cli._get_db()
    existing = read_labels_file(labels_path)
    pairs = db.list_scores_with_jobs(profile_id=profile_id, min_score=min_score, limit=500)
    todo = [(s, j) for s, j in pairs if j.job_id not in existing][:limit]

    if not todo:
        console.print("[yellow]没有待标注岗位（可能都标过了，或先 jobpilot score）。[/yellow]")
        return

    console.print(
        f"[bold]逐个标注 {len(todo)} 个岗位[/bold]  "
        "[dim]y=想投 / n=不想 / s=跳过 / q=保存退出[/dim]\n"
    )
    labels = dict(existing)
    added = 0
    for i, (score, job) in enumerate(todo, 1):
        salary = f"{job.salary_min // 1000}-{job.salary_max // 1000}K" if job.salary_max else "面议"
        console.print(
            f"[{i}/{len(todo)}] [bold]{job.title}[/bold] @ {job.company} "
            f"（{job.city}, {salary}）  AI={score.overall_score:.1f}"
        )
        if score.suggestion:
            console.print(f"  [dim]{score.suggestion}[/dim]")
        choice = typer.prompt("  想投?[y/n/s/q]", default="s").strip().lower()
        if choice == "q":
            break
        if choice == "y":
            labels[job.job_id] = 1
            added += 1
        elif choice == "n":
            labels[job.job_id] = 0
            added += 1
        # s or anything else: skip
        console.print()

    write_labels_file(labels, labels_path)
    console.print(
        f"[green]已保存 {len(labels)} 个标签（本次新增 {added}）→ {labels_path}[/green]"
    )
    console.print("[dim]下一步: jobpilot eval 看打分一致性[/dim]")


@app.command(name="eval")
def eval_cmd(
    threshold: float = typer.Option(7.0, "--threshold", "-t", help="判正阈值（AI分>=此值视为推荐）"),
    labels: str = typer.Option(
        "data/eval_labels.json", "--labels", "-l", help="手动标注文件 {job_id: 1|0}"
    ),
    profile_id: int = typer.Option(10, "--profile", "-p", help="Profile ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """评估 AI 打分与你真实判断的一致性（precision/recall/F1）。"""
    _setup_logging(verbose)
    from jobpilot.eval import evaluate, load_labels

    db = cli._get_db()
    label_map = load_labels(db, labels_path=labels or None, profile_id=profile_id)
    if not label_map:
        console.print("[yellow]没有可用标签。两种来源：[/yellow]")
        console.print("  1. 投递记录（applied/offer=想投，rejected=不投）—— 用 jobpilot apply")
        console.print(f"  2. 手动标注文件 {labels}，格式 {{\"<job_id>\": 1, \"<job_id>\": 0}}")
        return

    result = evaluate(db, label_map, threshold=threshold, profile_id=profile_id)
    if result.n == 0:
        console.print("[yellow]标签里的岗位都还没评分，先 jobpilot score。[/yellow]")
        return

    console.print(f"\n[bold]📊 打分一致性评估[/bold]（阈值 >= {threshold}，样本 {result.n}）\n")
    table = Table(show_header=True)
    table.add_column("指标", style="bold")
    table.add_column("值", justify="right")
    table.add_row("Precision（推荐里你真想投的比例）", f"{result.precision:.0%}")
    table.add_row("Recall（你想投的里被推荐的比例）", f"{result.recall:.0%}")
    table.add_row("F1", f"{result.f1:.2f}")
    table.add_row("Accuracy", f"{result.accuracy:.0%}")
    console.print(table)
    console.print(
        f"[dim]混淆矩阵: TP={result.tp} FP={result.fp} FN={result.fn} TN={result.tn}[/dim]"
    )
    if result.precision < 0.6:
        console.print("[yellow]→ Precision 偏低：高分岗里不少你其实不想投，可调高阈值或权重。[/yellow]")
    if result.recall < 0.6:
        console.print("[yellow]→ Recall 偏低：你想投的被漏判，可调低阈值或检查偏好。[/yellow]")
