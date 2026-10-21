# -*- coding: utf-8 -*-
"""
桌面 GUI 自动化 Agent
默认连接本地部署的 UI-TARS 模型（vLLM OpenAI 兼容接口）
也支持智谱 GLM-4.6V 等云端 API（调试用）

用法:
  python desktop_agent.py "你的任务描述"
  python desktop_agent.py --dry-run   # 仅测试 API，不操作鼠标
  python desktop_agent.py --test-api  # 测试模型连通性
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import mss
import pyautogui
from PIL import Image
from openai import OpenAI

from glm_parser import execute_glm_action, parse_glm_pc_response
from glm_prompt import build_glm_pc_messages
from project_paths import CONFIG_ENV, PROJECT_ROOT
from uitars_agent import (
    build_uitars_messages,
    call_uitars_vlm,
    execute_uitars_response,
    is_uitars_finished,
    parse_uitars_response,
)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

MAX_STEPS = 40
HISTORY_IMAGE_LIMIT = 4
# UI-TARS 历史消息保留轮数（每轮 = assistant + 截图）
UITARS_HISTORY_LIMIT = 10

# 各 Provider 默认配置（默认 local = 本地 UI-TARS）
PROVIDER_DEFAULTS = {
    "local": {
        "base_url": "http://127.0.0.1:8000/v1/",
        "model": "UI-TARS-1.5-7B",
        "model_type": "doubao",
        "api_key": "EMPTY",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model": "glm-4.6v",
        "model_type": "glm",
        "api_key": "",
    },
    "volcengine": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-1.5-ui-tars-250328",
        "model_type": "doubao",
        "api_key": "",
    },
    "huggingface": {
        "base_url": "",
        "model": "tgi",
        "model_type": "qwen25vl",
        "api_key": "",
    },
}


def load_env_file(env_path: Path) -> None:
    """从 .env 文件加载环境变量（不覆盖已有值）"""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def take_screenshot() -> tuple[Image.Image, int, int, str]:
    """截取主屏幕，返回 (PIL图, 宽, 高, base64_data_url)"""
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"
        return img, shot.width, shot.height, data_url


def shrink_image_data_url(data_url: str, scale: float = 0.5) -> str:
    """缩小历史截图以节省 token"""
    if not data_url.startswith("data:"):
        return data_url
    _, b64 = data_url.split(",", 1)
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    new_size = (int(img.width * scale), int(img.height * scale))
    img = img.resize(new_size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"


def call_glm_vlm(client: OpenAI, model: str, messages: list[dict]) -> str:
    """调用智谱 GLM 视觉模型"""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.01,
        max_tokens=2048,
        extra_body={"skip_special_tokens": False},
    )
    return response.choices[0].message.content or ""


def get_config() -> dict:
    """读取运行配置"""
    provider = os.environ.get("UI_TARS_PROVIDER", "local").lower()
    defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["local"])

    api_key = os.environ.get("UI_TARS_API_KEY", defaults.get("api_key", ""))

    return {
        "provider": provider,
        "base_url": os.environ.get("UI_TARS_BASE_URL", defaults["base_url"]),
        "api_key": api_key,
        "model": os.environ.get("UI_TARS_MODEL", defaults["model"]),
        "model_type": os.environ.get("UI_TARS_MODEL_TYPE", defaults["model_type"]),
    }


def is_glm_mode(cfg: dict) -> bool:
    """是否使用 GLM Prompt/解析（云端调试用）"""
    return cfg["provider"] == "zhipu" or cfg["model_type"] == "glm"


def call_vlm(cfg: dict, client: OpenAI, messages: list[dict]) -> str:
    """根据配置调用对应 VLM"""
    if is_glm_mode(cfg):
        return call_glm_vlm(client, cfg["model"], messages)
    return call_uitars_vlm(client, cfg["model"], messages)


def trim_uitars_history(history: list[dict]) -> list[dict]:
    """限制 UI-TARS 历史消息长度"""
    if len(history) <= UITARS_HISTORY_LIMIT * 2:
        return history
    return history[-(UITARS_HISTORY_LIMIT * 2) :]


def run_agent(
    instruction: str,
    dry_run: bool = False,
    max_steps: int = MAX_STEPS,
    start_delay: int = 3,
):
    """运行桌面自动化主循环"""
    cfg = get_config()
    use_glm = is_glm_mode(cfg)

    if not cfg["api_key"]:
        print("=" * 60)
        print("错误：未配置 API Key")
        print("本地 UI-TARS 请在 config.env 中设置 UI_TARS_API_KEY=EMPTY")
        print("=" * 60)
        sys.exit(1)

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])

    # GLM 与 UI-TARS 使用不同的历史格式
    glm_history: list[str] = []
    glm_history_images: list[str] = []
    memory = "[]"
    uitars_history: list[dict] = []

    print(f"任务: {instruction}")
    print(f"Provider: {cfg['provider']} | Model: {cfg['model']}")
    print(f"Model Type: {cfg['model_type']} | Base URL: {cfg['base_url']}")
    if dry_run:
        print("模式: dry-run（仅调用 API，不执行鼠标键盘操作）")
    else:
        print(f"{start_delay} 秒后开始，请勿移动鼠标到屏幕左上角（Failsafe）...")
        time.sleep(start_delay)

    for step in range(1, max_steps + 1):
        print(f"\n{'=' * 44} 步骤 {step}/{max_steps} {'=' * 44}")

        _, w, h, screenshot_url = take_screenshot()

        if use_glm:
            shrunk_history = [
                shrink_image_data_url(u)
                for u in glm_history_images[-HISTORY_IMAGE_LIMIT:]
            ]
            messages = build_glm_pc_messages(
                task=instruction,
                history=glm_history,
                memory=memory,
                history_image_urls=shrunk_history,
                current_image_url=screenshot_url,
            )
        else:
            messages = build_uitars_messages(
                instruction=instruction,
                history=trim_uitars_history(uitars_history),
                screenshot_data_url=screenshot_url,
            )

        # 调用 API，空响应时重试一次
        raw_response = ""
        for attempt in range(2):
            try:
                raw_response = call_vlm(cfg, client, messages)
            except Exception as e:
                print(f"API 调用失败 (尝试 {attempt + 1}/2): {e}")
                if attempt == 1:
                    break
                time.sleep(2)
                continue
            if raw_response.strip():
                break
            print(f"模型返回空响应，重试 ({attempt + 1}/2)...")
            time.sleep(1)

        if not raw_response.strip():
            print("模型连续返回空响应，停止执行")
            break

        print(f"\n--- 模型原始输出 ---\n{raw_response}\n")

        if use_glm:
            parsed = parse_glm_pc_response(raw_response)
            action = parsed.get("action")
            memory = parsed.get("memory", "[]") or "[]"
            print(f"--- 解析动作 ---\n{action}\n")
            print(f"--- Memory ---\n{memory}\n")
            glm_history.append(raw_response)
            glm_history_images.append(screenshot_url)
            if len(glm_history_images) > HISTORY_IMAGE_LIMIT:
                glm_history_images = glm_history_images[-HISTORY_IMAGE_LIMIT:]
        else:
            parsed = parse_uitars_response(raw_response)
            action = parsed.get("action")
            print(f"--- 解析动作 ---\n{action}\n")
            uitars_history.append({"role": "assistant", "content": raw_response})
            uitars_history.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": screenshot_url},
                        }
                    ],
                }
            )

        if dry_run:
            done = False
            if use_glm and action and re.match(r"^DONE\s*\(\s*\)$", action, re.I):
                done = step > 3
            elif not use_glm and is_uitars_finished(raw_response):
                done = step > 3
            if done:
                print("\n[dry-run] 模型返回完成信号，任务结束")
                break
            continue

        if use_glm:
            status = execute_glm_action(action or "", w, h)
        else:
            status = execute_uitars_response(
                raw_response, w, h, model_type=cfg["model_type"]
            )

        time.sleep(0.8)

        if status == "done":
            if step <= 5:
                print(f"[警告] 第 {step} 步返回完成信号，可能过早结束，忽略并继续")
            else:
                print("\n任务完成！")
                break
        if status == "fail":
            print("\n模型判定任务无法完成")
            break
    else:
        print(f"\n已达到最大步数 {max_steps}")


def test_api_connection() -> bool:
    """测试 API 连通性（发送一张截图）"""
    cfg = get_config()
    use_glm = is_glm_mode(cfg)

    print(f"测试连接: {cfg['provider']} / {cfg['model']}")
    print(f"Model Type: {cfg['model_type']}")
    print(f"Base URL: {cfg['base_url']}")

    if not cfg["api_key"]:
        print("错误: 未配置 API Key（本地模型请设 UI_TARS_API_KEY=EMPTY）")
        return False

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    _, w, h, screenshot_url = take_screenshot()

    if use_glm:
        messages = build_glm_pc_messages(
            task="描述当前屏幕上的内容，并输出 left_click(start_box='[500,500]') 格式的测试动作",
            history=[],
            memory="[]",
            history_image_urls=[],
            current_image_url=screenshot_url,
        )
    else:
        messages = build_uitars_messages(
            instruction="描述当前屏幕内容，并输出 click(point='<point>500 500</point>') 格式的测试动作",
            history=[],
            screenshot_data_url=screenshot_url,
        )

    try:
        resp = call_vlm(cfg, client, messages)
        print("\n--- API 响应成功 ---")
        print(resp[:800])
        if use_glm:
            parsed = parse_glm_pc_response(resp)
        else:
            parsed = parse_uitars_response(resp)
        print("\n--- 解析结果 ---")
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        print(f"\nAPI 测试失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="UI-TARS 桌面自动化 Agent")
    parser.add_argument("task", nargs="?", default="", help="任务描述")
    parser.add_argument("--dry-run", action="store_true", help="仅测试 API，不执行操作")
    parser.add_argument("--test-api", action="store_true", help="测试 API 连通性")
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS)
    parser.add_argument("--env-file", default="", help=".env 配置文件路径")
    args = parser.parse_args()

    env_files = [
        Path(args.env_file) if args.env_file else None,
        CONFIG_ENV,
        PROJECT_ROOT / ".env",
    ]
    for ef in env_files:
        if ef and ef.exists():
            load_env_file(ef)
            print(f"已加载配置: {ef}")
            break

    if args.test_api:
        ok = test_api_connection()
        sys.exit(0 if ok else 1)

    task = args.task or "回到桌面，右击鼠标新建一个记事本，写一些关于人工智能的文字，然后保存并重命名为123"
    run_agent(task, dry_run=args.dry_run, max_steps=args.max_steps)


if __name__ == "__main__":
    main()
