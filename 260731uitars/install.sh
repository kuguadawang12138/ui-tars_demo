#!/usr/bin/env bash
# Linux 服务器安装脚本（部署 UI-TARS 模型用）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "安装 UI-TARS 项目依赖 (Linux 服务器)"
echo "项目目录: $SCRIPT_DIR"
echo "========================================"

python3 -m pip install --upgrade pip
python3 -m pip install -r "$SCRIPT_DIR/requirements-server.txt"
python3 -m pip install -e "$SCRIPT_DIR/UI-TARS/codes"

echo ""
echo "安装完成。启动模型服务:"
echo "  bash scripts/start_vllm.sh"
