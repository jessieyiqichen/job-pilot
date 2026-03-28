'use client';

import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { FunnelChart as FunnelChartComponent } from 'echarts/charts';
import { TooltipComponent, TitleComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([FunnelChartComponent, TooltipComponent, TitleComponent, CanvasRenderer]);

interface FunnelChartProps {
  data: { stage: string; count: number }[];
}

export default function FunnelChart({ data }: FunnelChartProps) {
  const option = {
    title: {
      text: '求职漏斗',
      textStyle: { fontSize: 15, fontWeight: 600, color: '#0f172a' },
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}',
    },
    series: [
      {
        type: 'funnel',
        left: '10%',
        top: 50,
        bottom: 20,
        width: '80%',
        min: 0,
        max: Math.max(...data.map((d) => d.count), 1),
        sort: 'none',
        gap: 2,
        label: {
          show: true,
          position: 'inside',
          formatter: '{b}\n{c}',
          fontSize: 13,
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 1,
        },
        data: data.map((d, i) => ({
          name: d.stage,
          value: d.count,
          itemStyle: {
            color: [
              '#94a3b8', '#60a5fa', '#a78bfa', '#34d399', '#fbbf24', '#22c55e', '#ef4444',
            ][i % 7],
          },
        })),
      },
    ],
  };

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      <ReactEChartsCore echarts={echarts} option={option} style={{ height: 360 }} />
    </div>
  );
}
