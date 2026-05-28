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
- Phase 9: Web Dashboard + job_type过滤 + 来源链接 + 时间筛选 + 防僵尸 + 简历下载（03-27，275 tests）
- Phase 10: 多轮搜索（5轮XHS+websearch，267→274岗位）+ 手动Boss导入7个 + 简历新版生成（03-28）
- Phase 11: 新一轮XHS搜索 6关键词（274→349岗位，+75新增，高分28→37），API精评top20（05-06）
- Phase 12: 全流程自动化 `pipeline-all`（搜索→打分→定制→日报，单命令，stage 隔离失败）+ 偏好持久化 .claude/preferences.md + SessionStart hook 自动注入偏好（05-27，293 tests）
- Phase 13: 日报增强（新增高分岗位 digest 近N天 + 投递跟进提醒 + 修复 report profile_id=1 bug）（05-27，299 tests）
- Phase 14: 邮件 digest + 本地 launchd 定时（notify.py SMTP + generate_digest + pipeline-all --email + digest 命令 + daily_run.sh + plist）（05-28，307 tests）
- Phase 15: Web demo 部署 Vercel（脱敏快照 DB + API force-static/SSG + better-sqlite3 仅 build 期）→ LIVE: https://web-ten-omega-72.vercel.app （05-28）
- Phase 16: 面试准备生成器（ai/interview.py：高分岗+简历→面试题+STAR要点，JSON 结构化，无 API 降级导出 prompt）+ jobpilot interview 命令 + refresh_demo.sh 一键刷新 demo（05-28，320 tests）
- Phase 17: #4 eval 一致性度量（eval.py）+ label 交互式标注（333 tests，校准待真实标签）（05-28）
- Phase 18: README 整体重写 + GitHub topics/badge + demo 增强（详情页烤入定制简历/面试准备样例 + /how-it-works 页）→ redeploy https://web-ten-omega-72.vercel.app （05-28）
- Phase 18.5: API key 配好(.env 自动加载) + 真跑 interview 修 max_tokens 截断 bug + demo 用真实生成内容（05-28，334 tests）
- Phase 19: 借鉴对标项目（get_jobs/boss-agent-cli）→ 打招呼语生成器 + 黑名单/猎头过滤 + GitHub Actions CI + 合规边界声明（05-28，346 tests，覆盖率 77%）
- Phase 20: 个人风格打招呼话术重写（固定自我介绍模板 from resume_config + LLM 只生成钩子 + 风格自检）+ 修复 .env 自动加载导致测试打真实 API 的隔离 bug（conftest 强制 key 空，73s→1.7s）（05-28，350 tests）

## 关键数据

- 总岗位：349（XHS 134 / Boss 161 / Websearch 54）
- 已评分：339（profile 10）
- Score >= 8.0：20 个
- Score >= 7.0：37 个

## 待完成（用户已批准的升级路线图，全选）

- [x] Phase 13: 日报增强（#1 新岗 digest + #2 跟进提醒）
- [x] Phase 14: 定时跑（本地 launchd + 邮件 digest）— #1 调度部分。⚠️ 待用户：填 .env（SMTP 凭证）+ 给定时时间 → 我 launchctl load 并发一封测试邮件
- [x] Phase 16: 面试准备生成器（高分岗+简历 → 面试题+STAR 要点）— #3 完成
- [~] Phase 17: #4 反馈驱动评分校准
  - [x] 17a: `jobpilot eval` 打分一致性度量（eval.py，precision/recall/F1）— 底座完成
  - [x] 17b: 交互式标注入口 `jobpilot label`（y/n/s/q 写 eval_labels.json）— 解锁 eval 的 ground truth
  - [ ] 17c: 真正的权重校准（调 scorer 权重让指标变好）— 现在已解锁（用户跑 jobpilot label 标够样本后即可做）。需先攒一批标签再动手
- [ ] 待用户：定时器装上（填 .env SMTP + 给时间 → launchctl load + 测试邮件）

## Review 备注

