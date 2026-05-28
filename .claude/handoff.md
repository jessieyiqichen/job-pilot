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
- Phase 21: greeting 接入 pipeline-all（第 5 个 stage _greeting_stage，对 top N 高分岗生成话术存 data/greetings/，--greeting N 控制，缺模板优雅跳过）（05-28，353 tests）
- Phase 22: greeting 渠道差异化 + 可配置 style guide（boss短+截图配文/xhs自然/email正式带主题+签名；formality 正式度校准；interaction_rules HR互动规则；全在 resume_config.yaml greeting 段，改偏好只动配置）（05-28，354 tests）
- Phase 23: GitHub 招聘渠道适配器（adapters/github_jobs.py，gh search issues 官方API+AI抽取，合规不爬；接入 search/pipeline；broaden_query 去 job-type/城市词防 AND 过窄）（05-28，362 tests）
- Phase 23.5: GitHub 评论抽取（拉 ruanyf/weekly 最新「谁在招人」帖评论一起抽，岗位都在评论里；_latest_thread_number 用 --match title 只匹配月度帖标题避免抓到自荐帖；call_gh_issue_comments via gh api；MAX_THREAD_COMMENTS=30）。机制验证：评论 0→14 条流入 AI；产出随当月帖内容（5月帖多非产品岗被过滤，净增0）（05-28，github 11 tests）
- Phase 24: 策略诊断军师 advisor（advisor.py：诊断层 diagnose 确定性算 6 信号[漏斗/高分岗缺口/停滞/定制覆盖/投递节奏/数据量门槛]+建议层 generate_advice LLM 翻人话，无 key 降级导出 prompt；诚实护栏：投递<ADVISOR_MIN_APPLICATIONS(5) 时改口"先投起来"不硬编转化分析）+ jobpilot advisor 命令 + db.count_jobs_by_status（05-28，378 tests）
- Phase 25: 对话答疑军师 ask（ask.py：gather_context 收集诊断+高分岗+可选岗位，build_ask_prompt 注入真实处境+偏好，结合数据回答 offer/薪资/HR 问题；--job 注入具体 JD+评分；无 key 降级导出 prompt）+ jobpilot ask 命令 + **修复偏好取错源 bug**（advisor/ask 原从 profile.structured 取偏好[空]，改为回退 scorer._load_preferences 读 resume_config.yaml + 修正 key 名 cities→preferred_cities/values→priorities）（05-28，391 tests）
- Phase 26: 投递计划军师 plan（planner.py：build_weekly_plan 确定性算本周投递清单[待投高分岗 scored/tailored 按分排序+ready 标记+理由]+跟进清单[停滞投递按天数倒序]+节奏提示，PLAN_WEEKLY_TARGET 截断；format_plan_markdown 渲染；**纯确定性不烧 API**）+ jobpilot plan 命令（--target 覆盖目标数）（05-28，402 tests）。军师三刀齐：advisor 诊断+ask 答疑+plan 计划
- Phase 27: 军师上 Web demo（demo_export.advisor_snapshot 把诊断+周计划序列化成 JSON+export_advisor_snapshot.py 脚本[有 key 顺带真生成 advice]→web/demo-data/advisor.json；web /advisor 页[headline+信号卡+周计划表+MiniMarkdown 渲染 advice]+NavBar"求职军师"入口；refresh_demo.sh 加导出步；MiniMarkdown 极简组件免依赖）（05-28，408 tests，npm build 1055 页过）→ 已部署 https://web-ten-omega-72.vercel.app/advisor
- Phase 28: 实时对话军师 chat（chat.py：build_system_prompt 把诊断+偏好+高分岗灌进 system，run_chat REPL 维护 messages 历史多轮对话+记忆上文，generate_reply 调 API[system+history]；复用 ask.gather_context grounding；input_fn/output_fn 可注入便于测试；退出词 exit/q/bye/退出；EOF/Ctrl-C 优雅退出；无 key 抛 ChatError 实时对话不降级）+ jobpilot chat 命令（--job 锚定岗位）（05-28，417 tests）。真实端到端：两轮对话记忆生效，第二轮承接第一轮推荐具体岗位
- Phase 29: chat 记忆跨 session 持久化（chat_store.py：load/save/clear_history per-profile JSON 存 data/chats/[gitignored]，原子写，malformed 容错丢弃；run_chat resume=True 默认接续历史，全量存盘+滑动窗口 CHAT_MAX_CONTEXT_MESSAGES(30) 喂 API 控 token；--new 重开）（05-28，428 tests）。真实跨进程烟测：第二次重启准确记起第一次说的"成长空间>薪资"
- Phase 30: 军师主动跟进 followup（followup.py：Commitment(frozen)+extract_commitments[LLM 从对话提取行动意图,JSON]+reconcile_with_applications[投了的自动闭环,确定性]；followup_store.py JSON 持久化；chat 集成：退出自动提取承诺存盘+开场主动提 open 承诺并注入 system；jobpilot followup 命令[列出/--done/--drop]）（05-28，452 tests）。真实端到端：聊"这周投字节+改简历"→退出记下2件→下次开场主动问"做了吗"，直击 0 投递断点
- Phase 31: 认知军师——接入 Nous 认知模型（跨项目集成 cognitive.py：读 ../nous/data/subjects/jessie/cognitive_model_v2.json[9维认知建模]，format_cognitive_prompt 带使用守则[不贴标签/不诊断人格/帮建框架+允许good-enough]；注入 chat/advisor/ask 的 prompt；缺文件优雅降级；COGNITIVE_MODEL_PATH env 可配）（05-28，459 tests）。真实验证：advisor 对 0 投递的诊断从"先投起来"升级为"收敛了标准但没给启动许可"[命中决策架构+高标准盲区]，给 45 分钟倒计时+good-enough 框架，未越界念模型
- Phase 32: 语言风格 voice 闭环（voice.py：VoiceSample[manual/revised/chat]+per-profile JSON 持久化[data/voice/ gitignored]+build_voice_block few-shot 块；greeting build_hook_prompt/build_email_prompt 加 voice 参数注入真实文本范例；jobpilot voice 命令[add/--file/--revised/--list]，冷启动手动加+改后回灌统一入口）（05-28，472 tests）。辨析：Nous 是认知层不解决表达层；few-shot 真实范例 > 抽象风格描述；"每次改话术"的改后版本=最好范例。真实验证：加口语样本后 greeting 钩子句明显更像本人口语

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

