#!/usr/bin/env bash
# JobPilot 每日自动运行：搜索(websearch) → 打分 → 定制 → 日报 → 发邮件 digest。
# 由 launchd 定时调用（见 scripts/com.jobpilot.daily.plist）。
# 密钥从项目根目录的 .env 读取（.env 已 gitignore，绝不入仓）。
set -euo pipefail

# 项目根目录 = 本脚本所在目录的上一级（避免硬编码绝对路径）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# launchd 的 PATH 很精简，显式加上 jobpilot 所在目录
export PATH="/opt/anaconda3/bin:$PATH"

# 加载密钥（ANTHROPIC_API_KEY + JOBPILOT_SMTP_*）
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.env"
  set +a
fi

mkdir -p logs
echo "==== $(date '+%Y-%m-%d %H:%M:%S') JobPilot daily run ===="
exec jobpilot pipeline-all --platforms websearch --email