- 两轮评分 ✅ 已 review：heuristic 粗筛 + refine API 精评，force_heuristic 参数设计合理
- 偏好调整 ✅ 已 review：配置已改、旧评分已清零、merge 保护 role_fit

## CLI 完成报告

### 借鉴对标项目 Phase 19（2026-05-28）
调研 GitHub 中国招聘开源项目，对标 loks666/get_jobs(7k⭐ 激进派) + can4hou6joeng4/boss-agent-cli(937⭐ 克制派同类)。落地 4 项：
| 项 | 文件 | 说明 |
|----|------|------|
| 打招呼语生成器 | `ai/greeting.py` + cli `greeting` | 学 get_jobs 的 AI 打招呼，但保持"我们生成、你来发，不自动触达" |
| 黑名单/猎头过滤 | `filters.py` + scorer.score_jobs 接入 | 黑名单硬降权 2.0 / 猎头软降权 4.0，降权而非删除；偏好 blacklist_companies / filter_headhunter |
| GitHub Actions CI | `.github/workflows/ci.yml` | push/PR 跑 346 测试 + 覆盖率(77%)，codecov 上传 |
| 合规边界声明 | README「Compliance & boundaries」 | 本地/只读/不自动投递/不自爬/低频/数据本地 |

**测试 334→346（+12）。** ✅ codecov 已接入（05-28）：用户在 codecov.io 连接仓库 + 加 GitHub Secret `CODECOV_TOKEN`，ci.yml 加 `token: ${{ secrets.CODECOV_TOKEN }}`，CI 上传成功（queued for processing）→ badge 点亮。CI 状态 badge push 后自动生效。
**遗留观察**：测试套件耗时从 ~1.3s 涨到 ~38s（疑似某 anthropic-mock 测试或适配器测试有网络/慢点，未定位）。非阻塞，后续可查 test isolation。

---


> CLI session 完成任务后在这里写摘要，Opus session 会来 review。清空区域表示已读。

### 全流程自动化 + 偏好持久化（2026-05-27）

**需求**：用户要"完全自动化"。澄清后定为——单命令跑 搜索(WebSearch+XHS)→打分→定制简历→日报，投递留人工。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/pipeline.py` | 新建。编排模块：PipelineConfig/StageResult/PipelineResult（frozen dataclass）+ 4 个 stage 函数 + run_pipeline 编排器。每 stage 独立 try/except，单点失败不拖垮全链路 |
| `src/jobpilot/cli.py` | 新增 `pipeline-all` 命令（薄封装，调 pipeline.run_pipeline）。cli.py 未超 800 行因编排逻辑全在 pipeline.py |
| `.claude/preferences.md` | 新建。用户偏好单一事实来源（求职/话术/workflow 三类） |
| `CLAUDE.md` | 顶部加"每 session 必读 preferences.md"强制引用 + CLI 命令表加 pipeline-all + 结构加 pipeline.py |
| `tests/test_pipeline.py` | 新建，16 个单元测试 |
| `tests/test_cli_pipeline_all.py` | 新建，2 个 CLI 集成测试 |

**测试**：275 → 293（+18），全过。

**关键设计**：
- XHS 搜索是 Python 自起 Node 子进程直连 rednote-mcp（非 agent MCP 工具），所以单 CLI 命令能无人值守跑 XHS——前提 cookies 没过期
- `upsert_job` 的 ON CONFLICT 不动 status，重复跑 pipeline 不会把已评分岗位重置回 new，可安全重跑
- 搜索关键词默认从 preferences.career_track 派生（去重+fallback），可 `--keywords` 覆盖
- 打分：全部 new heuristic 秒评 → top N（默认20）API 精评（无 API key 自动跳过精评）
- 定制：top N（默认5）高分未定制岗自动生成 .docx
- **不自动投递**：投递不可逆+反爬，留人工

**待用户确认**：preferences.md 的话术习惯是从对话推断的；是否需要把 pipeline-all 接到 /schedule 做定时 cron（当前是手动触发，符合用户选的"我喊一句就跑"）。

### 偏好自动注入（SessionStart hook，2026-05-27）

**需求**：用户要 agent 每次工作都自动应用偏好，不靠"自觉读文件"。

**实现**：新建 `.claude/settings.json`，加 SessionStart hook，每次 session 开始 `cat $CLAUDE_PROJECT_DIR/.claude/preferences.md` 注入上下文。已 pipe-test（exit 0，全文输出）+ jq 校验通过。

**注意**：本 session 启动时 .claude/ 无 settings 文件，配置 watcher 可能需用户打开一次 `/hooks` 或重启 Claude Code 才加载。hook 本身写法正确。每个新 session 起来会自动带上 preferences.md 全文。

### 日报增强 Phase 13（2026-05-27）

**需求**：用户全选升级路线图。本轮做 #1（新岗 digest）+ #2（跟进提醒）。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/report.py` | 新增 `find_new_high_score_jobs()`（近 N 天发现的高分岗，按 discovered_at 字符串比较过滤）+ `find_stale_applications()`（applied 状态 >= N 天无更新）+ 两个新报告分区。**修复 profile_id=1 bug**：默认改 config.DEFAULT_PROFILE_ID（10），之前日报"推荐投递"恒为空 |
| `src/jobpilot/config.py` | 新增 DEFAULT_PROFILE_ID(10) / NEW_JOB_LOOKBACK_DAYS(1) / FOLLOWUP_STALE_DAYS(7)，均可环境变量覆盖 |
| `src/jobpilot/pipeline.py` | `_report_stage` 传 profile_id=cfg.profile_id（配合 bug 修复） |
| `tests/test_report_digest.py` | 新增 6 个单元测试 |