### 语言风格 voice 闭环 Phase 32（2026-05-28）

**需求**：用户说军师生成的话术每次都要改，因为不懂她的语言/表达习惯。问 Nous 能否解决/新建功能/从聊天捕捉。

**辨析（关键）**：①Nous 是认知层（怎么想），故意不碰表达层（怎么说），**不直接解决**；但其对话语料是真实语言样本可借。②最有效的不是"描述风格"，是**给真实范例 few-shot**（实证 > 形容词）。③"每次改话术"是金矿——改后版本=最好范例，回灌即可。用户选「手动给真实样本」冷启动。

**方案：voice 闭环三件套** = 冷启动手动样本 + 改后回灌(flywheel) + 生成时 few-shot。统一入口 `jobpilot voice`。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/voice.py` | 新建。VoiceSample(frozen, source=manual/revised/chat) + per-profile JSON 持久化(load/save/add 去重) + build_voice_block(取最近 N 个做 few-shot，带"模仿别用AI腔"指令) |
| `src/jobpilot/config.py` | 新增 VOICE_DIR（data/voice/）|
| `src/jobpilot/ai/greeting.py` | build_hook_prompt/build_email_prompt 加 voice 参数注入；generate_greeting load_samples+build_voice_block 传入 |
| `src/jobpilot/commands/apply_kit.py` | 新增 voice 命令（位置参数 text / --file / --revised / --list）|
| `.gitignore` | data/voice/ |
| `tests/test_voice.py`(+8) + `test_cli_voice.py`(+5) | +13 测试 |

**测试**：459 → 472（+13），全过。**真实对比验证**：加一条口语样本后，同一岗位 boss greeting 钩子句从工程腔（"设计过多个Agent分工协作...定了判断标准"）变得更口语（"我之前做过一个认知建模工具Nous，就是从...抽认知信号"）。区别温和（自我介绍固定+只钩子受影响+单样本），回灌越多越像。

**用法**：`jobpilot voice "<满意的真实话术>"` 冷启动；改完话术 `jobpilot voice "<改后版本>" --revised` 回灌；`jobpilot voice --list` 查看。**可选后续**：①voice 也接 tailor（简历 bullet）②greeting 命令加 --save-revised 直接回灌当前输出的修改 ③从 chat 历史自动抽 voice 样本（source=chat flywheel）。

### 认知军师：接入 Nous 认知模型 Phase 31（2026-05-28）

**需求**：用户说"想了解我怎么想，看 nous 项目"。Nous（../nous）是用户做的认知层 AI 建模——理解人怎么决策、盲区在哪，而非行为层模仿。用户想让军师有这种认知深度。看了她本人的 cognitive_model_v2.json（9 维），它直接解释了 0 投递：不是拖延，是 Decision Architecture（框架收敛才行动）+ Blind Spots（在乎的领域用不可持续高标准、低估 good-enough）。普通行为层 push（"先投"）对她无效。用户选「全面接入」。

**实现（跨项目集成）**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/cognitive.py` | 新建。CognitiveProfile/CognitiveDimension(frozen) + load_cognitive_profile（读 Nous JSON，缺失/corrupt/空→None 优雅降级）+ format_cognitive_prompt（summary+9维 description + **使用守则**：不贴标签/不当面诊断人格/用它调整建议方式[卡住时帮建框架+允许 good-enough]/点到为止）|
| `src/jobpilot/config.py` | 新增 COGNITIVE_MODEL_PATH（默认 ../nous/.../jessie/cognitive_model_v2.json，env 可覆盖）|
| `src/jobpilot/chat.py` `advisor.py` `ask.py` | build_*_prompt 加可选 cognitive 参数（保持纯函数）；run_chat/generate_advice/answer_question load+注入；缺模型退回纯求职 grounding |
| `src/jobpilot/commands/advisor_cmds.py` | advisor/ask 导出 prompt 降级路径也带认知 |
| `tests/test_cognitive.py`(+7) + test_chat fixture mock load | +7 测试 |

