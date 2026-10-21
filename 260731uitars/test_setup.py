# -*- coding: utf-8 -*-
"""验证 UI-TARS 环境是否正确安装"""

import sys
from pathlib import Path

from project_paths import PROJECT_ROOT, UI_TARS_CODES

# 优先使用项目内嵌的 UI-TARS 源码（上传服务器后无需额外 clone）
if UI_TARS_CODES.is_dir():
    sys.path.insert(0, str(UI_TARS_CODES))


def test_imports():
    """测试核心依赖导入"""
    import pyautogui
    import mss
    from PIL import Image
    from openai import OpenAI
    from ui_tars.action_parser import (
        parse_action_to_structure_output,
        parsing_response_to_pyautogui_code,
    )
    from ui_tars.prompt import COMPUTER_USE_DOUBAO
    print("[OK] 所有依赖导入成功")


def test_action_parser():
    """测试动作解析"""
    from ui_tars.action_parser import (
        parse_action_to_structure_output,
        parsing_response_to_pyautogui_code,
    )

    response = (
        "Thought: 点击桌面\n"
        "Action: click(point='<point>500 400</point>')"
    )
    parsed = parse_action_to_structure_output(
        response,
        factor=1000,
        origin_resized_height=1080,
        origin_resized_width=1920,
        model_type="doubao",
    )
    assert parsed[0]["action_type"] == "click"
    code = parsing_response_to_pyautogui_code(parsed, 1080, 1920)
    assert "pyautogui.click" in code
    print(f"[OK] 动作解析测试通过\n生成代码:\n{code}")


def test_screenshot():
    """测试截图功能"""
    import mss
    from PIL import Image

    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        save_path = PROJECT_ROOT / "test_screenshot.png"
        img.save(save_path)
        print(f"[OK] 截图测试通过，已保存到 {save_path} ({shot.width}x{shot.height})")


def test_prompt():
    """测试 prompt 模板"""
    from ui_tars.prompt import COMPUTER_USE_DOUBAO

    prompt = COMPUTER_USE_DOUBAO.format(
        instruction="打开记事本", language="Chinese"
    )
    assert "打开记事本" in prompt
    assert "click" in prompt
    print("[OK] Prompt 模板测试通过")


if __name__ == "__main__":
    print("=" * 50)
    print("UI-TARS 环境验证")
    print("=" * 50)
    test_imports()
    test_action_parser()
    test_screenshot()
    test_prompt()
    print("\n" + "=" * 50)
    print("所有测试通过！环境已就绪。")
    print("=" * 50)