**测试**：293 → 299（+6），全过。真实 DB 烟测：推荐投递表已正常填充（bug 修复验证），新分区无数据时正确不渲染。

**待 Opus review**：discovered_at 用字符串比较（ISO 格式天然有序，OK）；新岗 digest 复用 list_top_scored_jobs+Python 过滤而非新 SQL（避免重复 SQL）。

### 邮件 digest + 定时调度 Phase 14（2026-05-28）

**需求**：用户选「邮件到 Gmail + 自己定时间」。因 DB/简历是本地且 DB gitignored → 用本地 launchd（非云端 agent）。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/notify.py` | 新建。SMTP 发信（is_configured/send_email），凭证全走 config.SMTP_*（env），EmailNotConfigured 异常 |
| `src/jobpilot/config.py` | 新增 SMTP_HOST/PORT/USER/PASSWORD/TO（env 驱动，默认 gmail 587） |
| `src/jobpilot/report.py` | 新增 generate_digest()→(subject, body) 精简邮件正文（新高分岗+待跟进） |
| `src/jobpilot/cli.py` | pipeline-all 加 --email；新增 digest 命令（预览/发送）；_send_digest_email 辅助 |
| `scripts/daily_run.sh` | launchd wrapper：cd 项目+source .env+jobpilot pipeline-all --platforms websearch --email |
| `scripts/com.jobpilot.daily.plist` | launchd 定时模板，默认 08:00（改 Hour/Minute），日志写 logs/ |
| `.env.example` | 密钥模板（ANTHROPIC + SMTP）|
| `.gitignore` | 加 logs/ |
| `tests/test_notify.py` + `tests/test_report_digest_body.py` | +8 测试 |

**测试**：299 → 307（+8），全过。bash -n + plutil -lint 均通过。digest 预览烟测正常。

**未完成（需用户配合，我无法替做）**：
1. 用户 `cp .env.example .env` 填真实 ANTHROPIC_API_KEY + Gmail 应用专用密码
2. 用户给定时时间 → 改 plist Hour/Minute → `cp` 到 ~/Library/LaunchAgents/ → `launchctl load`
3. 配好后跑 `jobpilot digest --email` 发测试邮件验证
（SMTP 真实发送未端到端测过，只 mock 测了逻辑）

### Web demo 部署 Vercel Phase 15（2026-05-28）

**需求**：用户要部署 Vercel。澄清目的=简历/作品集 live demo（非 live 真实数据）。

**架构冲突 & 解法**：web 原本运行时读本地 SQLite（better-sqlite3，gitignored DB），Vercel serverless 无持久磁盘 → 直接部署是空壳。解法=把冻结快照在 `next build` 时烤成静态站点，运行时零 DB。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `web/demo-data/jobpilot.db` | 脱敏快照（349 岗+339 评分，profiles/applications 清空，WAL 折叠成单文件） |
| `web/lib/db.ts` | 默认路径→打包 demo db（JOBPILOT_DB_PATH 可切回 ../data 本地 live）+ getAllJobIds() |
| `web/app/api/jobs/route.ts`、`stats/route.ts` | force-static |
| `web/app/api/jobs/[id]/route.ts` | force-static + generateStaticParams（349 预渲染） |
| `web/app/api/jobs/[id]/resume{,/check}/route.ts` | force-static + generateStaticParams；demo 不提供下载（check 恒 false） |
| `.gitignore` | logs/、web/demo-data 的 db-wal/shm、web/.vercel |

**部署**：vercel CLI（已登录 jessiechenyiqihahaha），从 web/ `vercel --prod --yes`。
- LIVE: https://web-ten-omega-72.vercel.app （HTTP 200，公开无登录墙，/api/jobs 有数据，/api/stats 漏斗正常，/job/121 200）
- next build 验证 1053 静态页全部生成

**注意**：
- demo 数据冻结（本地 pipeline 不推送）；要更新 demo 需重新 cp+脱敏 web/demo-data/jobpilot.db 再 redeploy
- 公开的是真实 349 岗位+AI 评分/建议（profiles 简历原文已脱敏）；用户已知情同意
- 大脑（pipeline/打分/定制/定时/邮件/MCP）仍全部本地，Vercel 只托管看板 UI

### 面试准备生成器 Phase 16（2026-05-28）

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/ai/interview.py` | 新建。InterviewPrep/InterviewQuestion（frozen）+ build_interview_prompt + parse_interview_response（JSON 容错）+ generate_interview_prep（API，无 key 抛 InterviewPrepError）+ format_markdown。诚实规则：talking_point 必须基于简历真实经历不许编造；可吃 JobScore 的 concerns 做针对性准备 |
| `src/jobpilot/cli.py` | 新增 interview 命令：无 API key 导出 prompt（沿用 tailor 降级模式），有 key 生成+可 -o 存 md |
| `scripts/refresh_demo.sh` | 一键刷新 demo 快照（脱敏），--deploy 顺带 vercel |
| `tests/test_interview.py` + `tests/test_cli_interview.py` | +13 测试 |