**测试**：452 → 459（+7），全过。test_chat fixture 加 mock load_cognitive_profile→None 防读真实模型。**真实验证**：advisor 读真 Nous 模型后，对 0 投递诊断从"先投起来"升级为"收敛了标准但没给自己启动许可"（命中决策架构+高标准盲区），给"45 分钟倒计时/标准是可发出去不是完美"，未越界念模型/贴标签——守则有效。

**设计原则**：单一事实来源在 Nous（job-pilot 只读）；纯函数（build 加 cognitive 参数）+ orchestration 层 load；隐私=两项目都本地、认知模型不入 job-pilot 仓。**可选后续**：①Web 军师页也体现认知洞察 ②Nous 被动收集器已在跑[com.nous.collector]，认知模型会更新，军师自动受益（flywheel）③矛盾检测[stated vs behavioral]直接喂军师戳盲区。

### 军师主动跟进 followup Phase 30（2026-05-28）

**需求**：用户反馈①XHS 渠道高效 ②军师有大空间。选「军师主动跟进」切入——直击用户 0 投递断点（筛了 37 高分岗但没投），把军师从"被动问答"变"主动陪跑"。

**"主动"在 CLI 怎么落地**（务实设计）：
1. **默默记下**：chat 退出时 LLM 从对话提取"行动意图"（投某岗/改简历/联系内推）存成承诺
2. **主动开口**：下次 chat 开场先提 open 承诺"上次你说要做X，做了吗"，不等你问
3. **数据闭环**：承诺关联岗位若已投（applications 有记录）→ 自动标 done，不啰嗦

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/followup.py` | 新建。Commitment(frozen,new/with_status/to_dict/from_dict) + build_extract_prompt + parse_commitments_response(JSON 容错) + extract_commitments(API) + reconcile_with_applications(确定性自动闭环) |
| `src/jobpilot/followup_store.py` | 新建。per-profile JSON 持久化（load/save/add[去重]/update_status/list），存 data/chats/（gitignored）|
| `src/jobpilot/chat.py` | _greet_commitments（开场 reconcile+主动提+注入 system）+ _capture_commitments（退出 LLM 提取存盘，best-effort）接入 run_chat |
| `src/jobpilot/commands/advisor_cmds.py` | 新增 followup 命令（列出 open + 自动闭环 + --done/--drop）|
| `tests/test_followup.py`(+10) + `test_followup_store.py`(+7) + `test_cli_followup.py`(+4) + `test_chat.py`(+3) | +24 测试 |

**测试**：428 → 452（+24），全过。test_chat autouse fixture 加 mock extract_commitments 防退出真调 API。**真实端到端**：聊"这周投字节+改简历项目"→退出提取 2 条承诺（连 due="这周"都抓到）→第二次 chat 开场主动列出问"做了吗"。

**注意**：承诺捕获靠 LLM（退出+1 次 API 调用，无 key 静默跳过）；提取准确度依赖对话清晰度。reconcile 是确定性的（投了自动闭环不依赖 LLM）。**可选后续**：①承诺加真实 due date + 逾期高亮 ②advisor/plan 里也显示待跟进 ③XHS 内推联系方式提取（用户另一个高优方向，未做）。

### chat 记忆跨 session 持久化 Phase 29（2026-05-28）

**需求**：让 chat 成为记得住的长期军师——关掉重开能接着上次聊。

**设计**：全量存盘 + 滑动窗口喂 API（既要长期记忆又控 token）。
- `chat_store.py`：load/save/clear_history(profile_id)，per-profile JSON 存 config.CHATS_DIR（data/chats/，已 gitignore——对话含个人内容不入仓）。原子写（tmp+replace）；load 容错（corrupt JSON / malformed entry 丢弃返回干净 history）
- run_chat 加 `resume`（默认 True）：启动 load_history 接续；每轮 assistant 回复后 save 全量；喂 generate_reply 的是 history[-CHAT_MAX_CONTEXT_MESSAGES(30):] 滑动窗口
- CLI chat 加 `--new`（resume=False，全新对话）

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/chat_store.py` | 新建。chat_file/load_history/save_history/clear_history |
| `src/jobpilot/chat.py` | run_chat 加 resume 参数 + load/save 接入 + 滑动窗口 |
| `src/jobpilot/config.py` | 新增 CHATS_DIR（加 mkdir 循环）+ CHAT_MAX_CONTEXT_MESSAGES(30) |
| `src/jobpilot/cli.py` | chat 命令加 --new |
| `.gitignore` | 加 data/chats/ |
| `tests/test_chat_store.py`（+7）+ `tests/test_chat.py`（+4：持久化/续接/--new/滑动窗口）| +11 测试 |

