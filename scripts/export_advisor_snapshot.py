#!/usr/bin/env python
"""导出军师快照到 web/demo-data/advisor.json 供 Web demo 渲染。

诊断 + 周计划是确定性的，一定生成。军师建议（advice）只在有 API key 时
best-effort 生成；没有 key 就留空，Web 端优雅降级。

用法：
    python scripts/export_advisor_snapshot.py
通常由 scripts/refresh_demo.sh 调用。
"""

import json
from pathlib import Path

from jobpilot import config
from jobpilot.advisor import AdvisorError, diagnose, generate_advice
from jobpilot.db import JobPilotDB
from jobpilot.demo_export import advisor_snapshot
from jobpilot.models import Profile


def main() -> None:
    db = JobPilotDB()
    profile_id = config.DEFAULT_PROFILE_ID

    advice = ""
    if config.ANTHROPIC_API_KEY:
        try:
            profile = db.get_profile(profile_id) or Profile(id=profile_id)
            advice = generate_advice(diagnose(db, profile_id), profile)
            print("✅ 军师建议已用 Claude API 生成")
        except AdvisorError as exc:
            print(f"⚠️  跳过军师建议生成: {exc}")
    else:
        print("ℹ️  无 API key，仅导出确定性诊断 + 周计划（advice 留空）")

    snap = advisor_snapshot(db, profile_id, advice=advice)
    out = Path(__file__).resolve().parent.parent / "web" / "demo-data" / "advisor.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 军师快照已写入 {out}")


if __name__ == "__main__":
    main()
