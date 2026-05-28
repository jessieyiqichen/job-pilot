// Frozen demo samples baked into the static build, keyed by job numeric id.
// They showcase the CLI-only features (resume tailoring + interview prep) on the
// deployed read-only demo, where no API key / local docx pipeline is available.
// Content is representative of real output, not generated live.

export interface TailorSample {
  note: string;
  before: { section: string; text: string }[];
  after: { section: string; text: string }[];
}

export interface InterviewSampleQuestion {
  category: string;
  question: string;
  talking_point: string;
}

export interface InterviewSample {
  prep_notes: string;
  questions: InterviewSampleQuestion[];
}

export const TAILOR_SAMPLES: Record<number, TailorSample> = {
  188: {
    note: '原简历偏数据分析方向。针对 SpatialWalk 的「数字人 / AIGC / vibe-coding」JD，重排为 AI 产品方向：把最相关的 AI avatar 项目提到最前，量化结果，语言对标岗位。所有内容均源自真实经历，无捏造。',
    before: [
      {
        section: 'Summary',
        text: 'Economics graduate student at UChicago (GPA 4.0) with hands-on experience in causal inference, machine learning, and data-driven business analysis. Seeking analytics or strategy roles.',
      },
      {
        section: 'Project — Nous',
        text: 'Built a cognitive-layer AI avatar with 9-dimension modeling and conversational interviews.',
      },
    ],
    after: [
      {
        section: 'Summary',
        text: 'Builder of AI products focused on digital-human and conversational systems. Independently shipped an AI avatar engine (71% behavioral-prediction accuracy) and two live AI tools using Claude API + Next.js. Strong in rapid prototyping (vibe-coding), product evaluation, and turning model output into usable product. Seeking an AI product internship in the digital-human / AIGC space.',
      },
      {
        section: 'Project — Nous (AI Avatar)',
        text: 'Built a cognitive-layer AI avatar: 9-dimension cognitive modeling + conversational interviews, lifting behavioral-prediction accuracy from 49% to 71% (T2 90%). Designed contradiction detection across dimensions; passive collector captured 101 signals from natural conversation — directly relevant to high-fidelity digital-human behavior.',
      },
      {
        section: 'Skills (reordered)',
        text: 'AIGC tooling & prompt design · evaluation/eval loops · Python · Claude API · Next.js · NLP — front-loaded over econometrics to match the JD.',
      },
    ],
  },
  179: {
    note: '针对字节 AI 产品经理实习，强调端到端独立交付产品的能力 + 数据/指标思维（字节看重）。把 JobPilot/MusiClaw 的产品化与自动化提前，量化用户与规模。',
    before: [
      {
        section: 'Summary',
        text: 'Economics graduate student with experience in causal inference, machine learning, and data analysis.',
      },
      {
        section: 'Project — JobPilot',
        text: 'Built an AI job-hunting assistant with multi-channel search and AI scoring.',
      },
    ],
    after: [
      {
        section: 'Summary',
        text: 'AI product builder who ships end to end: from problem to a working, measured product. Built JobPilot (AI matching + one-command automation pipeline) and MusiClaw (live analytics platform) solo. Combines product sense with a quantitative, metrics-driven background (causal inference, A/B testing).',
      },
      {
        section: 'Project — JobPilot',
        text: 'Designed and shipped an AI job-search assistant: multi-channel aggregation, multi-dimensional AI scoring with a two-pass cost strategy (free heuristic pre-screen + API refine), automated resume tailoring, and an eval loop measuring score-vs-judgment agreement (precision/recall). 20 CLI commands, 330+ tests, Next.js dashboard — first user (myself) screened 349 jobs down to 37 high-matches.',
      },
    ],
  },
};