**测试**：417 → 428（+11），全过。test_chat.py 加 autouse fixture 把 CHATS_DIR 指 tmp 隔离副作用。**真实跨进程烟测**：第一次 run_chat 说"最看重成长空间其次薪资"存盘→第二次独立 run_chat(resume) 载入历史→准确记起。

**军师完整形态（5 命令）**：chat（实时多轮+长期记忆，主力）/ advisor（诊断）/ ask（单问答）/ plan（计划）+ Web /advisor 页。**可选后续**：①旧对话太长时做 summary 压缩（现在是滑动窗口，会丢早期上下文）②chat 上 Web（需后端+key+限流）。

**cli.py 拆分（独立任务，本 session 一并 commit）**：cli.py 从 1270+ 行拆成 63 行壳 + src/jobpilot/commands/*（advisor_cmds/apply_kit/discover/pipeline_cmds/quality），register-at-bottom 模式避免循环导入。428 测试全过共存验证。注：此拆分非军师 Phase 工作，是之前挂的技术债卡被执行，改动出现在工作树后本 session 帮忙提交（独立 refactor commit）。

**README 同步（Phase 24-29 收尾）**：之前的 session 只把 advisor/ask 加进 README，遗漏 chat/plan/Web 军师页。本次补齐：features 加"对话军师"（chat 多轮+记忆/advisor 诊断/plan 计划/ask 单问答）、架构图加 chat.py/planner.py + cli 拆分说明、命令表加 chat/plan 两行、Web dashboard 加 advisor page、测试 badge 391→428。

**需求澄清**：用户原意不是几个独立命令，而是「像 Claude 这样能实时多轮聊、记得上文」的对话军师。之前的 ask 是一问一答无记忆，理解窄了。本 Phase 补上真·多轮对话。载体经询问选定 CLI（Web 实时聊天需后端+API key 上线+防滥用，暂缓）。

**实现**：
- `build_system_prompt(profile, context)` — 把诊断+偏好+高分岗灌进 system prompt，定军师人设（多轮、记上文、讲人话、不知道就说不知道、主动反问）
- `run_chat(db, profile_id, job_id, *, input_fn, output_fn)` — REPL 循环，维护 messages 历史（user/assistant 交替累积=记忆），input_fn/output_fn 可注入便于单测；退出词 exit/q/bye/退出；EOF/Ctrl-C 优雅退出；API 出错丢掉未答 turn 保持 history 一致
- `generate_reply(history, system)` — 调 API（system=人设+grounding, messages=完整历史），ChatError 包装失败
- 复用 ask.gather_context（诊断+top10高分岗+可选岗位）做 grounding；复用 advisor._format_preferences
- **无 key 抛 ChatError**：实时对话不能降级导出 prompt（设计取舍）

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/chat.py` | 新建。ChatError + build_system_prompt + generate_reply + run_chat |
| `src/jobpilot/cli.py` | 新增 chat 命令（薄封装，--job 锚定岗位，output_fn→console.print） |
| `tests/test_chat.py` + `tests/test_cli_chat.py` | +9 测试（系统prompt/多轮历史累积/退出词/空输入跳过/无key/EOF/API契约/CLI封装） |

**测试**：408 → 417（+9），全过（1.6s）。**真实端到端烟测**：注入两轮["海投还是只投高分岗"→"那建议先投哪个"]，记忆生效——第二轮承接第一轮提到的字节/智谱/阿里，挑字节并给理由+末尾反问。质量高、讲人话、点名真实岗位。

**可选后续**：①对话记忆跨 session 持久化（存 data/chats/，"接着上次聊"）②把 chat 也搬上 Web（需后端 serverless+key 上线+限流，用户暂缓）。现在 ask（一次性）+ chat（多轮）并存，chat 是用户真正想要的形态。cli.py 拆分技术债仍挂着（已有独立卡）。

### 军师上 Web demo Phase 27（2026-05-28）

**需求**：军师三刀都在 CLI，作品集 demo（Vercel）看不到。把军师搬上 Web 增强叙事。

**架构难点**：web 是 Next.js（TS），不能调 Python 的 advisor/planner；且 demo 是静态站（零运行时 DB/API）。解法=refresh 期用 Python 算好军师诊断+计划 dump 成静态 JSON，web 只渲染（单一事实来源仍是 Python）。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/demo_export.py` | 新建。advisor_snapshot(db,profile_id,advice) → JSON-safe dict（diagnose+build_weekly_plan 序列化） |
| `scripts/export_advisor_snapshot.py` | 新建。读真实库算快照写 web/demo-data/advisor.json；有 API key 时 best-effort 真生成 advice（无 key 留空，web 优雅降级） |
| `scripts/refresh_demo.sh` | 加导出军师快照步（脱敏后、部署前） |
| `web/lib/advisor.ts` | 类型 + import demo-data/advisor.json |
| `web/components/MiniMarkdown.tsx` | 新建。极简 Markdown 渲染（##/###/**/列表/---），免加 markdown 依赖 |
| `web/app/advisor/page.tsx` | 新建。force-static：headline 卡 + 关键信号卡 + 本周计划表 + MiniMarkdown 渲染 advice + 脱敏说明 |
| `web/app/layout.tsx` | NavBar 加"求职军师" |
| `tests/test_demo_export.py` | +6 测试 |

