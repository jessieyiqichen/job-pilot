import { NextResponse } from 'next/server';
import { getPipelineCounts, getScoreDistribution, getSourceBreakdown } from '@/lib/db';
import type { PipelineStats } from '@/types/job';

const STAGE_ORDER = ['new', 'scored', 'tailored', 'applied', 'interview', 'offer', 'rejected'];

const STAGE_LABELS: Record<string, string> = {
  new: '新发现',
  scored: '已评分',
  tailored: '已定制',
  applied: '已投递',
  interview: '面试中',
  offer: '已录用',
  rejected: '已拒绝',
};

export async function GET() {
  try {
    const pipelineRows = getPipelineCounts();
    const scoreDist = getScoreDistribution();
    const sourceRows = getSourceBreakdown();

    // Build funnel in correct stage order
    const countMap = new Map(pipelineRows.map((r) => [r.status, r.count]));
    const funnel = STAGE_ORDER
      .filter((s) => countMap.has(s))
      .map((s) => ({
        stage: STAGE_LABELS[s] ?? s,
        count: countMap.get(s) ?? 0,
      }));

    const stats: PipelineStats = {
      funnel,
      scoreDistribution: scoreDist.map((r) => ({ bucket: r.bucket, count: r.count })),
      sourceBreakdown: sourceRows.map((r) => ({ platform: r.platform, count: r.count })),
    };

    return NextResponse.json(stats);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
