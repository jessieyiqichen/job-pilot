'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import ScoreBadge from '@/components/ScoreBadge';
import type { JobWithScore } from '@/types/job';
import { TAILOR_SAMPLES, INTERVIEW_SAMPLES } from '@/lib/demo-samples';

const PLATFORM_LABELS: Record<string, string> = {
  boss: 'BOSS直聘',
  websearch: 'Web搜索',
  xhs: '小红书',
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  new: { label: '新发现', color: 'bg-gray-100 text-gray-600' },
  scored: { label: '已评分', color: 'bg-blue-100 text-blue-700' },
  tailored: { label: '已定制', color: 'bg-purple-100 text-purple-700' },
  applied: { label: '已投递', color: 'bg-green-100 text-green-700' },
  interview: { label: '面试中', color: 'bg-amber-100 text-amber-700' },
  offer: { label: '已录用', color: 'bg-emerald-100 text-emerald-700' },
  rejected: { label: '已拒绝', color: 'bg-red-100 text-red-700' },
};

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  const v = value ?? 0;
  const pct = (v / 10) * 100;
  const color = v >= 7 ? 'bg-emerald-500' : v >= 5 ? 'bg-amber-400' : 'bg-red-400';

  return (
    <div className="flex items-center gap-3">
      <span className="w-20 text-[13px] text-gray-500">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-[13px] font-medium text-gray-700">
        {value != null ? value.toFixed(1) : '--'}
      </span>
    </div>
  );
}

