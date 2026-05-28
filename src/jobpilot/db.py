"""
SQLite data layer for JobPilot.

Provides unified storage for profiles, jobs, scores, and applications.
Pattern inspired by damai/scraper/db.py — connection-per-call, WAL mode, upsert semantics.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

from jobpilot import config
from jobpilot.models import Application, Job, JobScore, Profile

logger = logging.getLogger(__name__)


class JobPilotDB:
    """SQLite-backed data store for JobPilot."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else config.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """Create a new connection (one per call, not thread-shared)."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        conn = self._connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    raw_text TEXT,
                    structured JSON,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    job_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    company TEXT,
                    salary_min INTEGER,
                    salary_max INTEGER,
                    city TEXT,
                    experience TEXT,
                    education TEXT,
                    jd_text TEXT,
                    raw_data JSON,
                    discovered_at TEXT,
                    status TEXT DEFAULT 'new'
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_platform
                ON jobs(platform);

                CREATE INDEX IF NOT EXISTS idx_jobs_status
                ON jobs(status);

                CREATE INDEX IF NOT EXISTS idx_jobs_city
                ON jobs(city);

                CREATE TABLE IF NOT EXISTS job_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(job_id),
                    profile_id INTEGER NOT NULL REFERENCES profiles(id),
                    overall_score REAL,
                    skill_match REAL,
                    experience_match REAL,
                    salary_match REAL,
                    highlights JSON,
                    concerns JSON,
                    suggestion TEXT,
                    scored_at TEXT,
                    UNIQUE(job_id, profile_id)
                );

                CREATE INDEX IF NOT EXISTS idx_scores_overall
                ON job_scores(overall_score DESC);

                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(job_id),
                    status TEXT NOT NULL,
                    resume_path TEXT,
                    applied_at TEXT,
                    updated_at TEXT,
                    notes TEXT,
                    UNIQUE(job_id)
                );
            """)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Profiles
    # ------------------------------------------------------------------

    def upsert_profile(self, profile: Profile) -> int:
        """Insert or update a profile. Returns the profile id."""
        conn = self._connect()
        try:
            d = profile.to_dict()
            if profile.id:
                conn.execute(
                    """UPDATE profiles
                       SET name=?, raw_text=?, structured=?, updated_at=?
                       WHERE id=?""",
                    (d["name"], d["raw_text"], d["structured"], d["updated_at"], d["id"]),
                )
                conn.commit()
                return profile.id
            else:
                cursor = conn.execute(
                    """INSERT INTO profiles (name, raw_text, structured, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (d["name"], d["raw_text"], d["structured"], d["updated_at"]),
                )
                conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

    def get_profile(self, profile_id: int = 1) -> Profile | None:
        """Get a profile by id. Default to id=1 (primary profile)."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM profiles WHERE id = ?", (profile_id,)
            ).fetchone()
            return Profile.from_row(dict(row)) if row else None
        finally:
            conn.close()

    def list_profiles(self) -> list[Profile]:
        """List all profiles."""
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM profiles ORDER BY id").fetchall()
            return [Profile.from_row(dict(r)) for r in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def upsert_job(self, job: Job) -> None:
        """Insert or update a job (upsert on job_id)."""
        conn = self._connect()
        try:
            d = job.to_dict()
            conn.execute(
                """INSERT INTO jobs
                       (platform, job_id, title, company, salary_min, salary_max,
                        city, experience, education, jd_text, raw_data,
                        discovered_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(job_id) DO UPDATE SET
                       title=excluded.title,
                       company=excluded.company,
                       salary_min=excluded.salary_min,
                       salary_max=excluded.salary_max,
                       jd_text=excluded.jd_text,
                       raw_data=excluded.raw_data""",
                (
                    d["platform"], d["job_id"], d["title"], d["company"],
                    d["salary_min"], d["salary_max"], d["city"], d["experience"],
                    d["education"], d["jd_text"], d["raw_data"],
                    d["discovered_at"], d["status"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_jobs(self, jobs: list[Job]) -> int:
        """Batch upsert jobs. Returns count."""
        for job in jobs:
            self.upsert_job(job)
        return len(jobs)

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by platform job_id."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            return Job.from_row(dict(row)) if row else None
        finally:
            conn.close()

    def list_jobs(
        self,
        status: str | None = None,
        city: str | None = None,
        platform: str | None = None,
        limit: int = 100,
    ) -> list[Job]:
        """List jobs with optional filters."""
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if city:
            conditions.append("city = ?")
            params.append(city)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        conn = self._connect()
        try:
            rows = conn.execute(
                f"SELECT * FROM jobs {where} ORDER BY discovered_at DESC LIMIT ?",
                params,
            ).fetchall()
            return [Job.from_row(dict(r)) for r in rows]
        finally:
            conn.close()

    def update_job_status(self, job_id: str, status: str) -> None:
        """Update a job's status."""
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE jobs SET status = ? WHERE job_id = ?", (status, job_id)
            )
            conn.commit()
        finally:
            conn.close()

    def count_jobs(self, status: str | None = None) -> int:
        """Count jobs, optionally filtered by status."""
        conn = self._connect()
        try:
            if status:
                row = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status = ?", (status,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
            return row[0]
        finally:
            conn.close()

    def count_jobs_by_status(self) -> dict[str, int]:
        """Count jobs grouped by status. Returns {status: count}."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS n FROM jobs GROUP BY status"
            ).fetchall()
            return {r["status"]: r["n"] for r in rows}
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Scores
    # ------------------------------------------------------------------

    def upsert_score(self, score: JobScore) -> None:
        """Insert or update a score (upsert on job_id + profile_id)."""
        conn = self._connect()
        try:
            d = score.to_dict()
            conn.execute(
                """INSERT INTO job_scores
                       (job_id, profile_id, overall_score, skill_match,
                        experience_match, salary_match, highlights,
                        concerns, suggestion, scored_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(job_id, profile_id) DO UPDATE SET
                       overall_score=excluded.overall_score,
                       skill_match=excluded.skill_match,
                       experience_match=excluded.experience_match,
                       salary_match=excluded.salary_match,
                       highlights=excluded.highlights,
                       concerns=excluded.concerns,
                       suggestion=excluded.suggestion,
                       scored_at=excluded.scored_at""",
                (
                    d["job_id"], d["profile_id"], d["overall_score"],
                    d["skill_match"], d["experience_match"], d["salary_match"],
                    d["highlights"], d["concerns"], d["suggestion"],
                    d["scored_at"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_score(self, job_id: str, profile_id: int = 1) -> JobScore | None:
        """Get score for a job-profile pair."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM job_scores WHERE job_id = ? AND profile_id = ?",
                (job_id, profile_id),
            ).fetchone()
            return JobScore.from_row(dict(row)) if row else None
        finally:
            conn.close()

    def list_scores(
        self,
        profile_id: int = 1,
        min_score: float = 0.0,
        limit: int = 50,
    ) -> list[JobScore]:
        """List scores sorted by overall_score descending."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT * FROM job_scores
                   WHERE profile_id = ? AND overall_score >= ?
                   ORDER BY overall_score DESC LIMIT ?""",
                (profile_id, min_score, limit),
            ).fetchall()
            return [JobScore.from_row(dict(r)) for r in rows]
        finally:
            conn.close()

    def list_scores_with_jobs(
        self,
        profile_id: int = 1,
        min_score: float = 0.0,
        limit: int = 50,
    ) -> list[tuple[JobScore, Job]]:
        """List scores joined with job info."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT js.*, j.title, j.company, j.city, j.salary_min, j.salary_max,
                          j.platform, j.status as job_status
                   FROM job_scores js
                   JOIN jobs j ON js.job_id = j.job_id
                   WHERE js.profile_id = ? AND js.overall_score >= ?
                   ORDER BY js.overall_score DESC LIMIT ?""",
                (profile_id, min_score, limit),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                score = JobScore.from_row(d)
                job = Job.from_row({
                    "job_id": d["job_id"],
                    "title": d["title"],
                    "company": d["company"],
                    "city": d["city"],
                    "salary_min": d["salary_min"],
                    "salary_max": d["salary_max"],
                    "platform": d["platform"],
                    "status": d.get("job_status", ""),
                })
                result.append((score, job))
            return result
        finally:
            conn.close()

    def list_top_untailored(
        self,
        profile_id: int = 1,
        min_score: float = 0.0,
        limit: int = 10,
    ) -> list[tuple[JobScore, Job]]:
        """Top scored jobs where job.status = 'scored' (not yet tailored).

        Returns list of (JobScore, Job) sorted by overall_score DESC.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT js.*, j.platform, j.title, j.company, j.city,
                          j.salary_min, j.salary_max, j.experience, j.education,
                          j.jd_text, j.raw_data, j.discovered_at,
                          j.status as job_status
                   FROM job_scores js
                   JOIN jobs j ON js.job_id = j.job_id
                   WHERE js.profile_id = ?
                     AND js.overall_score >= ?
                     AND j.status = 'scored'
                   ORDER BY js.overall_score DESC
                   LIMIT ?""",
                (profile_id, min_score, limit),
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                score_obj = JobScore.from_row(d)
                job = Job.from_row({
                    "job_id": d["job_id"],
                    "platform": d.get("platform", ""),
                    "title": d["title"],
                    "company": d["company"],
                    "city": d["city"],
                    "salary_min": d["salary_min"],
                    "salary_max": d["salary_max"],
                    "experience": d.get("experience", ""),
                    "education": d.get("education", ""),
                    "jd_text": d.get("jd_text", ""),
                    "raw_data": d.get("raw_data", "{}"),
                    "discovered_at": d.get("discovered_at", ""),
                    "status": d.get("job_status", "scored"),
                })
                result.append((score_obj, job))
            return result
        finally:
            conn.close()

    def list_top_scored_jobs(
        self,
        profile_id: int = 1,
        min_score: float = 7.0,
        statuses: tuple[str, ...] = ("scored", "tailored"),
        limit: int = 20,
    ) -> list[tuple[JobScore, Job]]:
        """Join job_scores + jobs, filter by statuses, order by score DESC."""
        conn = self._connect()
        try:
            placeholders = ",".join("?" for _ in statuses)
            params: list = [profile_id, min_score] + list(statuses) + [limit]
            rows = conn.execute(
                f"""SELECT js.*, j.platform, j.title, j.company, j.city,
                           j.salary_min, j.salary_max, j.experience, j.education,
                           j.jd_text, j.raw_data, j.discovered_at,
                           j.status as job_status
                    FROM job_scores js
                    JOIN jobs j ON js.job_id = j.job_id
                    WHERE js.profile_id = ?
                      AND js.overall_score >= ?
                      AND j.status IN ({placeholders})
                    ORDER BY js.overall_score DESC
                    LIMIT ?""",
                params,
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                score_obj = JobScore.from_row(d)
                job = Job.from_row({
                    "job_id": d["job_id"],
                    "platform": d.get("platform", ""),
                    "title": d["title"],
                    "company": d["company"],
                    "city": d["city"],
                    "salary_min": d["salary_min"],
                    "salary_max": d["salary_max"],
                    "experience": d.get("experience", ""),
                    "education": d.get("education", ""),
                    "jd_text": d.get("jd_text", ""),
                    "raw_data": d.get("raw_data", "{}"),
                    "discovered_at": d.get("discovered_at", ""),
                    "status": d.get("job_status", ""),
                })
                result.append((score_obj, job))
            return result
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Applications
    # ------------------------------------------------------------------

    def upsert_application(self, app: Application) -> None:
        """Insert or update an application (upsert on job_id)."""
        conn = self._connect()
        try:
            d = app.to_dict()
            conn.execute(
                """INSERT INTO applications
                       (job_id, status, resume_path, applied_at, updated_at, notes)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(job_id) DO UPDATE SET
                       status=excluded.status,
                       resume_path=excluded.resume_path,
                       updated_at=excluded.updated_at,
                       notes=excluded.notes""",
                (
                    d["job_id"], d["status"], d["resume_path"],
                    d["applied_at"], d["updated_at"], d["notes"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_application(self, job_id: str) -> Application | None:
        """Get application by job_id."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM applications WHERE job_id = ?", (job_id,)
            ).fetchone()
            return Application.from_row(dict(row)) if row else None
        finally:
            conn.close()

    def list_applications(self, status: str | None = None) -> list[Application]:
        """List applications, optionally filtered by status."""
        conn = self._connect()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM applications ORDER BY updated_at DESC"
                ).fetchall()
            return [Application.from_row(dict(r)) for r in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        conn = self._connect()
        try:
            stats: dict[str, Any] = {}
            stats["profiles"] = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
            stats["jobs_total"] = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            stats["jobs_new"] = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'new'"
            ).fetchone()[0]
            stats["jobs_scored"] = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = 'scored'"
            ).fetchone()[0]
            stats["scores"] = conn.execute("SELECT COUNT(*) FROM job_scores").fetchone()[0]
            stats["applications"] = conn.execute(
                "SELECT COUNT(*) FROM applications"
            ).fetchone()[0]
            avg_row = conn.execute(
                "SELECT AVG(overall_score) FROM job_scores"
            ).fetchone()
            stats["avg_score"] = round(avg_row[0], 1) if avg_row[0] else 0.0
            return stats
        finally:
            conn.close()
