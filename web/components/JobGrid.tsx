'use client';

import { useState, useMemo } from 'react';
import JobCard from './JobCard';
import JobFilter, { type FilterState } from './JobFilter';
import type { JobWithScore } from '@/types/job';

export default function JobGrid({ jobs }: { jobs: JobWithScore[] }) {
  const [filter, setFilter] = useState<FilterState>({
    search: '',
    city: '',
    platform: '',
    jobType: 'intern',
    timeRange: '30d',
    minScore: 0,
    sort: 'score',
  });

  const cities = useMemo(() => {
    const set = new Set<string>();
    for (const j of jobs) {
      if (j.city) set.add(j.city);
    }
    return [...set].sort();
  }, [jobs]);

  const platforms = useMemo(() => {
    const set = new Set<string>();
    for (const j of jobs) {
      if (j.platform) set.add(j.platform);
    }
    return [...set].sort();
  }, [jobs]);

  const filtered = useMemo(() => {
    const q = filter.search.toLowerCase();
    let result = jobs.filter((j) => {
      if (q && !j.title.toLowerCase().includes(q) && !j.company.toLowerCase().includes(q)) return false;
      if (filter.city && j.city !== filter.city) return false;
      if (filter.platform && j.platform !== filter.platform) return false;
      if (filter.minScore > 0 && (j.overall_score == null || j.overall_score < filter.minScore)) return false;
      if (filter.jobType === 'intern') {
        const t = j.title.toLowerCase();
        if (!t.includes('实习') && !t.includes('intern')) return false;
      } else if (filter.jobType === 'fulltime') {
        const t = j.title.toLowerCase();
        if (t.includes('实习') || t.includes('intern')) return false;
      }
      if (filter.timeRange !== 'all' && j.discovered_at) {
        const days = filter.timeRange === '7d' ? 7 : filter.timeRange === '30d' ? 30 : 90;
        const cutoff = new Date(Date.now() - days * 86400000).toISOString();
        if (j.discovered_at < cutoff) return false;
      }
      return true;
    });

    result = [...result].sort((a, b) => {
      if (filter.sort === 'score') {
        return (b.overall_score ?? -1) - (a.overall_score ?? -1);
      }
      if (filter.sort === 'salary') {
        return (b.salary_max ?? 0) - (a.salary_max ?? 0);
      }
      // time
      return (b.discovered_at ?? '').localeCompare(a.discovered_at ?? '');
    });

    return result;
  }, [jobs, filter]);

  return (
    <div className="space-y-4">
      <JobFilter filter={filter} onChange={setFilter} cities={cities} platforms={platforms} />
      <div className="flex items-center justify-between">
        <span className="text-[13px] text-gray-400">
          共 {filtered.length} / {jobs.length} 个岗位
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {filtered.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>
      {filtered.length === 0 && (
        <div className="py-16 text-center text-gray-400">没有匹配的岗位</div>
      )}
    </div>
  );
}
