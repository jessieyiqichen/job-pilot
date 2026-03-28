# JobPilot 跨 Session 交接记录

**双向读写**：
- **Opus session（规划/review）**：写任务、写 review 结果、读 CLI 的完成报告
- **CLI session（实现）**：读任务、完成后标 ✅ 并写完成报告（改动文件、测试数、注意事项）

CLI session 完成任务后请在对应条目标 ✅，并在「CLI 完成报告」区域写上改动摘要，Opus session 会来读。

---

## 已完成（compact，只保留里程碑）

- Phase 1 MVP: 骨架 + CLI + SQLite + Boss适配器 + 简历解析 + AI打分（03-25，67 tests）
- Phase 2: Web搜索回退 + 启发式打分 + prompt导出（03-25，109 tests）
- Phase 3: 偏好评分 + GitHub链接 + 批量定制 + 投递流程（03-26，143 tests）
- Phase 4: 小红书收藏导入端到端（03-26，179 tests）
- Phase 5: setup问卷 + cli.py拆分 + merge逻辑（03-27，210 tests）
- Phase 6: role_fit 岗位适配度（03-27，226 tests）
- Phase 7: 偏好大调整 + 两轮评分策略（03-27，234 tests）
- Phase 8: 小红书搜索适配器（03-27，262 tests）

## 待完成

- ✅ Web 看板薪资显示修复：226/235 条岗位 salary_min/salary_max 都是 0（数据源问题），修复 `formatSalary()` 让 0 值不显示
- ✅ Web Dashboard 基础搭建（Next.js 16 + Tailwind 4 + echarts，3 页面 + 3 API + 7 组件）
- ✅ job_type 硬性过滤（全部完成）：
  1. ✅ scorer.py — `_heuristic_score()` + `score_job()` API 路径都加了 job_type cap（不匹配→max 3.0 + concern 提示）
  2. ✅ Web 看板 JobFilter — 增加岗位类型筛选下拉（实习/全职/全部），默认选「实习」
  3. ✅ search 命令 — 如果 job_type 有值且搜索关键词中未包含该类型关键词，自动追加（含 intern 英文检测）
- ✅ Web 看板增加来源链接：231/235 条岗位有 source_url（boss→zhipin URL、xhs→小红书链接、websearch→原文链接），卡片上来源标签可直接点击跳转
- ✅ boss-cli 登录失败排查：GitHub Issue #4 已知问题，__zp_stoken__ 被 BOSS 平台反爬机制主动失效。PR #14 尝试修复 cookie profile 但未彻底解决。当前 0.3.6 是最新版。**结论：boss-cli 暂不可用，搜索默认回退 websearch**
- ✅ Web 看板增加时间筛选：FilterState 新增 `timeRange: 'all' | '7d' | '30d' | '90d'`，默认「近30天」，基于 discovered_at ISO 字符串比较过滤
- ✅ Web 详情页薪资显示修复：`{(salary_min || salary_max) && ...}` → `{!!(salary_min || salary_max) && ...}`，防止 React 渲染 0 为文本
- ✅ Web 看板 hydration 错误修复：JobCard 外层从 `<Link>` 改为 `<div>` + `onClick` + `useRouter`，消除 `<a>` 嵌套
- ✅ websearch 防僵尸岗：EXTRACTION_PROMPT 增加时效性指令（优先近期、跳过过期岗位），search() 自动追加当前年份到搜索关键词
- ✅ 多轮搜索补充岗位库（5 轮搜索完成）：
  1. XHS "AI产品经理 实习" — 18 jobs（B站、携程、京东、小红书、月之暗面、ApexMind、西门子等）
  2. XHS "大模型产品 实习 上海" — 4 jobs（MiniMax、麦当劳 Data PM、Kimi）
  3. XHS "AI创业 产品实习" — 0 XHS + 6 websearch 回退（拉勾、Boss直聘、上海AI Lab、阿里千问）
  4. websearch "AI产品经理 实习 上海 2026" — 10 jobs（波克科技、腾讯、飞浆、万兴科技等）
  5. websearch "大模型产品实习 2026" — 0（query 过窄）
  - 新增 32 岗位（235→267），启发式评分 + API 精评 top 20
  - **高分岗位 >= 7.0：21 个**（原 17 → +4 新增：京东、小红书、B站、携程、月之暗面等）

- ✅ Web 看板定制简历下载：岗位详情页显示「下载定制简历」按钮 + 卡片显示「已定制」标签

