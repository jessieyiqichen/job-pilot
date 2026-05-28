"""
JobPilot configuration.

All configurable values: paths, API keys, search defaults, platform selection.
API keys are read from environment variables — never hardcoded.
"""

import os
from pathlib import Path

# ============================================================
# Paths
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # job-pilot/

# Load secrets from .env (gitignored) so the CLI works without exporting vars.
# Only fills in vars that are missing OR blank in the real environment — a real
# exported value always wins, but an empty env var (common gotcha) won't block .env.
try:
    from dotenv import dotenv_values

    _env_path = BASE_DIR / ".env"
    if _env_path.exists():
        for _k, _v in dotenv_values(_env_path).items():
            if _v and not os.environ.get(_k):
                os.environ[_k] = _v
except ImportError:  # python-dotenv optional; env vars still work
    pass

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "jobpilot.db"
RESUMES_DIR = DATA_DIR / "resumes"
TAILORED_DIR = DATA_DIR / "tailored"

# Ensure directories exist
for _d in (DATA_DIR, RESUMES_DIR, TAILORED_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ============================================================
# API Keys (from environment)
# ============================================================
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.environ.get("JOBPILOT_MODEL", "claude-sonnet-4-5-20250929")

# ============================================================
# Search Defaults
# ============================================================
DEFAULT_CITY: str = os.environ.get("JOBPILOT_CITY", "上海")
DEFAULT_PLATFORM: str = os.environ.get("JOBPILOT_PLATFORM", "websearch")

# ============================================================
# Web Search Fallback
# ============================================================
WEBSEARCH_FALLBACK_THRESHOLD = int(os.environ.get("JOBPILOT_WEBSEARCH_THRESHOLD", "3"))

# ============================================================
# Boss-CLI adapter
# ============================================================
# Path to boss-cli executable (if not on PATH)
BOSS_CLI_PATH: str = os.environ.get("BOSS_CLI_PATH", "boss")

# ============================================================
# rednote-mcp (小红书 MCP server)
# ============================================================
REDNOTE_MCP_PATH: str = os.environ.get(
    "REDNOTE_MCP_PATH",
    str(Path("~/.npm-global/lib/node_modules/rednote-mcp").expanduser()),
)

# ============================================================
# AI Scoring
# ============================================================
# Minimum score to recommend (1-10)
MIN_RECOMMEND_SCORE: float = 7.0

# ============================================================
# Reports & Follow-up
# ============================================================
# Default profile used by reports/pipeline when none is given
DEFAULT_PROFILE_ID: int = int(os.environ.get("JOBPILOT_PROFILE_ID", "10"))
# Daily digest: a job counts as "new" if discovered within N days
NEW_JOB_LOOKBACK_DAYS: int = int(os.environ.get("JOBPILOT_NEW_JOB_LOOKBACK_DAYS", "1"))
# Follow-up reminder: 'applied' with no update for >= N days needs follow-up
FOLLOWUP_STALE_DAYS: int = int(os.environ.get("JOBPILOT_FOLLOWUP_STALE_DAYS", "7"))

# ============================================================
# Email delivery (SMTP) — secrets come from env / .env, never committed
# ============================================================
SMTP_HOST: str = os.environ.get("JOBPILOT_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.environ.get("JOBPILOT_SMTP_PORT", "587"))
SMTP_USER: str = os.environ.get("JOBPILOT_SMTP_USER", "")
# Gmail App Password (NOT your login password); set in .env
SMTP_PASSWORD: str = os.environ.get("JOBPILOT_SMTP_PASSWORD", "")
# Recipient; defaults to SMTP_USER (send to yourself)
SMTP_TO: str = os.environ.get("JOBPILOT_SMTP_TO", "")

# ============================================================
# Application Status Flow
# ============================================================
APPLICATION_STATUSES = [
    "new",          # just discovered
    "scored",       # AI scored
    "tailored",     # resume tailored
    "applied",      # application sent
    "replied",      # got a reply
    "interview",    # interview scheduled
    "offer",        # received offer
    "rejected",     # rejected
]
