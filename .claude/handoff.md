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

## 关键数据

- 总岗位：349（XHS 134 / Boss 161 / Websearch 54）
- 已评分：339（profile 10）
- Score >= 8.0：20 个
- Score >= 7.0：37 个

## 待完成（用户已批准的升级路线图，全选）

- [x] Phase 13: 日报增强（#1 新岗 digest + #2 跟进提醒）
- [ ] Phase 14: 定时跑（/schedule 把 pipeline-all 接 cron，websearch-only 无人值守）— #1 的调度部分
- [ ] Phase 15: 面试准备生成器（高分岗+简历 → 面试题+STAR 要点）— #3
- [ ] Phase 16: 反馈驱动评分校准（投递/跳过决策 → 调偏好权重）— #4，过度工程风险，克制

## Review 备注

- 两轮评分 ✅ 已 review：heuristic 粗筛 + refine API 精评，force_heuristic 参数设计合理
- 偏好调整 ✅ 已 review：配置已改、旧评分已清零、merge 保护 role_fit

## CLI 完成报告

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