## Review 备注

- 两轮评分 ✅ 已 review：heuristic 粗筛 + refine API 精评，force_heuristic 参数设计合理，234 tests pass
- 偏好调整 ✅ 已 review：配置已改、旧评分已清零、merge 保护 role_fit
- 待用户操作：跑 `jobpilot score --heuristic` → `--refine 20` → `list --min-score 7`

## CLI 完成报告

> CLI session 完成任务后在这里写摘要，Opus session 会来 review。清空区域表示已读。

### Web Dashboard + 薪资修复（2026-03-27）

**新增文件（18 个）**：
- `web/package.json`, `next.config.ts`, `tsconfig.json`, `postcss.config.mjs` — 配置
- `web/types/job.ts` — JobWithScore, PipelineStats 接口
- `web/lib/db.ts` — 6 个查询函数（getJobsWithScores, getJobDetail, getPipelineCounts, getScoreDistribution, getSourceBreakdown, parseJsonArray）
- `web/app/api/jobs/route.ts`, `web/app/api/jobs/[id]/route.ts`, `web/app/api/stats/route.ts` — 3 个 API
- `web/app/layout.tsx`, `web/app/globals.css`, `web/app/page.tsx` — 布局+首页
- `web/app/job/[id]/page.tsx` — 详情页
- `web/app/pipeline/page.tsx` — 漏斗页
- `web/components/ScoreBadge.tsx`, `JobCard.tsx`, `JobFilter.tsx`, `JobGrid.tsx` — 看板组件
- `web/components/FunnelChart.tsx`, `ScoreDistChart.tsx`, `SourcePieChart.tsx` — 图表组件

**薪资修复**：
- 排查结果：226/235 条岗位 salary_min/salary_max = 0（数据源问题，搜索/导入时没解析薪资）
- 修复 `formatSalary()` — 用 `!min && !max` 替代 `== null`，0 值不再显示为 "0-0K"
- 详情页已用 `||` 判断，0 值本身不会显示

### 来源链接 + 实习筛选（2026-03-27）

**来源链接**（改动文件 6 个）：
- `lib/db.ts` — SQL 加 `j.raw_data`，新增 `extractSourceUrl()` 从 raw_data 提取 URL：
  - boss: `raw_data.encryptJobId` → `https://www.zhipin.com/job_detail/{id}.html`
  - xhs/websearch: `raw_data.source_url` 直接取
- `types/job.ts` — JobWithScore 新增 `source_url: string | null`
- `app/api/jobs/route.ts` + `app/api/jobs/[id]/route.ts` — 返回 source_url
- `app/page.tsx` — Server Component 传递 source_url
- `components/JobCard.tsx` — 来源标签变为 `<a>` 链接（带外链图标，stopPropagation 不影响卡片跳转）
- `app/job/[id]/page.tsx` — 头部卡片新增"查看原文"链接

**实习筛选**（改动文件 2 个）：
- `components/JobFilter.tsx` — FilterState 新增 `jobType: 'all' | 'intern' | 'fulltime'`，新增下拉菜单
- `components/JobGrid.tsx` — 默认 `jobType: 'intern'`，筛选逻辑：title 含"实习"/"intern" 为实习

**验证**：`npm run build` 零错误，API 返回 231/235 条有 source_url

**验证**：
- `npm run build` 零错误
- `/api/jobs` 返回 235 条岗位，最高分 8.5
- `/api/stats` 返回漏斗（已评分225/已定制10）+ 评分分布 + 来源分布
- 首页 HTML 正常渲染

### 跑评分并汇报结果（2026-03-27）

**执行过程**：
1. `score --heuristic --limit 200` — 173 个岗位秒评完成（~2 秒）
2. `score --refine 20 --profile 10` — top 20 API 精评完成（~6.5 分钟）
3. 查询结果：16 个岗位 >= 7.0

