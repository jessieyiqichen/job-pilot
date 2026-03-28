'use client';

import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { TooltipComponent, TitleComponent, GridComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([BarChart, TooltipComponent, TitleComponent, GridComponent, CanvasRenderer]);

interface ScoreDistChartProps {
  data: { bucket: number; count: number }[];
}

export default function ScoreDistChart({ data }: ScoreDistChartProps) {
  // Fill in missing buckets 0-10
  const bucketMap = new Map(data.map((d) => [d.bucket, d.count]));
  const buckets = Array.from({ length: 11 }, (_, i) => i);
  const counts = buckets.map((b) => bucketMap.get(b) ?? 0);

  const option = {
    title: {
      text: '评分分布',
      textStyle: { fontSize: 15, fontWeight: 600, color: '#0f172a' },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: Array<{ name: string; value: number }>) => {
        const p = params[0];
        return `${p.name} 分: ${p.value} 个`;
      },
    },
    grid: { left: 40, right: 20, top: 50, bottom: 30 },
    xAxis: {
      type: 'category',
      data: buckets.map(String),
      axisLabel: { fontSize: 12, color: '#64748b' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 12, color: '#64748b' },
    },
    series: [
      {
        type: 'bar',
        data: counts.map((c, i) => ({
          value: c,
          itemStyle: {
            color: i >= 7 ? '#22c55e' : i >= 5 ? '#eab308' : '#ef4444',
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barWidth: '60%',
      },
    ],
  };

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 300 }} />
    </div>
  );
}