export const INTERVIEW_SAMPLES: Record<number, InterviewSample> = {
  188: {
    prep_notes:
      '主打：你做过的 Nous AI avatar 与数字人方向高度相关，要主动牵到这条线；vibe-coding 用 JobPilot/MusiClaw 独立交付佐证。短板：没有正式产品岗 title，用「独立从 0 到 1 交付」对冲。',
    questions: [
      {
        category: '项目深挖',
        question: '介绍一个你做过的、和数字人/AI 形象最相关的项目。',
        talking_point:
          'S：想验证"用对话推断人的认知"。T：搭一个 9 维认知建模的 AI avatar。A：设计对话访谈 + 双轨信号提取 + 矛盾检测。R：行为预测从 49%→71%（T2 90%），被动采集 101 个信号。牵引到数字人「高保真行为」的产品价值。',
      },
      {
        category: '产品 sense',
        question: '如果让你评测一批数字人形象的质量，你会定义哪些指标？',
        talking_point:
          '从我做评分 eval 的经验出发：先定 ground truth（真人偏好打标），再分维度（真实度/口型同步/情绪一致/时延），用 precision/recall 量化模型和人判断的一致性，改一版测一版对比。',
      },
      {
        category: '技术理解',
        question: '你怎么理解 vibe-coding？举个你自己的例子。',
        talking_point:
          'JobPilot/MusiClaw 都是我用 Claude Code 独立从 0 到 1 搭出来的——快速搭骨架、跑起来、按真实使用反馈迭代。能交付结果而不是写文档。',
      },
      {
        category: '岗位&公司匹配',
        question: '为什么想来一家数字人创业公司，而不是大厂？',
        talking_point:
          '我喜欢端到端拥有一个产品（独立项目就是证据），创业公司没有 dirty work、直接和创始团队配合，正好匹配我「做核心、快速试错」的习惯。',
      },
      {
        category: '行为面',
        question: '讲一次你交付结果时遇到的最大障碍，怎么解决的。',
        talking_point:
          'MusiClaw 爬取座位图做票房估算时反爬+数据噪声大，我用座位图颜色分析 + 容错管道解决，最终部署上线日更。诚实说：这块更多是工程韧性，正式团队协作经验需要补强。',
      },
    ],
  },
  179: {
    prep_notes:
      '字节看重数据/指标思维 + 端到端落地。主打 JobPilot 的产品化与 eval；准备好被追问"指标怎么定、怎么验证"。',
    questions: [
      {
        category: '产品 sense',
        question: '你做的 JobPilot，如果要定一个北极星指标，你会选什么？为什么？',
        talking_point:
          '我会选「高匹配岗位的投递转化」而不是搜索量——因为产品价值是帮我投到对的岗，不是看更多岗。我已经用 eval（precision/recall）在量化"高分岗里我真想投的比例"，正是为这个指标服务。',
      },
      {
        category: '项目深挖',
        question: 'JobPilot 的 AI 打分，你怎么知道它"准"？',
        talking_point:
          '这正是我做 eval 模块的原因：用我自己的投/不投决策当 ground truth，算 AI≥7 分 vs 我真想投的 precision/recall/F1。先度量，再调权重，调完用同一指标对比——不瞎调。',
      },
      {
        category: '技术理解',
        question: '为了控制大模型成本，你在 JobPilot 里做过哪些取舍？',
        talking_point:
          '两段式打分：先用免费启发式给 339 个岗位秒评粗筛，只对 top 20 调 API 精评，一次跑下来成本可控。简历定制也不让 AI 重排版，而是 difflib 补丁回原 docx，避免翻车。',
      },
      {
        category: '行为面',
        question: '你一个人做这么多项目，怎么决定优先级？',
        talking_point:
          '按「对真实用户（我自己）痛点的价值」排。比如 JobPilot 先做自动化闭环再做 demo，因为闭环直接省我时间；eval 优先于校准，因为没度量调权重没意义。',
      },
      {
        category: '岗位&公司匹配',
        question: '为什么是 AI 产品，而不是继续走数据分析？',
        talking_point:
          '我的量化背景（因果推断、A/B）是底座，但我更享受"把模型能力变成有人用的产品"——三个独立项目都是这个模式。诚实说：我在主动从研究转向产品。',
      },
    ],
  },
};