**精评 Top 16（score >= 7.0）**：
| Score | Title | Company | City |
|-------|-------|---------|------|
| 8.5 | AI产品实习生 | SpatialWalk（中美双总部） | 深圳 |
| 8.5 | AI产品经理-实习生 | 字节跳动 | 上海 |
| 8.5 | 情感对话专家/NLP工程师 | 自然选择（深圳） | 深圳 |
| 8.5 | AI平台产品开发工程师 | 港中深-人工智能与机器人研究院 | 深圳 |
| 8.5 | AI产品经理 | 自然选择（深圳） | 深圳 |
| 8.5 | AI金融数据产品经理 | 弘量科技 | 深圳 |
| 8.5 | 产品经理实习生 | 智谱华章 | 北京 |
| 8.5 | 人工智能产品经理实习生 | 腾讯 | 深圳 |
| 8.5 | AI产品经理实习生 | 阿里云千问 | 北京/杭州 |
| 8.5 | AI产品和数据分析专员 | 众生互联 | 北京 |
| 8.5 | AI产品实习生 | 临港实验室 | 上海 |
| 8.5 | AI数据产品经理 | Anker | 深圳 |
| 8.5 | AI 产品经理 | 百秋尚美 | 上海 |
| 8.5 | AI产品经理(大模型落地应用) | 智源研究院 | 北京 |
| 7.5 | 大模型产品经理 | 上海人工智能实验室 | 上海 |
| 7.5 | ai产品经理 | 智慧树 | 上海 |

**发现的问题**：
- `list --min-score 7` 命令默认用 `profile_id=1`，但所有评分在 `profile_id=10`，导致结果为空
- 需要给 `list` 命令加 `--profile` 参数或改默认值
- 本次用 Python 直接查 `list_scores_with_jobs(profile_id=10)` 绕过

**观察**：
- 14/20 精评岗位得分 8.5，远高于启发式的 7.0-7.9 — API 评分更精准也更乐观
- 深圳岗位占比高（8/16），上海 4 个，北京 4 个
- 大部分是 AI 产品方向实习/全职，与偏好一致

### Bug fix: list --min-score profile_id（2026-03-27）

**问题**：`list --min-score 7` 调用 `list_scores_with_jobs()` 时用默认 `profile_id=1`，但所有评分在 `profile_id=10`，导致结果为空。

**修复**：
- `src/jobpilot/cli.py` — `list` 命令新增 `--profile` 参数（默认 10，与 score/tailor/apply/pipeline 一致），传给 `list_scores_with_jobs(profile_id=...)`
- `tests/test_cli_score.py` — +2 测试（profile_id 传递 + 默认值验证）

**验证**：`list --min-score 7` 现在正确显示 16 个高分岗位。236 tests all pass。

### 小红书搜索适配器（2026-03-27）

**新增文件**：
- `src/jobpilot/adapters/xhs_search.py` — XHS 搜索适配器（322 行）
  - `XHSSearchAdapter(BaseAdapter)` — `search --platform xhs` 入口
  - `call_mcp_search()` — Node.js subprocess 调用 rednote-mcp 的 `search_notes` MCP tool
  - `_parse_notes_text()` — 解析 rednote-mcp 输出（标题/作者/内容/链接 格式）
  - `_extract_jobs_via_ai()` — Anthropic API 识别招聘帖 + 提取结构化字段
  - `_build_mcp_script()` — 生成 Node.js MCP 客户端脚本
  - `_extract_json_from_text()` — 从 AI 回复中提取 JSON
- `tests/test_adapter_xhs_search.py` — 26 个测试（解析/提取/适配器/AI/错误处理）

**修改文件**：
- `src/jobpilot/config.py` — 新增 `REDNOTE_MCP_PATH` 配置
- `src/jobpilot/cli.py` — search 命令注册 `"xhs": XHSSearchAdapter`

**架构决策**：
- 新建 `xhs_search.py` 而非修改 `xhs.py`（xhs.py 是纯解析模块，不是 adapter）
- 复用 `xhs.py` 的 `parse_xhs_jobs()` 做最终转换
- MCP 通信用 Node.js subprocess + MCP SDK CJS 绝对路径（npm exports map 不暴露 client/stdio 子路径）
- rednote-mcp 需 `--stdio` flag 启动 MCP 服务端模式

**用法**：
```bash
jobpilot search "AI产品经理" --platform xhs --city 上海
```

**验证**：262 tests all pass（+26 新测试）。

### 测试小红书搜索（2026-03-27）

**执行命令**：`jobpilot search "AI产品实习" --platform xhs --city 上海`

**结果**：
- MCP 搜索：13 条小红书笔记（~60 秒）
- AI 识别：16 条招聘帖（从 13 条笔记中提取，有些笔记包含多个岗位）
- 全部存入数据库

