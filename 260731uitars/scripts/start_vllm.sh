#!/usr/bin/env bash
# 在 Linux 服务器上启动 UI-TARS-1.5-7B（vLLM OpenAI 兼容接口）
# 需要约 24G 显存，建议单卡 A100/L40S/4090
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 可通过环境变量覆盖
MODEL="${UI_TARS_HF_MODEL:-ByteDance-Seed/UI-TARS-1.5-7B}"
HOST="${UI_TARS_HOST:-0.0.0.0}"
PORT="${UI_TARS_PORT:-8000}"
GPU="${CUDA_VISIBLE_DEVICES:-0}"

echo "========================================"
echo "启动 UI-TARS vLLM 服务"
echo "模型: $MODEL"
echo "地址: http://${HOST}:${PORT}/v1/"
echo "项目: $PROJECT_DIR"
echo "========================================"

export CUDA_VISIBLE_DEVICES="$GPU"

python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --host "$HOST" \
  --port "$PORT" \
  --trust-remote-code \
  --max-model-len 8192 \
  --limit-mm-per-prompt image=5
