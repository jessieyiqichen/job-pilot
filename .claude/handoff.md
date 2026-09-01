# JobPilot 跨 Session 交接

## 项目状态
- **定位**：作品集 + 面试谈资（不是实际求职工具）
- **测试**：532 pass | **数据**：349 岗位（XHS 134 / Boss 161 / Web 54），Score≥7 有 37 个
- **已完成 33 个 Phase**（MVP→搜索→打分→定制→XHS→Web→军师→叙事），功能完整

## 最近完成（09-01）
- ✅ **linkedin adapter**（JobSpy 免登录公开端点，无账号风险）：`adapters/linkedin_jobspy.py` + 10 tests；已注册 pipeline/discover 两处；可选依赖 `pip install -e ".[linkedin]"`；env: JOBPILOT_JOBSPY_SITES/RESULTS/HOURS/COUNTRY/REMOTE
- 用法：`jobpilot search "AI product intern" -p linkedin`；周雷达=cron 跑 pipeline --platforms linkedin

## 待完成
- [ ] 日报功能完善
- [ ] 17c: 评分权重校准（需先 `jobpilot label` 攒标签）
- [ ] 定时器装上（填 .env SMTP + launchctl load）

## 架构约定
- frozen dataclass · connection-per-call SQLite · adapter 模式 · 不可变对象 · 文件<800行 · TDD
