#!/usr/bin/env bash
# Linux 下测试 API 连通性（桌面自动化仍需在 Windows 上运行）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 "$SCRIPT_DIR/desktop_agent.py" "$@"
