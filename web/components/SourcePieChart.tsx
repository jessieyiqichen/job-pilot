'use client';

import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { PieChart } from 'echarts/charts';
import { TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([PieChart, TooltipComponent, TitleComponent, LegendComponent, CanvasRenderer]);

const PLATFORM_LABELS: Record<string, string> = {
  boss: 'BOSS直聘',
  websearch: 'Web搜索',
  xhs: '小红书',
};

const PLATFORM_COLORS: Record<string, string> = {
  boss: '#60a5fa',
  websearch: '#a78bfa',
  xhs: '#f87171',
};

interface SourcePieChartProps {
  data: { platform: string; count: number }[];
}

export default function SourcePieChart({ data }: SourcePieChartProps) {
  const option = {
    title: {
      text: '岗位来源',
      textStyle: { fontSize: 15, fontWeight: 600, color: '#0f172a' },
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      bottom: 0,
      textStyle: { fontSize: 12, color: '#64748b' },
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n{c}',
          fontSize: 12,
        },
        data: data.map((d) => ({
          name: PLATFORM_LABELS[d.platform] ?? d.platform,
          value: d.count,
          itemStyle: {
            color: PLATFORM_COLORS[d.platform] ?? '#94a3b8',
          },
        })),
      },
    ],
  };

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 300 }} />
    </div>
  );
}