**测试**：402 → 408（+6），全过。npm run build 通过（/advisor 预渲染为静态，1055 页全生成）。真实 advice 已生成烤入（点出"19 份简历 0 投递=完美准备的坑"，有说服力）。

**注意**：军师快照基于真实库生成（含真实偏好诊断），advice 文本含求职状态（用户已知情同意公开，同 Phase 15）。**待用户**：是否部署上线（cd web && vercel --prod / 或 refresh_demo.sh --deploy）。

### 投递计划军师 Phase 26（2026-05-28）

**需求**：军师第三刀。`jobpilot plan` 给一份本周可执行的投递行动清单。和 advisor 的分工：advisor 诊断"哪里有问题"，plan 给"这周具体投哪几个"。

**关键决策：纯确定性，不烧 API**。"该投哪些/该跟进哪些"完全能从数据算，比 LLM 自由发挥更扛得住追问、更符合"讲实话可执行"。

**逻辑**：
- 本周投递清单 = list_top_scored_jobs(statuses=scored/tailored=未投, min_score>=7) 按分降序，PLAN_WEEKLY_TARGET(默认5) 截断；ready=status=="tailored"（简历已定制）；reason 规则派生（高分优先/简历就绪今天能投/先 tailor）
- 跟进清单 = applied 状态停滞 >= FOLLOWUP_STALE_DAYS，按 days_since 倒序
- note = 待投清单空→提示去 search/score；已达标→提示保持

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/planner.py` | 新建。PlanItem/FollowUpItem/WeeklyPlan（frozen）+ _days_since + build_weekly_plan + format_plan_markdown |
| `src/jobpilot/config.py` | 新增 PLAN_WEEKLY_TARGET(5)，env 可覆盖 |
| `src/jobpilot/cli.py` | 新增 plan 命令（--target/--output） |
| `tests/test_planner.py` + `tests/test_cli_plan.py` | +11 测试 |

**测试**：391 → 402（+11），全过（2.0s）。真实 DB 烟测：profile 10 正确列出 top5 待投高分岗，区分待定制/就绪，给具体动作；0 投递→无跟进区（符合预期）。

**军师全貌（三刀已齐）**：advisor（策略诊断）+ ask（对话答疑）+ plan（投递计划）。情绪支持未单独做，体现在各命令语气规则。可选后续：把 advisor/plan 接进 pipeline-all 末尾自动出周报；或做 jobpilot coach 把三者串成一个交互式入口。cli.py 拆分技术债仍未还。

### 对话答疑军师 Phase 25（2026-05-28）

**需求**：军师第二刀。`jobpilot ask "<问题>"` 结合用户真实处境回答求职问题（offer 接不接/薪资怎么谈/HR 怎么应对），区别于通用 ChatGPT 的点=喂进真实数据。

**设计**：复用 advisor.diagnose 做处境上下文。gather_context 收集 [诊断 + top10 高分岗 + 可选某岗位 JD/评分]，build_ask_prompt 把 [处境 + 偏好 + 高分岗 + 问题] 组装。`--job <id>` 注入具体岗位上下文做针对性回答。honesty 规则：不知道就说不知道、给可执行下一步、350 字内、讲人话。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/ask.py` | 新建。AskContext（frozen）+ gather_context + build_ask_prompt + answer_question（API，无 key 抛 AskError） |
| `src/jobpilot/cli.py` | 新增 ask 命令（位置参数 question + --job/-j 选项），无 key 导出 prompt |
| `src/jobpilot/advisor.py` | **修偏好 bug**：_format_preferences 改为 profile.structured 优先→回退 scorer._load_preferences()（resume_config.yaml 才是真源），并修正 key 名（cities→preferred_cities/values→priorities/salary_floor→min_salary），新增 _PREF_LABELS 映射。ask 复用此函数，一处修两边好 |
| `tests/test_ask.py` + `tests/test_cli_ask.py` | +11 测试 |
| `tests/test_advisor.py` | +2 测试（偏好源优先级 + 回退） |

