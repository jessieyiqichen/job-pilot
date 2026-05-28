"""End-to-end automation pipeline: 搜索 → 打分 → 定制简历 → 日报.

`jobpilot pipeline-all` 一条命令跑完整条链路。设计目标是"我喊一句就跑全流程"：

- 每个 stage 独立 try/except，单点失败（如 XHS cookies 过期）不会拖垮整条链路。
- 搜索默认走 WebSearch + XHS 两个渠道，关键词从偏好的 career_track 派生。
- 打分先 heuristic 秒评全部 new 岗位，再对 top N 用 API 精评。
- 定制简历对高分未定制岗位批量生成 .docx。
- **不做投递**：投递不可逆，留人工确认（命令结束提示 jobpilot apply）。
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from jobpilot import config
from jobpilot.db import JobPilotDB

logger = logging.getLogger(__name__)

DEFAULT_PLATFORMS: tuple[str, ...] = ("websearch", "xhs")
DEFAULT_REFINE_TOP = 20
DEFAULT_TAILOR_TOP = 5
DEFAULT_GREETING_TOP = 5
DEFAULT_PROFILE_ID = 10
_FALLBACK_KEYWORD = "AI产品经理"


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable configuration for a single pipeline run."""

    keywords: tuple[str, ...]
    platforms: tuple[str, ...] = DEFAULT_PLATFORMS
    city: str = ""
    profile_id: int = DEFAULT_PROFILE_ID
    refine_top: int = DEFAULT_REFINE_TOP
    tailor_top: int = DEFAULT_TAILOR_TOP
    greeting_top: int = DEFAULT_GREETING_TOP


