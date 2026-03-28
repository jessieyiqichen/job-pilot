'use client';

import { useEffect, useState } from 'react';
import FunnelChart from '@/components/FunnelChart';
import ScoreDistChart from '@/components/ScoreDistChart';
import SourcePieChart from '@/components/SourcePieChart';
import type { PipelineStats } from '@/types/job';

export default function PipelinePage() {
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/stats')
      .then((r) => r.json())
      .then((data) => setStats(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex h-64 items-center justify-center text-gray-400">加载中...</div>;
  }

  if (!stats) {
    return <div className="flex h-64 items-center justify-center text-gray-400">加载失败</div>;
  }

  const totalJobs = stats.funnel.reduce((sum, s) => sum + s.count, 0);
  const totalScored = stats.scoreDistribution.reduce((sum, s) => sum + s.count, 0);
  const highScore = stats.scoreDistribution
    .filter((s) => s.bucket >= 7)
    .reduce((sum, s) => sum + s.count, 0);

  return (
    <div className="animate-fadeIn space-y-6">
      <h1 className="text-xl font-bold text-gray-900">求职漏斗</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-[12px] text-gray-400">总岗位</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{totalJobs}</p>
        </div>
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-[12px] text-gray-400">已评分</p>
          <p className="mt-1 text-2xl font-bold text-blue-600">{totalScored}</p>
        </div>
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-[12px] text-gray-400">高分 (&ge;7)</p>
          <p className="mt-1 text-2xl font-bold text-emerald-600">{highScore}</p>
        </div>
        <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
          <p className="text-[12px] text-gray-400">来源数</p>
          <p className="mt-1 text-2xl font-bold text-purple-600">{stats.sourceBreakdown.length}</p>
        </div>
      </div>

      {/* Charts */}
      <FunnelChart data={stats.funnel} />

      <div className="grid gap-4 sm:grid-cols-2">
        <ScoreDistChart data={stats.scoreDistribution} />
        <SourcePieChart data={stats.sourceBreakdown} />
      </div>
    </div>
  );
}
