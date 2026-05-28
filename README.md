# JobPilot

[![CI](https://github.com/jessieyiqichen/job-pilot/actions/workflows/ci.yml/badge.svg)](https://github.com/jessieyiqichen/job-pilot/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jessieyiqichen/job-pilot/branch/main/graph/badge.svg)](https://codecov.io/gh/jessieyiqichen/job-pilot)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![Claude API](https://img.shields.io/badge/Claude-API-D97757?logo=anthropic&logoColor=white)
![Tests](https://img.shields.io/badge/tests-452%20passing-3FB950)
![License](https://img.shields.io/badge/license-MIT-blue)

AI-powered job hunting assistant for Chinese recruitment platforms.

Not a scraper — an intelligent layer on top of existing tools: AI matching, resume tailoring, application tracking, and a one-command automation pipeline, with a Next.js dashboard.

**Live demo (read-only snapshot):** https://web-ten-omega-72.vercel.app

## What it does

- **Resume parsing** — PDF/DOCX to structured profile via Claude API
- **Multi-channel search** — WebSearch (default) + Xiaohongshu (search & favorites import) + GitHub hiring issues (official Search API) + Boss (via boss-cli)
- **AI scoring** — Multi-dimensional 1-10 matching with preference weighting; two-pass strategy (free heuristic pre-screen + API refine on top N); company blacklist + headhunter down-ranking
- **Resume tailoring** — Proficiently methodology + original docx patching (preserves fonts & layout); skills whitelist prevents AI inflation
- **One-command pipeline** — `pipeline-all` runs search → score → tailor → greeting → report end to end; each stage is isolated so one dead channel never aborts the rest
- **Daily digest + email** — Surfaces only newly-discovered high-score jobs and stale-application follow-ups; optional local scheduling (launchd) + SMTP delivery
- **Interview prep** — Likely questions per job mapped to STAR talking points grounded in your real resume
- **Greeting messages** — Channel-specific opening messages (Boss / Xiaohongshu / email) from a configurable style guide; you send them yourself
- **Job-hunt strategy companion (军师)** — `chat` is a multi-turn advisor with cross-session memory, grounded in your real data; it proactively follows up on commitments you voiced ("you said you'd apply to ByteDance — did you?"), auto-closing them once the job is applied. `advisor` diagnoses your funnel for weekly actions; `plan` builds this week's apply list (deterministic); `ask` answers one-off questions; `followup` tracks open commitments
- **Eval-driven scoring** — `label` + `eval` measure agreement (precision/recall/F1) between AI scores and your own apply/skip decisions
- **Web dashboard** — Next.js board: job cards, funnel chart, score distribution, and an advisor page
- **Graceful degradation** — Heuristic scoring + prompt export when no API key

## What it does NOT do

- No scraping (uses existing CLI/MCP tools via subprocess)
- No automatic application submission (apply stays human-in-the-loop)
- No skill fabrication (whitelist-based)

> Note: `boss-cli` is currently unavailable upstream (anti-scraping broke `__zp_stoken__`), so search defaults to WebSearch + Xiaohongshu.

## Compliance & boundaries（合规与边界）

JobPilot is a **local, read-first, user-triggered** assistant. Deliberate boundaries:

- **Does not submit applications or contact recruiters.** `apply` only records status locally; you open the original post and reach out yourself.
- **Does not write its own scrapers.** WebSearch uses Anthropic's official `web_search` tool (no browser). Xiaohongshu goes through `rednote-mcp` (Playwright automation **under your own login session**). Boss relies on `boss-cli`.
- **Low-frequency, on-demand.** No bulk outreach, no risk-control bypass; a scheduled run does single-digit-to-tens of jobs/day with `job_id` dedup.
- **Data stays local.** SQLite DB and resumes never leave your machine; the public demo serves a sanitized, frozen snapshot.
- **No skill fabrication.** Tailoring/interview/greeting only reference experience that exists in your resume.

## Architecture

```
JobPilot CLI (26 commands; cli.py is a thin shell → commands/*)
    ├── pipeline.py    — End-to-end orchestration (search→score→tailor→greeting→report), per-stage isolation
    │
    ├── AI Layer (Claude API)
    │   ├── parser.py    — Resume → structured JSON
    │   ├── scorer.py    — Multi-dim scoring + heuristic fallback
    │   ├── tailor.py    — Proficiently methodology + docx patch
    │   ├── interview.py — Interview questions + STAR talking points
    │   ├── greeting.py  — Channel-specific HR opening messages
    │   ├── advisor.py   — Funnel diagnosis (deterministic) + weekly advice
    │   ├── ask.py       — Situation-grounded job-search Q&A
    │   └── chat.py      — Multi-turn advisor + cross-session memory (chat_store.py)
    │
    ├── Adapter Layer
    │   ├── websearch.py   — Anthropic web_search tool (default)
    │   ├── xhs_search.py  — Xiaohongshu search via rednote-mcp + AI extraction
    │   ├── xhs.py         — Xiaohongshu favorites (parse-only)
    │   ├── github_jobs.py — GitHub hiring issues + 谁在招人 thread comments (official API)
    │   └── boss.py        — Boss (subprocess → boss-cli)
    │
    ├── planner.py / filters.py / eval.py / notify.py / report.py — Weekly apply plan, blacklist filter, scoring eval, SMTP digest, report
    │
    ├── Data Layer (SQLite, WAL, 4 tables)
    │   ├── profiles · jobs · job_scores · applications
    │
    └── web/ — Next.js 16 dashboard (Tailwind 4 + echarts): board + funnel + advisor page, better-sqlite3
```

## Quick Start

```bash
pip install -e .

cp data/resume_config.example.yaml data/resume_config.yaml   # edit with your details
cp .env.example .env                                         # add ANTHROPIC_API_KEY (+ SMTP for email)

jobpilot resume ~/resume.docx          # 1. parse resume
jobpilot pipeline-all                  # 2. one command: search → score → tailor → report
jobpilot list --min-score 7            # 3. review high matches
jobpilot interview <job_id>            # 4. prep for an interview
jobpilot apply                         # 5. mark applied (human-in-the-loop)
```

## All Commands

| Command | Description |
|---------|-------------|
| `setup` | Interactive preference questionnaire |
| `resume <path>` | Parse resume into profile |
| `search <query> --platform <websearch\|xhs\|github\|boss>` | Search jobs via adapters |
| `score [--heuristic] [--refine N]` | AI score (two-pass: heuristic + API refine) |
| `list [--min-score N]` | List jobs with scores |
| `detail <job_id>` | Job details + score breakdown |
| `status <job_id> <status>` | Update application status |
| `tailor <job_id>` / `--top N` / `--from-text <file>` | Tailor resume (single / batch / import) |
| `interview <job_id> [-o file.md]` | Generate interview prep (questions + STAR points) |
| `greeting <job_id> [-c boss\|xhs\|email]` | Channel-specific opening message for the HR (you send it) |
| `advisor` | Strategy advisor — diagnoses your real funnel and gives this week's actions |
| `ask "<question>"` | Job-search Q&A grounded in your situation + preferences |
| `chat [--job <id>] [--new]` | Real-time multi-turn advisor with cross-session memory + proactive follow-up |
| `plan [--target N]` | This week's apply list (deterministic) + follow-up reminders |
| `followup [--done <id>] [--drop <id>]` | Track commitments voiced in chat; auto-closes once a job is applied |
| `import-xhs <json> [--score]` | Import Xiaohongshu favorites |
| `apply` | Interactive batch apply |
| `pipeline` | Funnel statistics |
| `pipeline-all [--email] [--platforms ...] [--greeting N]` | Full automation: search→score→tailor→greeting→report |
| `digest [--email]` | Preview/send daily digest |
| `label [--min-score N]` | Interactively label jobs (apply/skip) for eval |
| `eval [--threshold N]` | Measure AI-score agreement (precision/recall/F1) |
| `pdf <md_path>` | Markdown resume to PDF |
| `report` | Daily progress report |
| `stats` | Database statistics |

## Full automation

```bash
# One command runs the whole chain; each stage is isolated (a dead channel won't abort the rest)
jobpilot pipeline-all --platforms websearch --email
```

Optional daily scheduling on macOS (local launchd — your data and API key stay on your machine):

```bash
cp scripts/com.jobpilot.daily.plist ~/Library/LaunchAgents/   # edit Hour/Minute first
launchctl load ~/Library/LaunchAgents/com.jobpilot.daily.plist
```

`scripts/daily_run.sh` runs the pipeline and emails a digest of only the newly-discovered high-score jobs. SMTP credentials are read from `.env` (never committed).

## Eval-driven scoring

```bash
jobpilot label              # interactively mark jobs apply/skip → data/eval_labels.json
jobpilot eval --threshold 7 # precision/recall/F1 of AI score vs your judgment
```

Ground truth comes from your application decisions (applied/offer = 1, rejected = 0) and/or the manual labels file. This is the measurement foundation for recalibrating scoring weights — tune, re-eval, compare.

## Web dashboard

```bash
cd web
npm install
npm run dev    # reads ../data/jobpilot.db (set JOBPILOT_DB_PATH to override)
```

Deploys to Vercel as a read-only demo: a sanitized snapshot is bundled and baked into a static site at build time (`force-static` + `generateStaticParams`), so there's no runtime database. Refresh the snapshot with `scripts/refresh_demo.sh [--deploy]`.

## No-API Workflow

JobPilot works without an API key:

1. `jobpilot score` uses heuristic scoring (skills 40% + experience 25% + education 15% + relevance 20%)
2. `jobpilot tailor <job_id>` / `jobpilot interview <job_id>` export a complete prompt to paste into Claude.ai
3. `jobpilot tailor <job_id> --from-text response.txt` patches the AI response back into your docx

## Key Design Decisions

| Decision | Why |
|----------|-----|
| Per-stage isolation in pipeline | One dead channel (e.g. expired XHS cookies) never aborts the whole run |
| Two-pass scoring | Free heuristic pre-screen, API refine only on top N — controls cost |
| Resume patch, not generate | Preserves user's fonts, layout, formatting |
| Skills whitelist | `resume_config.yaml` manually maintained, prevents AI skill inflation |
| Build-time static dashboard | No runtime DB on the deployed demo — robust on serverless |
| Eval before calibration | Measure score↔judgment agreement first; never tune weights blind |
| No auto-apply | Application submission is irreversible — kept human-in-the-loop |
| Frozen dataclasses / connection-per-call | Immutable models, no shared SQLite connections |

## Requirements

- Python 3.12+
- `ANTHROPIC_API_KEY` (optional, for AI features)
- Node 18+ (for the `web/` dashboard)
- [`rednote-mcp`](https://github.com/iFurySt/RedNote-MCP) (optional, for Xiaohongshu search/import)
- [`boss-cli`](https://github.com/jackwener/boss-cli) (optional; currently unavailable upstream)

## Tests

```bash
python -m pytest tests/   # 452 tests
```

## License

MIT