@dataclass(frozen=True)
class StageResult:
    """Outcome of one pipeline stage."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PipelineResult:
    """Aggregated outcome of a full pipeline run."""

    stages: tuple[StageResult, ...] = field(default_factory=tuple)
    found: int = 0
    scored: int = 0
    refined: int = 0
    tailored: int = 0
    greeted: int = 0
    report_path: str | None = None


def default_keywords(prefs: dict) -> tuple[str, ...]:
    """Derive search keywords from preferences' career_track.

    Dedupes while preserving order; falls back to a sensible default when
    no career_track is configured.
    """
    tracks = prefs.get("career_track") or []
    seen: list[str] = []
    for track in tracks:
        if track and track not in seen:
            seen.append(track)
    if not seen:
        seen.append(_FALLBACK_KEYWORD)
    return tuple(seen)


def build_config(
    prefs: dict,
    *,
    keywords: list[str] | None = None,
    city: str | None = None,
    platforms: list[str] | None = None,
    profile_id: int = DEFAULT_PROFILE_ID,
    refine_top: int = DEFAULT_REFINE_TOP,
    tailor_top: int = DEFAULT_TAILOR_TOP,
    greeting_top: int = DEFAULT_GREETING_TOP,
) -> PipelineConfig:
    """Build a PipelineConfig from preferences plus optional overrides."""
    kw = tuple(keywords) if keywords else default_keywords(prefs)
    return PipelineConfig(
        keywords=kw,
        platforms=tuple(platforms) if platforms else DEFAULT_PLATFORMS,
        city=city or "",
        profile_id=profile_id,
        refine_top=refine_top,
        tailor_top=tailor_top,
        greeting_top=greeting_top,
    )


# ----------------------------------------------------------------------
# Stages
# ----------------------------------------------------------------------


def _search_stage(db: JobPilotDB, cfg: PipelineConfig) -> tuple[StageResult, int]:
    """Search every platform × keyword, upserting results. Returns (result, count).

    Per-platform/keyword failures are caught so one dead channel does not
    abort the others.
    """
    from jobpilot.adapters.base import SearchFilters
    from jobpilot.adapters.github_jobs import GitHubAdapter
    from jobpilot.adapters.websearch import WebSearchAdapter
    from jobpilot.adapters.xhs_search import XHSSearchAdapter

    registry = {
        "websearch": WebSearchAdapter,
        "xhs": XHSSearchAdapter,
        "github": GitHubAdapter,
    }
    filters = SearchFilters(city=cfg.city)
    total = 0
    errors: list[str] = []

    for platform in cfg.platforms:
        adapter_cls = registry.get(platform)
        if adapter_cls is None:
            errors.append(f"{platform}:未知平台")
            continue
        adapter = adapter_cls()
        for keyword in cfg.keywords:
            try:
                jobs = adapter.search(keyword, filters)
                if jobs:
                    total += db.upsert_jobs(jobs)
            except Exception as exc:  # noqa: BLE001 - isolate per-channel failure
                logger.exception("search failed: %s / %s", platform, keyword)
                errors.append(f"{platform}/{keyword}:{exc}")

    ok = not errors
    detail = f"入库 {total} 个岗位"
    if errors:
        detail += "；部分失败: " + "; ".join(errors)
    return StageResult("搜索", ok, detail), total


def _score_stage(db: JobPilotDB, cfg: PipelineConfig) -> tuple[StageResult, int, int]:
    """Heuristic-score all new jobs, then API-refine top N. Returns (result, scored, refined)."""
    from jobpilot.ai.scorer import score_jobs

    profile = db.get_profile(cfg.profile_id)
    if not profile:
        return StageResult("打分", False, f"未找到 profile {cfg.profile_id}"), 0, 0

    new_jobs = db.list_jobs(status="new", limit=10000)
    scored = 0
    if new_jobs:
        scores = score_jobs(profile, new_jobs, force_heuristic=True)
        for s in scores:
            db.upsert_score(s)
            db.update_job_status(s.job_id, "scored")
        scored = len(scores)

    refined = 0
    if cfg.refine_top > 0 and config.ANTHROPIC_API_KEY:
        pairs = db.list_scores_with_jobs(profile_id=cfg.profile_id, limit=cfg.refine_top)
        if pairs:
            jobs_to_refine = [job for _, job in pairs]
            refined_scores = score_jobs(profile, jobs_to_refine, force_heuristic=False)
            for s in refined_scores:
                db.upsert_score(s)
            refined = len(refined_scores)

    detail = f"启发式秒评 {scored} 个，API 精评 {refined} 个"
    return StageResult("打分", True, detail), scored, refined


def _tailor_stage(db: JobPilotDB, cfg: PipelineConfig) -> tuple[StageResult, int]:
    """Batch-tailor resumes for top N scored-but-untailored jobs. Returns (result, count)."""
    if cfg.tailor_top <= 0:
        return StageResult("定制简历", True, "已跳过 (tailor_top=0)"), 0

    from jobpilot.ai.tailor import save_tailored_resume

    profile = db.get_profile(cfg.profile_id)
    if not profile:
        return StageResult("定制简历", False, f"未找到 profile {cfg.profile_id}"), 0

    candidates = db.list_top_untailored(cfg.profile_id, limit=cfg.tailor_top)
    if not candidates:
        return StageResult("定制简历", True, "没有待定制的高分岗位"), 0

    success = 0
    errors: list[str] = []
    for _score_obj, job in candidates:
        try:
            save_tailored_resume(profile, job)
            db.update_job_status(job.job_id, "tailored")
            success += 1
        except Exception as exc:  # noqa: BLE001 - isolate per-job failure
            logger.exception("tailor failed for %s", job.job_id)
            errors.append(f"{job.company}:{exc}")

    ok = not errors
    detail = f"定制 {success}/{len(candidates)} 份简历"
    if errors:
        detail += "；失败: " + "; ".join(errors)
    return StageResult("定制简历", ok, detail), success


def _greeting_filename(company: str, title: str) -> str:
    safe_company = (company or "公司").replace("/", "_")[:20]
    safe_title = (title or "岗位").replace("/", "_")[:30]
    return f"{safe_company}_{safe_title}.txt"


def _greeting_stage(db: JobPilotDB, cfg: PipelineConfig) -> tuple[StageResult, int]:
    """Generate personal-style greetings for top N high-score jobs, saved to files."""
    if cfg.greeting_top <= 0:
        return StageResult("打招呼话术", True, "已跳过 (greeting_top=0)"), 0

    from jobpilot.ai.greeting import GreetingError, _load_greeting_config, generate_greeting

    if not _load_greeting_config().get("base_template"):
        return StageResult("打招呼话术", True, "未配置 greeting 模板，已跳过"), 0

    pairs = db.list_top_scored_jobs(
        profile_id=cfg.profile_id,
        min_score=config.MIN_RECOMMEND_SCORE,
        statuses=("scored", "tailored"),
        limit=cfg.greeting_top,
    )
    if not pairs:
        return StageResult("打招呼话术", True, "没有高分岗位"), 0

    success = 0
    errors: list[str] = []
    for score_obj, job in pairs:
        try:
            result = generate_greeting(job, score_obj, channel="boss")
            path = config.GREETINGS_DIR / _greeting_filename(job.company, job.title)
            path.write_text(result.save_text(), encoding="utf-8")
            success += 1
        except GreetingError as exc:
            errors.append(f"{job.company}:{exc}")
        except Exception as exc:  # noqa: BLE001 - isolate per-job failure
            logger.exception("greeting failed for %s", job.job_id)
            errors.append(f"{job.company}:{exc}")

    ok = not errors
    detail = f"生成 {success}/{len(pairs)} 条打招呼话术 → {config.GREETINGS_DIR}"
    if errors:
        detail += "；失败: " + "; ".join(errors)
    return StageResult("打招呼话术", ok, detail), success


def _report_stage(db: JobPilotDB, cfg: PipelineConfig) -> tuple[StageResult, str | None]:
    """Generate and persist the daily report. Returns (result, path)."""
    from jobpilot.report import save_report

    path = save_report(db, None, profile_id=cfg.profile_id)
    return StageResult("日报", True, f"已保存: {path}"), path


# ----------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------


def run_pipeline(
    db: JobPilotDB,
    cfg: PipelineConfig,
    *,
    progress: Callable[[str], None] | None = None,
) -> PipelineResult:
    """Run the full chain. Each stage is isolated; a crash never aborts later stages.

    Args:
        db: Database handle.
        cfg: Pipeline configuration.
        progress: Optional callback for stage-by-stage progress messages.

    Returns:
        Aggregated PipelineResult with per-stage outcomes and counters.
    """

    def emit(msg: str) -> None:
        if progress:
            progress(msg)

    stages: list[StageResult] = []
    found = scored = refined = tailored = greeted = 0
    report_path: str | None = None

    emit("[1/5] 搜索岗位 (WebSearch + 小红书)…")
    try:
        result, found = _search_stage(db, cfg)
    except Exception as exc:  # noqa: BLE001
        logger.exception("search stage crashed")
        result = StageResult("搜索", False, f"阶段异常: {exc}")
    stages.append(result)

    emit("[2/5] AI 打分 (启发式 + API 精评)…")
    try:
        result, scored, refined = _score_stage(db, cfg)
    except Exception as exc:  # noqa: BLE001
        logger.exception("score stage crashed")
        result = StageResult("打分", False, f"阶段异常: {exc}")
    stages.append(result)

    emit("[3/5] 定制 top 简历…")
    try:
        result, tailored = _tailor_stage(db, cfg)
    except Exception as exc:  # noqa: BLE001
        logger.exception("tailor stage crashed")
        result = StageResult("定制简历", False, f"阶段异常: {exc}")
    stages.append(result)

    emit("[4/5] 生成 top 打招呼话术…")
    try:
        result, greeted = _greeting_stage(db, cfg)
    except Exception as exc:  # noqa: BLE001
        logger.exception("greeting stage crashed")
        result = StageResult("打招呼话术", False, f"阶段异常: {exc}")
    stages.append(result)

    emit("[5/5] 生成日报…")
    try:
        result, report_path = _report_stage(db, cfg)
    except Exception as exc:  # noqa: BLE001
        logger.exception("report stage crashed")
        result = StageResult("日报", False, f"阶段异常: {exc}")
    stages.append(result)

    return PipelineResult(
        stages=tuple(stages),
        found=found,
        scored=scored,
        refined=refined,
        tailored=tailored,
        greeted=greeted,
        report_path=report_path,
    )