**测试**：378 → 391（+13），全过（1.9s）。真实 DB 烟测：ask prompt 正确注入 37 个高分岗 + 真实偏好（城市/deal-breaker/看重项全出来了，修 bug 前显示"无偏好记录"）。

**⚠️ 注意**：偏好 bug 同样影响 Phase 24 的 advisor（已提交版本偏好为空），本次一并修复。cli.py 行数继续增长（advisor+ask），cli.py 拆分技术债仍未还（已挂独立任务卡）。

### 策略诊断军师 Phase 24（2026-05-28）

**需求**：用户想把 agent 从"找岗位+面试准备"升级成"求职军师"（策略/计划/答疑/情绪支持）。澄清后选「策略诊断军师」这一刀——护城河最强，因为建立在用户独有的真实求职数据上，不是套壳 ChatGPT。

**核心设计：两层拆分**
- 诊断层 `diagnose()` — 纯确定性数据计算，无 LLM，可测，每个数字 trace 回 DB。这是"扛得住面试官追问"的关键。
- 建议层 `generate_advice()` — 把诊断喂 LLM 翻成人话建议；无 API key 降级导出 prompt（沿用 interview/tailor 模式）。

**6 个诊断信号**：漏斗各环计数 / 高分岗缺口（≥7分共几个 vs 已投几个 vs 已定制几个）/ 停滞投递 / 投递节奏（近 N 天）/ 回音分布 / **数据量诚实护栏**（投递 < ADVISOR_MIN_APPLICATIONS 时 headline 改口"先投起来"，不硬编转化故事）。headline 是规则派生，不靠 LLM。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `src/jobpilot/advisor.py` | 新建。FunnelStage/StrategyDiagnosis（frozen）+ diagnose + format_diagnosis_markdown（规则展示，无 API 可用）+ build_advisor_prompt + generate_advice（API，无 key 抛 AdvisorError） |
| `src/jobpilot/db.py` | 新增 count_jobs_by_status()（一次 GROUP BY） |
| `src/jobpilot/config.py` | 新增 ADVISOR_MIN_APPLICATIONS(5) / ADVISOR_PACE_DAYS(7)，env 可覆盖 |
| `src/jobpilot/cli.py` | 新增 advisor 命令：诊断永远先出→无 key 附导出 prompt / 有 key 出 LLM 建议 |
| `tests/test_advisor.py` + `tests/test_cli_advisor.py` | +16 测试 |

**测试**：362 → 378（+16），全过（3.4s）。真实 DB 烟测：profile 10 当前 0 投递→军师正确输出"37 个高分岗在等，先投起来"，护栏生效未瞎编漏斗分析。

**⚠️ 遗留**：cli.py 已 1214 行，超 800 行上限（接手时已 1098+，本次 +58 加重）。需独立拆分（参考 Phase 5 把 setup 抽到 setup.py 的做法），不在本 feature 内做以免 bloat。

**下一步建议（军师后续刀）**：当前只做了"策略诊断"切片。完整军师还差 ①对话答疑 jobpilot ask（结合数据回答 offer/薪资/HR 问题）②投递计划编排（高分岗排序+follow-up 时间表，与 advisor 有重叠可合并）。情绪支持不单独做，已体现在 headline/advice 的语气规则里。

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
