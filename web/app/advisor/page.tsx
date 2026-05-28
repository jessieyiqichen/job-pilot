import Link from 'next/link';
import MiniMarkdown from '../../components/MiniMarkdown';
import { ADVISOR } from '../../lib/advisor';

export const dynamic = 'force-static';

function SignalCard({ value, label, accent }: { value: number; label: string; accent?: boolean }) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        accent ? 'border-blue-100 bg-blue-50/40' : 'border-gray-100 bg-white'
      }`}
    >
      <div className={`text-2xl font-bold ${accent ? 'text-blue-600' : 'text-gray-900'}`}>
        {value}
      </div>
      <div className="mt-1 text-[12px] text-gray-500">{label}</div>
    </div>
  );
}

export default function AdvisorPage() {
  const { headline, signals, plan, advice, generated_at } = ADVISOR;

  return (
    <div className="animate-fadeIn space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">求职军师</h1>
        <p className="mt-2 text-[14px] leading-relaxed text-gray-600">
          不只是找岗位——军师读你的真实求职数据，诊断瓶颈、排本周投递计划、答疑。
          诊断和计划是确定性的（每个数字都来自系统记录），策略建议由 Claude 生成。
        </p>
      </div>

      {/* Headline verdict */}
      <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-6">
        <div className="text-[12px] font-medium uppercase tracking-wide text-blue-600">一句话诊断</div>
        <p className="mt-2 text-[16px] font-semibold leading-relaxed text-gray-900">{headline}</p>
      </div>

      {/* Key signals */}
      <div>
        <h2 className="mb-3 text-[15px] font-semibold text-gray-900">关键信号</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <SignalCard value={signals.high_score_total} label="高分岗（≥7）" accent />
          <SignalCard value={signals.high_score_applied} label="高分岗已投" />
          <SignalCard value={signals.high_score_tailored} label="已定制简历" />
          <SignalCard value={signals.total_applications} label="投递总数" />
        </div>
      </div>

      {/* Weekly plan */}
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h2 className="mb-1 text-[15px] font-semibold text-gray-900">本周投递计划</h2>
        <p className="mb-3 text-[12px] text-gray-500">
          目标本周投 {plan.weekly_target} 个；近 7 天已投 {plan.recent_applied} 个。
        </p>
        {plan.note && (
          <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-[12px] text-amber-700">{plan.note}</p>
        )}
        {plan.to_apply.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-gray-100 text-[12px] text-gray-400">
                  <th className="py-2 pr-3">评分</th>
                  <th className="py-2 pr-3">岗位</th>
                  <th className="py-2 pr-3">公司</th>
                  <th className="py-2 pr-3">简历</th>
                  <th className="py-2">怎么做</th>
                </tr>
              </thead>
              <tbody>
                {plan.to_apply.map((it, i) => (
                  <tr key={i} className="border-b border-gray-50 last:border-0">
                    <td className="py-2 pr-3 font-semibold text-blue-600">{it.score.toFixed(1)}</td>
                    <td className="py-2 pr-3 text-gray-900">{it.title}</td>
                    <td className="py-2 pr-3 text-gray-600">{it.company}</td>
                    <td className="py-2 pr-3">
                      {it.ready ? (
                        <span className="text-green-600">✅ 就绪</span>
                      ) : (
                        <span className="text-gray-400">✍️ 待定制</span>
                      )}
                    </td>
                    <td className="py-2 text-[12px] text-gray-500">{it.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-[13px] text-gray-500">暂无待投高分岗。</p>
        )}

        {plan.follow_ups.length > 0 && (
          <div className="mt-4">
            <h3 className="mb-2 text-[13px] font-semibold text-gray-800">⏰ 该跟进的投递</h3>
            <ul className="space-y-1">
              {plan.follow_ups.map((f, i) => (
                <li key={i} className="text-[13px] text-gray-600">
                  {f.title} — 投出去 {f.days_since} 天，主动问进度或转下一个
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Claude advice */}
      {advice && (
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-[15px] font-semibold text-gray-900">军师建议</h2>
          <MiniMarkdown text={advice} />
        </div>
      )}

      {/* Footnote */}
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <ul className="space-y-1.5 text-[13px] leading-relaxed text-gray-600">
          <li>· 诊断 + 周计划由 <code className="rounded bg-gray-100 px-1.5 py-0.5 text-[12px]">jobpilot advisor / plan</code> 确定性生成，每条都能指回数据。</li>
          <li>· 「军师建议」由 <code className="rounded bg-gray-100 px-1.5 py-0.5 text-[12px]">jobpilot advisor</code> 调 Claude API 真实生成（非手写）。</li>
          <li>· 数据为脱敏只读快照；投递相关数字反映真实状态（当前尚未开始投递）。</li>
        </ul>
        <Link href="/" className="mt-4 inline-block text-[13px] text-blue-600 hover:underline">
          &larr; 回到岗位看板
        </Link>
        <p className="mt-3 text-[11px] text-gray-400">快照生成于 {generated_at}</p>
      </div>
    </div>
  );
}