**搜索到的岗位**：
| Company | Title | City |
|---------|-------|------|
| 阶跃星辰 | 基模产品实习生 | 上海 |
| 初创AI公司 | Data Analyst/Scientist/Engineer | 上海 |
| 蔚来汽车 | AI agent算法实习生 | 上海 |
| 阶跃星辰 | AI产品实习生 | 上海 |
| AIGC动漫创业 | AIGC产品实习生 | 上海 |
| AMD | AI实习生 | 上海 |
| 字节跳动-TikTok | 产品战略实习生 | 上海 |
| 小红书 | 战略与投资实习生 | 上海 |
| 百度 | AI视频产品实习生 | 北京/上海 |
| 上海AI Lab | 科学实习生/工程师 | 上海 |

**发现并修复的 bug**（3 个）：
1. **分隔符粘连**：rednote-mcp 输出 `---标题:` 无换行，`_parse_notes_text` 只检查 `line == "---"` 导致只解析到第一条。修复：新增 `line.startswith("---标题: ")` 处理
2. **MCP 超时**：MCP SDK 默认请求超时 60s，搜索 15 条需要更久。修复：`callTool()` 传 `{ timeout: 120000 }` 选项
3. **JSON 截断**：AI 输出 13 条笔记的提取结果超过 4096 tokens 被截断。修复：`max_tokens` 提到 8192 + `_extract_json_from_text()` 新增截断恢复逻辑

**账号确认**：cookies 时间戳 2023-03-14（user ID: `6410425e`），cookie 文件最后修改 2026-03-26。⚠️ 无法通过 MCP 直接确认账号名（无 get_profile 工具），需要用户自行确认是否为招工专用账号。

**验证**：264 tests all pass（+2 新测试）。

### 小红书大规模搜索 + API 精评（2026-03-27）

**搜索过程（5 个关键词）**：
| # | 关键词 | 笔记数 | 招聘帖 | 耗时 |
|---|--------|--------|--------|------|
| 1 | AI创业 招聘 | - | 0 | 171s（MCP 超时/AI 未识别） |
| 2 | AI startup 实习 | - | 11 | 130s |
| 3 | AI初创 产品经理 | - | 0 | 178s（MCP 超时/AI 未识别） |
| 4 | 大模型创业 招人 | - | 13 | 141s |
| 5 | AIGC创业 实习 | - | 5 | 95s |

**新增岗位**：29 条（含 Ailoha、ApexMind、FriesAI、Sheet0 等 AI 初创公司）

**过滤规则**：已在 `JOB_EXTRACTION_PROMPT` 中永久加入岗位过滤（过滤后端/前端/全栈/算法/嵌入式/硬件岗，只保留产品/运营/分析/研究/商务/战略/市场）。但上一轮搜索("AI产品实习")已入库的技术岗（如 Software Engineer/Frontend/Backend）未受影响。

**启发式评分**：52 个新岗位已评分（~2 秒）

**API 精评**：`score --refine 20 --profile 10`（~6 分钟）

**最终高分岗位（>= 7.0）**：17 个
| Score | Title | Company | City | Source |
|-------|-------|---------|------|--------|
| 8.5 | AI产品实习生 | SpatialWalk | 深圳 | xhs |
| 8.5 | AI产品经理-实习生 | 字节跳动 | 上海 | websearch |
| 8.5 | 大模型产品经理 | 上海人工智能实验室 | 上海 | websearch |
| 8.5 | AI平台产品开发工程师 | 港中深-AI研究院 | 深圳 | websearch |
| 8.5 | AI产品经理 | 自然选择 | 深圳 | websearch |
| 8.5 | AI金融数据产品经理 | 弘量科技 | 深圳 | boss |
| 8.5 | 产品经理实习生 | 智谱华章 | 北京 | websearch |
| 8.5 | 人工智能产品经理实习生 | 腾讯 | 深圳 | websearch |
| 8.5 | AI产品经理实习生 | 阿里云千问 | 北京/杭州 | xhs |
| 8.5 | AI产品和数据分析专员 | 众生互联 | 北京 | boss |
| 8.5 | AI产品实习生 | 临港实验室 | 上海 | websearch |
| 8.5 | AI数据产品经理 | Anker | 深圳 | boss |
| 8.5 | AI产品经理(大模型落地应用) | 智源研究院 | 北京 | websearch |
| 8.5 | AI陪伴产品经理实习生 | 某创业孵化团队 | 上海 | websearch |
| 8.5 | AgentRun AI产品实习生 | 阿里云 | 上海 | websearch |
| 8.5 | AIGC产品实习生 | AIGC动漫创业公司 | 上海 | xhs |
| 7.5 | AI视频产品实习生 | 百度 | 北京/上海 | xhs |

