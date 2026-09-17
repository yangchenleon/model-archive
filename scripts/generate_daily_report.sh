#!/usr/bin/env bash
# Generate Daily Toy News Report from Bilibili video or UP Space URL
# Default UP Space: https://space.bilibili.com/290901588 (嘟嘟模玩丶)
set -euo pipefail

TARGET="${1:-https://space.bilibili.com/290901588/upload/video}"
LIMIT="${2:-1}"
if [ $# -ge 1 ]; then shift; fi
if [ $# -ge 1 ]; then shift; fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found. Creating..."
    python3 -m venv .venv
    .venv/bin/pip install -r tools/requirements.txt
fi

echo "=================================================="
echo "模玩每日速报系统 (Daily Toy News Pipeline)"
echo "目标源: ${TARGET}"
echo "获取条数: ${LIMIT}"
echo "=================================================="

PYTHONPATH=. .venv/bin/python -m tools.daily_pipeline "${TARGET}" --limit "${LIMIT}" "$@"
