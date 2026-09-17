#!/usr/bin/env bash
# Start midnight batch process in background with nohup
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

START_AT="${1:-auto-midnight}"
INTERVAL="${2:-300}"

LOG_FILE="outputs/batch_july_august.log"
PID_FILE="outputs/batch_july_august.pid"

mkdir -p outputs

if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if ps -p "${OLD_PID}" > /dev/null 2>&1; then
        echo "⚠️ 批处理任务已在运行中 (PID: ${OLD_PID})。"
        echo "如需查看日志: tail -f ${LOG_FILE}"
        exit 0
    fi
fi

echo "=================================================="
echo "启动 7月/8月 模玩日报夜间批处理后台服务"
echo "启动时间策略: ${START_AT}"
echo "调用间隔: ${INTERVAL} 秒 (5分钟)"
echo "日志文件: ${LOG_FILE}"
echo "=================================================="

nohup env PYTHONPATH=. .venv/bin/python scripts/run_midnight_batch.py \
    --start-at "${START_AT}" \
    --interval "${INTERVAL}" \
    > "${LOG_FILE}" 2>&1 &

NEW_PID=$!
echo "${NEW_PID}" > "${PID_FILE}"

echo "✅ 后台进程已成功启动！PID: ${NEW_PID}"
echo "提示: 可通过以下命令查看实时运行日志:"
echo "  tail -f ${LOG_FILE}"
