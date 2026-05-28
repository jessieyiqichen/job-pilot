#!/usr/bin/env bash
# 刷新 Vercel demo 的数据快照：从本地真实库生成脱敏快照，可选直接重新部署。
#   bash scripts/refresh_demo.sh           # 只刷新快照
#   bash scripts/refresh_demo.sh --deploy  # 刷新 + vercel --prod 重新部署
#
# 脱敏：清空 profiles（简历原文）和 applications（投递记录），只保留
# jobs + job_scores（公开岗位 + AI 评分）。
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DB="$PROJECT_DIR/data/jobpilot.db"
DEMO_DB="$PROJECT_DIR/web/demo-data/jobpilot.db"

if [ ! -f "$SRC_DB" ]; then
  echo "❌ 找不到本地库：$SRC_DB" >&2
  exit 1
fi

echo "📋 复制快照 → web/demo-data/"
mkdir -p "$(dirname "$DEMO_DB")"
rm -f "$DEMO_DB" "$DEMO_DB-wal" "$DEMO_DB-shm"
cp "$SRC_DB" "$DEMO_DB"

echo "🧹 脱敏（清空 profiles / applications，折叠 WAL）"
sqlite3 "$DEMO_DB" "DELETE FROM profiles; DELETE FROM applications; VACUUM; PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode=DELETE;" >/dev/null
rm -f "$DEMO_DB-wal" "$DEMO_DB-shm"

JOBS=$(sqlite3 "$DEMO_DB" "SELECT COUNT(*) FROM jobs;")
SCORES=$(sqlite3 "$DEMO_DB" "SELECT COUNT(*) FROM job_scores;")
echo "✅ 快照就绪：$JOBS 岗位 / $SCORES 评分（profiles 已清空）"

echo "🧭 导出军师快照 → web/demo-data/advisor.json"
# 基于真实库算诊断+周计划（确定性），有 API key 时顺带生成军师建议。
(cd "$PROJECT_DIR" && python scripts/export_advisor_snapshot.py)

if [ "${1:-}" = "--deploy" ]; then
  echo "🚀 重新部署到 Vercel…"
  (cd "$PROJECT_DIR/web" && vercel --prod --yes)
else
  echo "👉 重新部署：cd web && vercel --prod"
fi