**测试**：307 → 320（+13），全过。真实端到端烟测：env 无 API key，走降级导出路径，真实 JD+简历正确注入 prompt（API 路径 mock 单测覆盖）。

**注意**：当前 shell 的 ANTHROPIC_API_KEY 未设置（CLAUDE.md 说已充值，但需在 env/.env 配置才走 API 生成；否则导出 prompt 供 Claude.ai 手动用）。

### #4 第一步：打分一致性 eval Phase 17a（2026-05-28）

**思路**：先度量后校准。校准前必须有"打分准不准"的指标，否则瞎调。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/eval.py` | 新建。load_labels（投递状态 applied/offer=1, rejected=0 + 手动文件覆盖）+ EvalResult（precision/recall/F1/accuracy，零除安全）+ evaluate（混淆矩阵，只算有评分的标注岗） |
| `src/jobpilot/cli.py` | 新增 eval 命令（--threshold/--labels，输出指标+混淆矩阵+低分诊断提示） |
| `.gitignore` | data/eval_labels.json（个人判断不入仓） |
| `tests/test_eval.py` | +7 测试 |

**测试**：320 → 327（+7），全过。eval 无标签时给引导。

**17b 校准 gated**：当前 0 投递 + 无标注文件 → 无 ground truth。下一步需先做"标注入口"（交互式 label 命令 or 预填高/中/低分岗模板让用户快速标 1/0），有了标签 eval 才能跑、校准才有依据。未在无数据时硬造校准逻辑（避免过度工程）。

**已为用户打开**：Anthropic Console API Keys 页（console.anthropic.com/settings/keys）供取 ANTHROPIC_API_KEY 填 .env。

### #4 第二步：交互式标注 jobpilot label Phase 17b（2026-05-28）

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/eval.py` | 加 read_labels_file / write_labels_file（排序稳定 diff，truthy 强转 1/0） |
| `src/jobpilot/cli.py` | 新增 label 命令：逐个岗位 y/n/s/q 标注，跳过已标过的，q 保存退出，merge 写回 |
| `tests/test_cli_label.py` | +6 测试（文件 roundtrip + 交互流 via CliRunner input） |

