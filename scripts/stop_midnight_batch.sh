#!/usr/bin/env bash
# Stop the midnight batch daemon process cleanly
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

PID_FILE="outputs/batch_july_august.pid"

if [ ! -f "${PID_FILE}" ]; then
    echo "ℹ️ 未检测到 PID 文件 (${PID_FILE})，尝试通过进程名查找..."
    PIDS=$(pgrep -f "scripts/run_midnight_batch.py" || true)
    if [ -z "${PIDS}" ]; then
        echo "目前没有正在运行的批处理后台进程。"
        exit 0
    fi
else
    PIDS=$(cat "${PID_FILE}")
fi

for PID in ${PIDS}; do
    if ps -p "${PID}" > /dev/null 2>&1; then
        echo "正在终止批处理进程 PID: ${PID}..."
        kill -TERM "${PID}" || true
        sleep 1
        if ps -p "${PID}" > /dev/null 2>&1; then
            echo "强制结束进程 PID: ${PID}..."
            kill -9 "${PID}" || true
        fi
        echo "✅ 进程 ${PID} 已终止。"
    else
        echo "进程 ${PID} 已经不在运行。"
    fi
done

rm -f "${PID_FILE}"
echo "批处理后台守护已停止。"
