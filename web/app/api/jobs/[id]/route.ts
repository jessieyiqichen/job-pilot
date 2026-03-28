import { NextResponse } from 'next/server';
import { getJobDetail, parseJsonArray, extractSourceUrl } from '@/lib/db';
import type { JobWithScore } from '@/types/job';

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const jobId = parseInt(id, 10);
    if (isNaN(jobId)) {
      return NextResponse.json({ error: 'Invalid job ID' }, { status: 400 });
    }

    const row = getJobDetail(jobId);
    if (!row) {
      return NextResponse.json({ error: 'Job not found' }, { status: 404 });
    }

    const job: JobWithScore = {
      id: row.id,
      job_id: row.job_id,
      platform: row.platform,
      title: row.title ?? '',
      company: row.company ?? '',
      salary_min: row.salary_min,
      salary_max: row.salary_max,
      city: row.city,
      experience: row.experience,
      education: row.education,
      jd_text: row.jd_text,
      discovered_at: row.discovered_at,
      status: row.status,
      overall_score: row.overall_score,
      skill_match: row.skill_match,
      experience_match: row.experience_match,
      salary_match: row.salary_match,
      highlights: parseJsonArray(row.highlights),
      concerns: parseJsonArray(row.concerns),
      suggestion: row.suggestion,
      scored_at: row.scored_at,
      source_url: extractSourceUrl(row),
    };

    return NextResponse.json(job);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
