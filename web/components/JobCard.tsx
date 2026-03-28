'use client';

import { useRouter } from 'next/navigation';
import ScoreBadge from './ScoreBadge';
import type { JobWithScore } from '@/types/job';

const PLATFORM_LABELS: Record<string, { label: string; color: string }> = {
  boss: { label: 'BOSS', color: 'bg-blue-100 text-blue-700' },
  websearch: { label: '搜索', color: 'bg-purple-100 text-purple-700' },
  xhs: { label: '小红书', color: 'bg-red-100 text-red-700' },
};

function formatSalary(min: number | null, max: number | null): string {
  if (!min && !max) return '';
  if (min && max) return `${min}-${max}K`;
  if (min) return `${min}K+`;
  return `${max}K`;
}

export default function JobCard({ job }: { job: JobWithScore }) {
  const router = useRouter();
  const platform = PLATFORM_LABELS[job.platform] ?? { label: job.platform, color: 'bg-gray-100 text-gray-700' };
  const salary = formatSalary(job.salary_min, job.salary_max);

  return (
    <div
      onClick={() => router.push(`/job/${job.id}`)}
      className="group flex cursor-pointer gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm transition-all hover:border-blue-200 hover:shadow-md"
    >
      <ScoreBadge score={job.overall_score} size={52} />
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-[15px] font-semibold text-gray-900 group-hover:text-blue-700">
          {job.title}
        </h3>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-[13px] text-gray-500">
          <span className="font-medium text-gray-700">{job.company}</span>
          {job.city && <span>{job.city}</span>}
          {salary && <span className="font-medium text-emerald-600">{salary}</span>}
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {job.source_url ? (
            <a
              href={job.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${platform.color} hover:opacity-80`}
            >
              {platform.label}
              <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M3.5 1.5H10.5V8.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M10.5 1.5L1.5 10.5" strokeLinecap="round" />
              </svg>
            </a>
          ) : (
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${platform.color}`}>
              {platform.label}
            </span>
          )}
          {job.experience && (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-500">
              {job.experience}
            </span>
          )}
          {job.education && (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-500">
              {job.education}
            </span>
          )}
          {job.status === 'tailored' && (
            <span className="inline-flex items-center gap-0.5 rounded-full bg-purple-50 px-2 py-0.5 text-[11px] font-medium text-purple-600">
              <svg className="h-3 w-3" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M4 8h8M4 4h8M4 12h5" strokeLinecap="round" />
              </svg>
              已定制
            </span>
          )}
        </div>
        {job.suggestion && (
          <p className="mt-2 truncate text-[12px] leading-relaxed text-gray-400">
            {job.suggestion}
          </p>
        )}
      </div>
    </div>
  );
}
