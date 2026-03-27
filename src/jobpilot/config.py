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
# AI Scoring
# ============================================================
# Minimum score to recommend (1-10)
MIN_RECOMMEND_SCORE: float = 7.0

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
