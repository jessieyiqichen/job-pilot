import Link from 'next/link';

export const dynamic = 'force-static';

function Decision({ title, why }: { title: string; why: string }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <h3 className="text-[14px] font-semibold text-gray-900">{title}</h3>
      <p className="mt-1.5 text-[13px] leading-relaxed text-gray-600">{why}</p>
    </div>
  );
}

export default function ProductThinkingPage() {
  return (
    <div className="animate-fadeIn space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">产品思考</h1>
        <p className="mt-2 text-[14px] leading-relaxed text-gray-600">
          这个项目想证明的不是「写了多少功能」，而是「每个决策都想清楚了为什么」。
          下面是几个主动做出的取舍。
        </p>
      </div>

      {/* Core insight */}
      <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-6">
        <h2 className="mb-2 text-[15px] font-semibold text-gray-900">核心洞察：从「行为层」到「认知层」</h2>
        <p className="text-[13px] leading-relaxed text-gray-600">
          市面上的 AI 求职工具都在帮你<strong className="text-gray-900">投得更多更快</strong>——海投、关键词匹配、套模板。
          但求职真正的卡点不在信息，在人：为什么筛了好岗却不投？为什么 AI 写的话术每次都要改？
          JobPilot 建模的是你<strong className="text-gray-900">怎么想、怎么说</strong>，
          甚至能抓「你说的」和「你做的」之间的矛盾——例如：嘴上把 996 列为 deal-breaker，
          但认知模型显示你在乎的事会自我压榨，于是选 offer 时它提醒你守住边界。关键词匹配给不了这种洞察。
        </p>
      </div>

      {/* Decisions */}
      <div>
        <h2 className="mb-3 text-[15px] font-semibold text-gray-900">关键决策与取舍</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Decision
            title="不做自动投递、不写爬虫"
            why="投递不可逆、平台反爬。边界划在「我们生成、你来发」——宁可少一个功能，换信任和账号安全。"
          />
          <Decision
            title="计划/跟进用确定性逻辑，不烧 LLM"
            why="「本周该投哪几个」能用规则算就别调 API：省成本，且每条建议都能指回数据、扛得住「凭什么」。"
          />
          <Decision
            title="两段式 AI 打分"
            why="免费启发式给全部岗位粗筛，只对 top N 调 API 精评。一次跑完成本可控。"
          />
          <Decision
            title="简历定制 patch 原文件，不重新生成"
            why="用 diff 把改动补丁回原 docx，保留字体排版；技能白名单防 AI 膨胀未声明的能力。"
          />
          <Decision
            title="话术学你的真实语言"
            why="发现给真实范例 few-shot 比写风格规则准得多；你每次改后的版本就是最好的样本，回灌后越用越像你。"
          />
          <Decision
            title="不急着做多用户"
            why="现在最强的个性化恰恰来自深度绑定一个人。冷启动没想清楚前通用化，会稀释成市面上又一个普通工具——先验证对一个人有用。"
          />
        </div>
      </div>

      {/* Honest boundary */}
      <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-[15px] font-semibold text-gray-900">诚实的边界</h2>
        <p className="text-[13px] leading-relaxed text-gray-600">
          现在是深度单用户阶段。多用户的工程不难（数据层已按用户隔离），真难题是<strong className="text-gray-900">冷启动</strong>：
          陌生用户怎么快速获得这种认知深度。思路是「渐进式深度」——新用户不做测评，只填 5 分钟问卷 + 给几段自己的话术，
          然后越用越懂你，像一个跟了你三个月的人。很多时候「不做什么」比「做什么」更体现判断。
        </p>
        <Link href="/advisor" className="mt-4 inline-block text-[13px] text-blue-600 hover:underline">
          看军师怎么诊断 &rarr;
        </Link>
      </div>
    </div>
  );
}
