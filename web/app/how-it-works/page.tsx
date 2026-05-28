import Link from 'next/link';

function Term({ children }: { children: React.ReactNode }) {
  return (
    <pre className="overflow-x-auto rounded-lg bg-gray-900 p-4 text-[12px] leading-relaxed text-gray-100">
      {children}
    </pre>
  );
}

function Step({
  n,
  cmd,
  title,
  children,
}: {
  n: number;
  cmd: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="mb-2 flex items-center gap-3">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-[12px] font-bold text-white">
          {n}
        </span>
        <h3 className="text-[15px] font-semibold text-gray-900">{title}</h3>
        <code className="ml-auto rounded bg-gray-100 px-2 py-0.5 text-[12px] text-gray-600">{cmd}</code>
      </div>
      <p className="text-[13px] leading-relaxed text-gray-600">{children}</p>
    </div>
  );
}

export default function HowItWorksPage() {
  return (
    <div className="animate-fadeIn space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">工作原理</h1>
        <p className="mt-2 text-[14px] leading-relaxed text-gray-600">
          这个看板只是 JobPilot 的「结果展示层」。真正的引擎是一套 Python CLI（20 个命令）+ Claude API：
          多渠道搜索 → AI 打分 → 简历定制 → 面试准备 → 投递追踪，可一条命令端到端跑完。
          下面是核心能力（看板里看到的评分数据，就是这条链路产出的）。
        </p>
      </div>

      <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-6">
        <h2 className="mb-2 text-[15px] font-semibold text-gray-900">一条命令跑完全流程</h2>
        <p className="mb-3 text-[13px] text-gray-600">
          每个阶段独立容错——某个渠道挂了（如小红书 cookies 过期）不会拖垮其余阶段。
        </p>
        <Term>{`$ jobpilot pipeline-all --platforms websearch --email
[1/4] 搜索岗位 (WebSearch + 小红书)…
[2/4] AI 打分 (启发式 + API 精评)…
[3/4] 定制 top 简历…
[4/4] 生成日报…

运行结果
  ✓ 搜索: 入库 18 个岗位
  ✓ 打分: 启发式秒评 18 个，API 精评 20 个
  ✓ 定制简历: 定制 5/5 份简历
  ✓ 日报: 已保存
✉️  digest 已发送`}</Term>
      </div>

      <div className="space-y-4">
        <Step n={1} cmd="jobpilot score" title="多维 AI 打分（两段式控成本）">
          先用免费启发式给全部岗位秒评粗筛，只对 top N 调 Claude API 精评。维度含技能/经验/学历/岗位相关度/偏好，
          输出亮点、顾虑、建议——看板每个岗位详情页的评分就来自这里。
        </Step>
        <Step n={2} cmd="jobpilot tailor" title="简历定制（保留排版）">
          按 JD 重排真实经历，不重新生成 docx，而是用 difflib 把改动补丁回原文件，保留字体与排版；
          技能白名单防止 AI 膨胀未声明的技能。点开任意示范岗位看「定制简历样例」。
        </Step>
        <Step n={3} cmd="jobpilot interview" title="面试准备生成">
          给高分岗 + 你的简历，生成大概率会问的问题 + 对标你真实经历的 STAR 答题要点。示范岗位页有样例。
        </Step>
        <Step n={4} cmd="jobpilot label / eval" title="评分一致性度量（先度量后校准）">
          用你的「投 / 不投」决策当 ground truth，量化 AI 打分与你判断的一致性，为调权重提供依据——不瞎调。
        </Step>
      </div>

      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-[15px] font-semibold text-gray-900">打分一致性评估</h2>
        <Term>{`$ jobpilot eval --threshold 7
📊 打分一致性评估（阈值 >= 7.0，样本 N）
  Precision（推荐里你真想投的比例）   ██████
  Recall   （你想投的里被推荐的比例）  ████████
  F1 / Accuracy + 混淆矩阵 + 调参诊断`}</Term>
      </div>

      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-[15px] font-semibold text-gray-900">关于这个 demo</h2>
        <ul className="space-y-1.5 text-[13px] leading-relaxed text-gray-600">
          <li>· 这是只读快照：本地 pipeline 不向线上推送，岗位数据为脱敏冻结快照（已移除简历原文）。</li>
          <li>· 简历定制 / 面试准备在示范岗位以静态样例呈现（真实功能跑在本地 CLI + Claude API）。</li>
          <li>· 引擎（搜索/打分/定制/自动化/邮件）全部本地运行——Vercel 只托管这个看板。</li>
        </ul>
        <Link href="/" className="mt-4 inline-block text-[13px] text-blue-600 hover:underline">
          &larr; 回到岗位看板
        </Link>
      </div>
    </div>
  );
}
