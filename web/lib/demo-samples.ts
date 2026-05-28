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
  // 真实由 `jobpilot interview` 生成（Claude API），非手写。
  188: {
    prep_notes:
      '核心优势：① 数据驱动+结果导向（所有项目都有数据→insight→business impact 链路）② 快速学习（6 天搭爬虫、独立完成多项目）③ 商业 sense（经济学+票务项目）④ 项目 ownership（多次 Team Leader / 独立项目）。需提前补强：面试前深度体验 HeyGen/D-ID/腾讯智影，了解 Stable Diffusion/ComfyUI 基础，准备数字人赛道分析 + SpatialWalk 针对性问题。',
    questions: [
      {
        category: '行为面',
        question:
          '你在简历中提到担任过多个项目的负责人，能否分享一次你在团队协作中遇到冲突或意见不统一的情况，你是如何处理的？',
        talking_point:
          '【S】Sentiment Analysis 项目任 Team Leader，处理 10 万+ 评论、选模型方案。【T】要在 KNN/Random Forest/LSTM 间做选择，成员对技术路线有分歧。【A】设计系统 benchmark，用 TimeSeriesSplit 交叉验证客观对比，用数据说话；每人负责一个模型调优，保证参与感。【R】LSTM 达 86% 精度、比 baseline 高 18 个百分点，团队因清晰分工+数据驱动而信服。',
      },
      {
        category: '行为面',
        question:
          "这个岗位需要'能交付结果'且'肯花时间'。能分享一个时间紧迫或资源有限、你仍保质保量完成的例子吗？",
        talking_point:
          '【S】Live Ticketing 市场情报系统是我的独立项目，数据源完全不公开。【T】短时间从零搭自动化爬虫拿 SKU 级票务数据。【A】自学 Playwright/Selenium 搭稳定采集 pipeline，6 天积累 618+ 条覆盖 22 场演出，反复调试反爬。【R】识别出销售率 3.7%→97.5% 的巨大差异、发现 6 天涨 17 个百分点的爆款，为定价提供独特 insight。',
      },
      {
        category: '产品sense',
        question:
          '如果让你评估一个数字人产品的核心指标，你会选哪些？若生成速度与画面质量冲突，如何取舍？',
        talking_point:
          '分层设计：技术指标(逼真度/流畅度/速度/稳定性)、用户指标(满意度/时长/复购)、商业指标(转化/客单价/交付周期)。取舍看场景：ToB 大客户→画质优先；C 端高频→速度优先。方法上像做 TimeSeriesSplit 一样用 A/B 找质量-速度最优点。【需补强】面试前深度体验 HeyGen、D-ID，记录各家取舍策略。',
      },
      {
        category: '产品sense',
        question:
          "JD 提到'探索算法效果的边界'。让你测一个新的数字人生成算法，你会怎样系统性发现它的能力边界和局限？",
        talking_point:
          '【方法论迁移】像 Tax Morale 项目处理 7000+ 样本那样构建测试集，覆盖人物特征/场景复杂度/动作类型；像 benchmark 三个模型一样设可量化指标(保真度/自然度/边缘成功率)+评分 rubric；系统测极端 case 记录失败模式；像 Bayesian 调参一样按结果向算法团队反馈。【需补强】学习 FID/LPIPS 等数字人专业评测标准。',
      },
      {
        category: '技术理解',
        question:
          '你对主流 AI 图像/视频生成模型(Stable Diffusion、Runway、Sora 等)的原理与应用区别有了解吗？对数字人有什么启发？',
        talking_point:
          '【基础】有 LSTM/Random Forest 训练调优经验，理解架构/数据质量/超参的影响；知道 SD 基于 diffusion、Sora 增加时间维度连贯性挑战。【迁移】NLP 处理 10 万+ 文本让我懂数据质量决定效果，对数字人(高质量人脸/表情数据)同样关键。【诚实+计划】实操工具(Midjourney/ComfyUI)经验有限，计划系统学 prompt 工程、读 CVPR/ICCV 数字人论文、1-2 周内能独立产出——6 天搭爬虫证明我学得快。',
      },
      {
        category: '技术理解',
        question: "JD 提到 'vibe-coding'，你理解吗？有相关经历吗？在 AI 产品开发中能发挥什么作用？",
        talking_point:
          "【理解】通过快速原型迭代找产品'感觉'，而非一开始追求完美工程。【经历】Live Ticketing 先搭 MVP 爬虫验证数据价值再优化；爬虫项目本质就是 vibe-coding；Sentiment Analysis 快速 benchmark 三个模型而非 all-in。【价值】对数字人意味着快速测不同参数/风格/场景，用实际效果指导方向。【需补强】了解 ComfyUI workflow、API 调用等快速原型工具链。",
      },
      {
        category: '项目深挖',
        question:
          "Live Ticketing 项目里你提到 'identified pricing inefficiencies'，你是如何定义和量化它的？对商业决策有什么实际启发？",
        talking_point:
          '【量化】收集座位级价格+售罄、算每场销售速率(6 天变化)；定义 inefficiency = 同等速度下价格偏低/高价快速售罄(可涨价)、或低价滞销(定价过高或营销不足)。发现一场 6 天 80%→97.5% 却没调价=动态定价机会损失；另一场仅 3.7% 但价格中等=问题在营销而非价格。【迁移】方法论可迁到数字人定价(不同质量/风格如何定价最大化价值)，也支撑"用数据说服大客户"。',
      },
      {
        category: '项目深挖',
        question:
          'Sentiment Analysis 最终 precision 86%，但实际业务里这个模型还有哪些局限？要真正用于投资决策你会如何改进？',
        talking_point:
          '【批判】局限：样本偏差(知乎用户不代表整体)、相关≠因果、时滞、黑天鹅。【改进】扩展微博/雪球多源降偏差；用毕业论文的 econometric 方法(工具变量/DID)建因果；升级到小时级数据；结合成交量/换手率做 ensemble。【迁移】这种"不只看成功案例、系统分析失败模式"的思维正对应"探索算法边界"，毕业论文的 heterogeneity / robustness check 就是体现。',
      },
      {
        category: '岗位&公司匹配',
        question:
          '为什么选择数字人这个方向？未来最大的商业机会在哪？作为经济学背景候选人你的优势是什么？',
        talking_point:
          '【Why】技术成熟度(2024-25 快速突破，正从 demo 走向商业化)+内容产业的差异化需求(票务项目看到)+个人对 AI 商业化落地的兴趣。【机会判断】ToB 企业服务(数字代言人/虚拟客服)、内容降本、结合 LLM 的个性化 1 对 1(教育/陪伴)。【经济学优势】商业 sense + 数据驱动评估 + ROI 思维(哪些功能优先、如何定价)，正是创业公司需要的判断力。',
      },
      {
        category: '岗位&公司匹配',
        question: '这是早期创业公司，多变不确定。你为什么选创业公司而非大厂？你适合这种环境吗？',
        talking_point:
          "【Why】成长速度(快速成为核心而非螺丝钉)+直接 impact(与创始团队配合)+技术前沿(团队在 CVPR/NeurIPS 发表)。【适应性证明】独立项目从 idea 到执行自驱、不需 hand-holding；6 天搭爬虫证明快速学习；多次 Team Leader / 带 4 人团队的结果导向；同时推进多项目仍保持 GPA 4.0 的抗压。【价值观】JD 的'聪明、肯花时间、能交付'正是我的工作风格。",
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
