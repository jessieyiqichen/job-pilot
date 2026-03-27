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

## 待完成

- [x] 偏好大调整 — 用户不喜欢数据分析和量化研究，更想做 AI 产品方向 ✅（部分完成：配置已改、旧分已清、状态已重置；问卷 + 重新评分待用户交互完成）

## Review 备注

- role_fit 实现 ✅ 已 review：multiplier 方案合理，weak_match hard-cap 5.0，向后兼容，226 tests pass
- 死数据字段（career_stage、previous_track、priorities、learning_goals）— 暂不处理

## CLI 完成报告

> CLI session 完成任务后在这里写摘要，Opus session 会来 review。清空区域表示已读。

### 偏好大调整（2026-03-27）

**改动文件**：
- `data/resume_config.yaml` — preferences 调整：
  - `career_track`: `["AI产品经理", "产品经理", "研究助理"]`（移除"数据分析"）
  - `role_fit.strong_match`: `["AI产品", "产品经理", "产品实习", "研究助理", "产品策划"]`
  - `role_fit.good_match`: `["运营分析", "AI应用", "项目管理", "内容运营"]`
  - `role_fit.weak_match`: `["数据分析", "商业分析", "量化研究", ...]`（数据分析/量化研究从 strong → weak）

**数据库操作**：
- 清除全部 287 条旧评分（DELETE FROM job_scores）
- 重置 173 条 scored → new 状态（UPDATE jobs SET status='new'）

**待用户交互**：
- `jobpilot setup` 需用户在终端交互填写（Bash tool 无法处理 stdin 交互）
- `jobpilot score --limit 200` 重新评分（用户 setup 完成后执行）
- `jobpilot list --min-score 7` 验证高分岗位方向

**测试**：226 tests all pass（无代码改动，仅配置 + 数据变更）

**注意事项**：
- 问卷使用 merge 模式，只覆盖 `_QUESTIONNAIRE_KEYS`，不会丢失 role_fit
- 评分清零后需要用户手动跑 score，因为 score 命令需要 API 或启发式打分

## 架构约定（CLI 必须遵守）
- frozen dataclass
- connection-per-call SQLite
- adapter 模式
- 不可变对象
- 文件上限 800 行
- 先写测试再实现
