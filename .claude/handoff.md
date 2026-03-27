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

## 待完成

- [x] 跑评分并汇报结果 ✅
- [x] Bug fix: `list --min-score` profile_id 不一致 ✅

## Review 备注

- 两轮评分 ✅ 已 review：heuristic 粗筛 + refine API 精评，force_heuristic 参数设计合理，234 tests pass
- 偏好调整 ✅ 已 review：配置已改、旧评分已清零、merge 保护 role_fit
- 待用户操作：跑 `jobpilot score --heuristic` → `--refine 20` → `list --min-score 7`

## CLI 完成报告

> CLI session 完成任务后在这里写摘要，Opus session 会来 review。清空区域表示已读。

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

## 架构约定（CLI 必须遵守）
- frozen dataclass
- connection-per-call SQLite
- adapter 模式
- 不可变对象
- 文件上限 800 行
- 先写测试再实现