**测试**：327 → 333（+6），全过。真实端到端：标 4 个高分岗(y/n/y/n)→eval 算出 TP=2/FP=2，precision 50% 并触发"调阈值/权重"诊断。✅ 闭环可用。

**17c 校准下一步建议**：用户先 `jobpilot label` 标 30-50 个（含高/中/低分），跑 `jobpilot eval` 看基线 precision/recall；若 precision 低→scorer 权重偏高估，调 ai/scorer.py 维度权重或 role_fit cap，改完再 eval 对比。校准应是"调-测-对比"循环，由真实指标驱动。

### 新一轮XHS搜索（2026-05-06）

**搜索过程（6 个关键词）**：
| # | 关键词 | 笔记数 | 招聘帖 | 备注 |
|---|--------|--------|--------|------|
| 1 | AI产品经理 实习 2026 | 13 | 15 | 小红书/MiniMax/腾讯/字节/德勤/上海AI Lab |
| 2 | AI产品实习 深圳 招聘 | 14 | 26 | 智谱AI/微软/阿里巴巴/腾讯/字节 |
| 3 | AI产品实习 上海 招聘 | 13 | 22 | 百度/阿里/腾讯/字节/AIGC公司 |
| 4 | 大模型产品 实习 招人 | 13 | 5 | 上海交大MIFA/小红书/模速空间/上海AI Lab |
| 5 | AIGC产品 实习生 招聘 | 11 | 10 | Shopee/网易/携程/HelloTalk/MiniMax |
| 6 | AI创业 产品实习 | 13 | 0+7 | XHS 0招聘帖，websearch回退找到7个 |

**汇总**：274→349 岗位（+75），XHS 66→134（+68），websearch +7
**评分**：75个heuristic秒评 + top 20 API精评
**高分岗位**：28→37（+9新增 >= 7.0）

**新增高分岗位（9 个）**：
| Score | Title | Company | City | Source |
|-------|-------|---------|------|--------|
| 8.5 | AI陪伴产品经理实习生 | 未知AI创业公司 | 上海 | websearch |
| 8.5 | AI产品经理实习生（2026届转正实习） | 上海人工智能实验室 | 上海 | websearch |
| 7.5 | 产品经理 | 腾讯 | 上海/多城市 | xhs |
| 7.5 | AI产品经理 | 腾讯 | 上海/多城市 | xhs |
| 7.5 | AI产品经理实习生 | Oran | 上海闵行 | xhs |
| 7.4 | 营销活动产品实习生 | 携程 | 上海 | xhs |
| 7.2 | AI产品开发测试实习生 | Perfects.AI | 可远程 | websearch |
| 7.1 | AI产品经理实习生（视觉方向） | 百度 | 北京 | xhs |
| 7.0 | AI产品经理 | Top AI 半熟社交平台 | 全国 | xhs |

**账号说明**：cookies 文件 `~/.mcp/rednote/cookies.json` 最后修改 2026-03-27，user ID `6410425e`。无法通过 MCP 程序化确认账号名（无 get_profile 工具），用户需自行确认是否为招工专用账号。

## 架构约定（CLI 必须遵守）
- frozen dataclass
- connection-per-call SQLite
- adapter 模式
- 不可变对象
- 文件上限 800 行
- 先写测试再实现
