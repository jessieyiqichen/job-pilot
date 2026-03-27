"""
Application tracker — state machine for job application lifecycle.

Status flow:
  new → scored → tailored → applied → replied → interview → offer
                                                            → rejected

Any status can also transition to 'rejected'.
"""

from __future__ import annotations

import logging

from jobpilot import config
from jobpilot.db import JobPilotDB
from jobpilot.models import Application, now_iso

logger = logging.getLogger(__name__)

# Valid status transitions
TRANSITIONS: dict[str, set[str]] = {
    "new": {"scored", "rejected"},
    "scored": {"tailored", "applied", "rejected"},
    "tailored": {"applied", "rejected"},
    "applied": {"replied", "interview", "rejected"},
    "replied": {"interview", "rejected"},
    "interview": {"offer", "rejected"},
    "offer": set(),  # terminal
    "rejected": set(),  # terminal
}


class TrackerError(Exception):
    """Raised when a status transition is invalid."""


def validate_transition(current: str, target: str) -> bool:
    """Check if a status transition is valid."""
    allowed = TRANSITIONS.get(current, set())
    return target in allowed


def update_status(
    db: JobPilotDB,
    job_id: str,
    new_status: str,
    notes: str = "",
) -> Application:
    """Update the status of a job application.

    Creates the application record if it doesn't exist.
    Validates the transition before applying.

    Returns:
        The updated Application
    """
    existing = db.get_application(job_id)

    if existing:
        current = existing.status
        if not validate_transition(current, new_status):
            valid = TRANSITIONS.get(current, set())
            raise TrackerError(
                f"Cannot transition from '{current}' to '{new_status}'. "
                f"Valid transitions: {valid or 'none (terminal state)'}"
            )
    else:
        # For new applications, update the job status too
        job = db.get_job(job_id)
        if not job:
            raise TrackerError(f"Job '{job_id}' not found in database")

    updated_app = Application(
        job_id=job_id,
        status=new_status,
        resume_path=existing.resume_path if existing else "",
        applied_at=existing.applied_at if existing else now_iso(),
        updated_at=now_iso(),
        notes=notes or (existing.notes if existing else ""),
    )
    db.upsert_application(updated_app)

    # Sync job status
    status_map = {
        "applied": "applied",
        "replied": "replied",
        "interview": "interview",
        "offer": "offer",
        "rejected": "rejected",
    }
    if new_status in status_map:
        db.update_job_status(job_id, status_map[new_status])

    logger.info("Job %s: status updated to '%s'", job_id, new_status)
    return updated_app


def get_pipeline_summary(db: JobPilotDB) -> dict[str, int]:
    """Get counts for each status in the pipeline."""
    summary: dict[str, int] = {}
    for status in config.APPLICATION_STATUSES:
        apps = db.list_applications(status=status)
        summary[status] = len(apps)
    return summary