**XHS 来源高分**：4 个（SpatialWalk、阿里云千问、AIGC动漫创业、百度）

**数据库统计**：
- 总岗位：235（+28 新增 XHS）
- XHS 岗位：50
- 已评分：225
- Score >= 7.0：17
- Score 5.0-6.9：57

**代码改动**：
- `src/jobpilot/adapters/xhs_search.py` — JOB_EXTRACTION_PROMPT 加入岗位过滤规则

### job_type cap + search append + Web 修复（2026-03-27）

**scorer.py job_type 硬性过滤**（改动 1 个文件）：
- `_heuristic_score()` — 在 role_fit cap 之后、suggestion 之前新增 job_type cap 逻辑：
  - 实习偏好 + 岗位无实习/intern 关键词 → `overall = min(overall, 3.0)` + concern
  - 全职偏好 + 岗位有实习/intern 关键词 → `overall = min(overall, 3.0)` + concern
- `score_job()` API 路径 — 同样的 cap 逻辑，在构建 JobScore 前应用
- 新增测试 6 个（`tests/test_scorer_preferences.py::TestJobTypeCapInHeuristic`）

**search 自动追加关键词**（改动 1 个文件）：
- `cli.py search()` — 从 `_load_preferences()` 读 job_type，如果关键词不在 query 中则追加
- 支持 intern 英文检测（query 含 "intern" 时不追加 "实习"）
- 新增测试 5 个（`tests/test_cli_search_append.py`）

**Web 修复**（改动 4 个文件）：
- `job/[id]/page.tsx` — `{(salary || salary)` → `{!!(salary || salary)` 防止 React 渲染 0
- `components/JobCard.tsx` — 外层 `<Link>` → `<div>` + `onClick` + `useRouter`，消除嵌套 `<a>` hydration error
- `components/JobFilter.tsx` — 新增 `timeRange` 筛选（全部/近7天/近30天/近3个月）
- `components/JobGrid.tsx` — 默认 `timeRange: '30d'`，基于 discovered_at ISO 字符串过滤

**boss-cli 排查**：
- GitHub Issue #4 已知问题：__zp_stoken__ 被反爬主动失效
- 当前 0.3.6 是最新版，PR #14 尝试修复但未合入
- **结论：boss-cli 暂不可用**，搜索默认已是 websearch

**验证**：275 tests all pass（+11 新测试），`npm run build` 零错误

### websearch 防僵尸 + 多轮搜索（2026-03-27）

**websearch 防僵尸**（改动 1 个文件）：
- `adapters/websearch.py` — EXTRACTION_PROMPT 增加时效性指令（优先近期、跳过过期岗位、年份 {year} 参数）
- `search()` 方法自动追加当前年份到搜索关键词（如果不在 query 中）

**多轮搜索结果**：
- 5 轮搜索（3 XHS + 2 websearch），新增 32 岗位（235→267）
- 启发式评分 32 个 + API 精评 top 20
- 高分 >= 7.0：21 个（原 17 + 4 新增）
- 新增高分岗位：京东、小红书、B站、携程、月之暗面 Kimi

### Web 看板定制简历下载（2026-03-28）

**新增文件（2 个）**：
- `web/app/api/jobs/[id]/resume/route.ts` — 文件下载 API（构造文件名 → 读取 data/tailored/ → 返回 .docx 流）
- `web/app/api/jobs/[id]/resume/check/route.ts` — 文件存在检查 API（返回 `{ exists, filename }`）

**修改文件（3 个）**：
- `web/lib/db.ts` — 新增 `getJobById(id)` 轻量查询（只取 company + title）
- `web/app/job/[id]/page.tsx` — 新增 `resumeReady` state + `/resume/check` 调用 + 紫色下载按钮（带下载图标）
- `web/components/JobCard.tsx` — `status === 'tailored'` 时显示紫色「已定制」标签（带文档图标）

**文件名构造逻辑**（与 Python tailor.py 一致）：
```
safe_company = company.replace("/", "_").slice(0, 20)
safe_title = title.replace("/", "_").slice(0, 30)
filename = `${safe_company}_${safe_title}.docx`
```

**验证**：`npm run build` 零错误，5 个 API routes（含 2 个新增）

## 架构约定（CLI 必须遵守）
- frozen dataclass
- connection-per-call SQLite
- adapter 模式
- 不可变对象
- 文件上限 800 行
- 先写测试再实现