export default function JobDetailPage() {
  const params = useParams();
  const [job, setJob] = useState<JobWithScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [resumeReady, setResumeReady] = useState(false);

  useEffect(() => {
    fetch(`/api/jobs/${params.id}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setJob(null);
        } else {
          setJob(data);
        }
      })
      .finally(() => setLoading(false));
  }, [params.id]);

  useEffect(() => {
    if (!job) return;
    fetch(`/api/jobs/${params.id}/resume/check`)
      .then((r) => r.json())
      .then((data) => {
        if (data.exists) setResumeReady(true);
      })
      .catch(() => {});
  }, [job, params.id]);

  if (loading) {
    return <div className="flex h-64 items-center justify-center text-gray-400">加载中...</div>;
  }

  if (!job) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4 text-gray-400">
        <p>岗位不存在</p>
        <Link href="/" className="text-blue-500 hover:underline">返回看板</Link>
      </div>
    );
  }

  const status = STATUS_LABELS[job.status] ?? { label: job.status, color: 'bg-gray-100 text-gray-600' };
  const tailorSample = job.id != null ? TAILOR_SAMPLES[job.id] : undefined;
  const interviewSample = job.id != null ? INTERVIEW_SAMPLES[job.id] : undefined;

  return (
    <div className="animate-fadeIn space-y-6">
      {/* Back */}
      <Link href="/" className="inline-flex items-center gap-1 text-[13px] text-gray-400 hover:text-blue-600">
        &larr; 返回看板
      </Link>

      {/* Header Card */}
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <ScoreBadge score={job.overall_score} size={72} />
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-bold text-gray-900">{job.title}</h1>
            <p className="mt-1 text-[15px] font-medium text-gray-700">{job.company}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-[13px]">
              {job.city && (
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-600">{job.city}</span>
              )}
              {!!(job.salary_min || job.salary_max) && (
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">
                  {job.salary_min && job.salary_max
                    ? `${job.salary_min}-${job.salary_max}K`
                    : job.salary_min
                      ? `${job.salary_min}K+`
                      : `${job.salary_max}K`}
                </span>
              )}
              {job.experience && (
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-600">{job.experience}</span>
              )}
              {job.education && (
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-600">{job.education}</span>
              )}
              <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">
                {PLATFORM_LABELS[job.platform] ?? job.platform}
              </span>
              <span className={`rounded-full px-2.5 py-1 font-medium ${status.color}`}>
                {status.label}
              </span>
              {resumeReady && (
                <button
                  onClick={() => window.open(`/api/jobs/${job.id}/resume`, '_blank')}
                  className="inline-flex items-center gap-1.5 rounded-full bg-purple-50 px-2.5 py-1 text-[13px] font-medium text-purple-700 hover:bg-purple-100 transition-colors"
                >
                  <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M8 2v8m0 0L5 7.5m3 2.5l3-2.5" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M3 11v2.5h10V11" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  下载定制简历
                </button>
              )}
            </div>
            {job.source_url && (
              <a
                href={job.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1.5 text-[13px] text-blue-600 hover:text-blue-800 hover:underline"
              >
                查看原文
                <svg className="h-3.5 w-3.5" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M3.5 1.5H10.5V8.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M10.5 1.5L1.5 10.5" strokeLinecap="round" />
                </svg>
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Score Card */}
      {job.overall_score != null && (
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-[15px] font-semibold text-gray-900">匹配评分</h2>
          <div className="space-y-3">
            <ScoreBar label="技能匹配" value={job.skill_match} />
            <ScoreBar label="经验匹配" value={job.experience_match} />
            <ScoreBar label="薪资匹配" value={job.salary_match} />
          </div>
        </div>
      )}

      {/* AI Analysis Card */}
      {(job.highlights.length > 0 || job.concerns.length > 0 || job.suggestion) && (
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-[15px] font-semibold text-gray-900">AI 分析</h2>
          <div className="space-y-4">
            {job.highlights.length > 0 && (
              <div>
                <h3 className="mb-2 text-[13px] font-medium text-emerald-700">亮点</h3>
                <ul className="space-y-1">
                  {job.highlights.map((h, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px] text-gray-600">
                      <span className="mt-0.5 text-emerald-500">+</span>
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {job.concerns.length > 0 && (
              <div>
                <h3 className="mb-2 text-[13px] font-medium text-red-600">顾虑</h3>
                <ul className="space-y-1">
                  {job.concerns.map((c, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px] text-gray-600">
                      <span className="mt-0.5 text-red-400">-</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {job.suggestion && (
              <div>
                <h3 className="mb-2 text-[13px] font-medium text-blue-700">AI 建议</h3>
                <p className="text-[13px] leading-relaxed text-gray-600 whitespace-pre-wrap">{job.suggestion}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* JD Card */}
      {job.jd_text && (
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-[15px] font-semibold text-gray-900">岗位描述</h2>
          <div className="text-[13px] leading-relaxed text-gray-600 whitespace-pre-wrap">{job.jd_text}</div>
        </div>
      )}

      {/* Tailored Resume Sample (demo showcase of the CLI tailoring feature) */}
      {tailorSample && (
        <div className="rounded-xl border border-purple-100 bg-white p-6 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="text-[15px] font-semibold text-gray-900">定制简历样例</h2>
            <span className="rounded-full bg-purple-50 px-2 py-0.5 text-[11px] font-medium text-purple-600">
              jobpilot tailor
            </span>
          </div>
          <p className="mb-4 text-[12px] leading-relaxed text-gray-400">{tailorSample.note}</p>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="mb-2 text-[12px] font-medium text-gray-400">原简历</h3>
              <div className="space-y-3">
                {tailorSample.before.map((b, i) => (
                  <div key={i} className="rounded-lg bg-gray-50 p-3">
                    <p className="mb-1 text-[11px] font-medium text-gray-400">{b.section}</p>
                    <p className="text-[12px] leading-relaxed text-gray-600">{b.text}</p>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="mb-2 text-[12px] font-medium text-purple-600">定制后（按 JD）</h3>
              <div className="space-y-3">
                {tailorSample.after.map((a, i) => (
                  <div key={i} className="rounded-lg bg-purple-50/50 p-3 ring-1 ring-purple-100">
                    <p className="mb-1 text-[11px] font-medium text-purple-500">{a.section}</p>
                    <p className="text-[12px] leading-relaxed text-gray-700">{a.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Interview Prep Sample (demo showcase of the CLI interview feature) */}
      {interviewSample && (
        <div className="rounded-xl border border-amber-100 bg-white p-6 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="text-[15px] font-semibold text-gray-900">面试准备样例</h2>
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-600">
              jobpilot interview
            </span>
          </div>
          <p className="mb-4 text-[12px] leading-relaxed text-gray-400">{interviewSample.prep_notes}</p>
          <div className="space-y-4">
            {interviewSample.questions.map((q, i) => (
              <div key={i} className="border-l-2 border-amber-200 pl-3">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-600">
                    {q.category}
                  </span>
                  <p className="text-[13px] font-medium text-gray-800">{q.question}</p>
                </div>
                <p className="mt-1.5 text-[12px] leading-relaxed text-gray-600">
                  <span className="font-medium text-gray-400">要点：</span>
                  {q.talking_point}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
