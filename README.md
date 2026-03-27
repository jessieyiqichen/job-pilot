# JobPilot

AI-powered job hunting assistant for Chinese recruitment platforms.

Built with Claude Code — not a scraper, but an intelligent layer on top of existing tools.

## What it does

- **Resume parsing** — PDF/DOCX to structured profile via Claude API
- **Multi-channel search** — Boss (via boss-cli) + web search (auto-fallback) + Xiaohongshu favorites import
- **AI scoring** — Multi-dimensional 1-10 matching with preference weighting
- **Resume tailoring** — Proficiently methodology + original docx patching (preserves fonts & layout)
- **Batch tailoring** — `tailor --top N` for bulk resume customization
- **Application tracking** — State machine: new → scored → applied → interviewing → offer/rejected
- **Pipeline view** — Funnel statistics across all stages
- **Graceful degradation** — Heuristic scoring + prompt export when no API key

## What it does NOT do

- No scraping (uses existing CLI tools via subprocess)
- No login management
- No anti-detection
- No skill fabrication (whitelist-based)

## Architecture

```
JobPilot CLI (15 commands)
    ├── AI Layer (Claude API)
    │   ├── parser.py    — Resume → structured JSON
    │   ├── scorer.py    — Multi-dim scoring + heuristic fallback
    │   └── tailor.py    — Proficiently methodology + docx patch
    │
    ├── Adapter Layer
    │   ├── boss.py      — Boss (subprocess → boss-cli)
    │   ├── websearch.py — Anthropic web_search tool
    │   └── xhs.py       — Xiaohongshu favorites (parse-only)
    │
    └── Data Layer (SQLite, WAL, 4 tables)
        ├── profiles      — Parsed resumes
        ├── jobs          — Aggregated job listings
        ├── job_scores    — AI match scores
        └── applications  — Application tracking
```

## Quick Start

```bash
# Install
pip install -e .

# Configure
cp data/resume_config.example.yaml data/resume_config.yaml
# Edit resume_config.yaml with your details

# Set API key
export ANTHROPIC_API_KEY="your-key"

# 1. Parse your resume
jobpilot resume ~/resume.docx

# 2. Search jobs
jobpilot search "data analyst" --city Shanghai

# 3. AI score all jobs
jobpilot score

# 4. View top matches
jobpilot list --min-score 7

# 5. Tailor resume for top 3
jobpilot tailor --top 3

# 6. Mark as applied
jobpilot apply

# 7. View pipeline
jobpilot pipeline
```

## All Commands

| Command | Description |
|---------|-------------|
| `resume <path>` | Parse resume into profile |
| `search <query> --city <city>` | Search jobs via adapters |
| `score` | AI score all unscored jobs |
| `list [--min-score N]` | List jobs with scores |
| `detail <job_id>` | Job details + score breakdown |
| `status <job_id> <status>` | Update application status |
| `tailor <job_id>` | Tailor resume for a job |
| `tailor --top N` | Batch tailor top N scored jobs |
| `tailor <id> --from-text <file>` | Import externally generated text |
| `import-xhs <json> [--score]` | Import Xiaohongshu favorites |
| `apply` | Interactive batch apply |
| `pipeline` | Funnel statistics |
| `pdf <md_path>` | Markdown resume to PDF |
| `report` | Daily progress report |
| `stats` | Database statistics |

## No-API Workflow

JobPilot works without an API key:

1. `jobpilot score` uses heuristic scoring (skills 40% + experience 25% + education 15% + relevance 20%)
2. `jobpilot tailor <job_id>` exports a complete prompt to paste into Claude.ai
3. `jobpilot tailor <job_id> --from-text response.txt` patches the AI response back into your docx

## Key Design Decisions

| Decision | Why |
|----------|-----|
| Adapter pattern, no scraping | Isolate platform differences, reuse existing tools |
| AI-optional degradation | Works without API key (heuristic scoring + prompt export) |
| Resume patch, not generate | Preserves user's fonts, layout, formatting |
| Skills whitelist | `resume_config.yaml` is manually maintained, prevents AI skill inflation |
| Frozen dataclasses | All models immutable, prevents side effects |
| Connection-per-call SQLite | No shared connections across calls |
| XHS import-only | Discovery is manual (favorites), code only handles structured import |

## Requirements

- Python 3.12+
- `ANTHROPIC_API_KEY` env var (optional, for AI features)
- [`boss-cli`](https://github.com/jackwener/boss-cli) (optional, for Boss search)
- [`rednote-mcp`](https://github.com/iFurySt/RedNote-MCP) (optional, for Xiaohongshu import)

## Tests

```bash
python -m pytest tests/ -v  # 179 tests
```

## License

MIT
