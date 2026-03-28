import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH =
  process.env.JOBPILOT_DB_PATH ??
  path.join(process.cwd(), '..', 'data', 'jobpilot.db');

function openDb(): Database.Database {
  return new Database(DB_PATH, { readonly: true });
}

export interface JobRow {
  id: number;
  job_id: string;
  platform: string;
  title: string;
  company: string;
  salary_min: number | null;
  salary_max: number | null;
  city: string | null;
  experience: string | null;
  education: string | null;
  jd_text: string | null;
  discovered_at: string | null;
  status: string;
  overall_score: number | null;
  skill_match: number | null;
  experience_match: number | null;
  salary_match: number | null;
  highlights: string | null;
  concerns: string | null;
  suggestion: string | null;
  scored_at: string | null;
  raw_data: string | null;
}

function parseJsonArray(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function getJobsWithScores(): ReadonlyArray<JobRow> {
  const db = openDb();
  try {
    return db
      .prepare(
        `SELECT
          j.id, j.job_id, j.platform, j.title, j.company,
          j.salary_min, j.salary_max, j.city, j.experience, j.education,
          j.jd_text, j.discovered_at, j.status, j.raw_data,
          s.overall_score, s.skill_match, s.experience_match, s.salary_match,
          s.highlights, s.concerns, s.suggestion, s.scored_at
        FROM jobs j
        LEFT JOIN job_scores s ON j.job_id = s.job_id
        ORDER BY s.overall_score DESC NULLS LAST`,
      )
      .all() as JobRow[];
  } finally {
    db.close();
  }
}

export function getJobDetail(jobId: number): JobRow | null {
  const db = openDb();
  try {
    const row = db
      .prepare(
        `SELECT
          j.id, j.job_id, j.platform, j.title, j.company,
          j.salary_min, j.salary_max, j.city, j.experience, j.education,
          j.jd_text, j.discovered_at, j.status, j.raw_data,
          s.overall_score, s.skill_match, s.experience_match, s.salary_match,
          s.highlights, s.concerns, s.suggestion, s.scored_at
        FROM jobs j
        LEFT JOIN job_scores s ON j.job_id = s.job_id
        WHERE j.id = ?`,
      )
      .get(jobId) as JobRow | undefined;
    return row ?? null;
  } finally {
    db.close();
  }
}

export function getPipelineCounts(): ReadonlyArray<{ status: string; count: number }> {
  const db = openDb();
  try {
    return db
      .prepare(
        `SELECT status, COUNT(*) as count FROM jobs GROUP BY status ORDER BY count DESC`,
      )
      .all() as Array<{ status: string; count: number }>;
  } finally {
    db.close();
  }
}

export function getScoreDistribution(): ReadonlyArray<{ bucket: number; count: number }> {
  const db = openDb();
  try {
    return db
      .prepare(
        `SELECT CAST(overall_score AS INT) as bucket, COUNT(*) as count
        FROM job_scores
        WHERE overall_score IS NOT NULL
        GROUP BY bucket
        ORDER BY bucket ASC`,
      )
      .all() as Array<{ bucket: number; count: number }>;
  } finally {
    db.close();
  }
}

export function getSourceBreakdown(): ReadonlyArray<{ platform: string; count: number }> {
  const db = openDb();
  try {
    return db
      .prepare(
        `SELECT platform, COUNT(*) as count FROM jobs GROUP BY platform ORDER BY count DESC`,
      )
      .all() as Array<{ platform: string; count: number }>;
  } finally {
    db.close();
  }
}

function extractSourceUrl(row: JobRow): string | null {
  // XHS / websearch: source_url in raw_data
  if (row.raw_data) {
    try {
      const raw = JSON.parse(row.raw_data);
      if (raw.source_url) return raw.source_url;
      // Boss: construct URL from encryptJobId
      if (row.platform === 'boss' && raw.encryptJobId) {
        return `https://www.zhipin.com/job_detail/${raw.encryptJobId}.html`;
      }
    } catch {
      // ignore
    }
  }
  return null;
}

/** Lightweight query: only company + title for filename construction */
export function getJobById(jobId: number): { company: string; title: string } | null {
  const db = openDb();
  try {
    const row = db
      .prepare(`SELECT company, title FROM jobs WHERE id = ?`)
      .get(jobId) as { company: string; title: string } | undefined;
    return row ?? null;
  } finally {
    db.close();
  }
}

export { parseJsonArray, extractSourceUrl };
