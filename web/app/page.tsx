import { getJobsWithScores, parseJsonArray, extractSourceUrl } from '@/lib/db';
import JobGrid from '@/components/JobGrid';
import type { JobWithScore } from '@/types/job';

export default function HomePage() {
  const rows = getJobsWithScores();
  const jobs: JobWithScore[] = rows.map((r) => ({
    id: r.id,
    job_id: r.job_id,
    platform: r.platform,
    title: r.title ?? '',
    company: r.company ?? '',
    salary_min: r.salary_min,
    salary_max: r.salary_max,
    city: r.city,
    experience: r.experience,
    education: r.education,
    jd_text: null, // Don't send full JD to client
    discovered_at: r.discovered_at,
    status: r.status,
    overall_score: r.overall_score,
    skill_match: r.skill_match,
    experience_match: r.experience_match,
    salary_match: r.salary_match,
    highlights: parseJsonArray(r.highlights),
    concerns: parseJsonArray(r.concerns),
    suggestion: r.suggestion,
    scored_at: r.scored_at,
    source_url: extractSourceUrl(r),
  }));

  return (
    <div className="animate-fadeIn space-y-4">
      <h1 className="text-xl font-bold text-gray-900">岗位看板</h1>
      <JobGrid jobs={jobs} />
    </div>
  );
}
