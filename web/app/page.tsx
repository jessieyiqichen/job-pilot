import Link from 'next/link';
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
      {/* Demo guide banner */}
      <div className="rounded-xl border border-blue-100 bg-gradient-to-r from-blue-50/70 to-purple-50/50 p-4">
        <p className="text-[13px] leading-relaxed text-gray-700">
          <span className="font-semibold text-gray-900">JobPilot</span> 是一套 AI 求职助手（Python + Claude API）。
          这是只读 demo——点开{' '}
          <Link href="/job/188" className="font-medium text-blue-600 hover:underline">
            SpatialWalk
          </Link>{' '}
          或{' '}
          <Link href="/job/179" className="font-medium text-blue-600 hover:underline">
            字节
          </Link>{' '}
          的岗位详情，可看「定制简历」与「面试准备」样例；
          <Link href="/how-it-works" className="font-medium text-blue-600 hover:underline">
            工作原理
          </Link>{' '}
          讲清整条引擎。
        </p>
      </div>
      <h1 className="text-xl font-bold text-gray-900">岗位看板</h1>
      <JobGrid jobs={jobs} />
    </div>
  );
}
