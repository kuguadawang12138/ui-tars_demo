# -*- coding: utf-8 -*-
"""智谱 GLM GUI Agent 响应解析与 pyautogui 动作执行"""

import json
import re
import time
from typing import Any

import pyautogui
import pyperclip

# 坐标归一化范围（智谱 GLM 使用 0-999）
COORD_SCALE = 1000


def parse_glm_pc_response(response: str) -> dict[str, Any]:
    """
    解析 GLM PC 模式响应，只取第一个有效动作。
    支持 <|begin_of_box|>、<tool_call>、纯函数调用等格式。
    """
    if not response:
        return {"action": None, "action_text": "", "memory": "[]"}

    text = response.strip()
    text = re.sub(r"^```(?:json|python)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    action = _extract_first_action(text)

    # 提取 Memory（取最后一个 Memory: 块，避免多动作干扰）
    memory = "[]"
    memory_matches = list(re.finditer(r"Memory:\s*(.*)", text, re.DOTALL))
    if memory_matches:
        raw_mem = memory_matches[-1].group(1).strip()
        # 截断到下一行动作之前
        raw_mem = raw_mem.split("\n")[0].strip()
        if raw_mem:
            memory = raw_mem

    action_text = text
    if action:
        action_text = text[: text.index(action.split("(")[0])].strip() if "(" in action else text

    return {"action": action, "action_text": action_text, "memory": memory}


def _extract_first_action(text: str) -> str | None:
    """从响应中提取第一个有效 GUI 动作"""
    # 1. box token 格式
    box_pattern = r"<\|begin_of_box\|>(.*?)<\|end_of_box\|>"
    box_match = re.search(box_pattern, text, re.DOTALL)
    if box_match:
        return _clean_action_string(box_match.group(1).strip())

    # 2. 精确匹配各类动作（必须带括号）
    action_pattern = re.compile(
        r"(?:<\|?tool_call\|?>\s*)?"
        r"((?:left|right|middle)_click\s*\([^)]*\)"
        r"|left_double_click\s*\([^)]*\)"
        r"|left_drag\s*\([^)]*\)"
        r"|hover\s*\([^)]*\)"
        r"|key\s*\([^)]*\)"
        r"|type\s*\([^)]*\)"
        r"|scroll\s*\([^)]*\)"
        r"|WAIT\s*\(\s*\)"
        r"|DONE\s*\(\s*\)"
        r"|FAIL\s*\(\s*\))",
        re.IGNORECASE,
    )

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Memory:"):
            continue
        m = action_pattern.search(line)
        if m:
            return _clean_action_string(m.group(1))

    m = action_pattern.search(text)
    if m:
        return _clean_action_string(m.group(1))

    return None


def _clean_action_string(action: str) -> str:
    """清理动作字符串中的多余前缀"""
    action = action.strip()
    action = re.sub(r"^<\|?tool_call\|?>\s*", "", action, flags=re.I)
    action = re.sub(r"^Action:\s*", "", action, flags=re.I)
    return action.strip()


def _parse_coord_list(raw: str) -> list[int]:
    """解析 '[500,400]' 或 '(500,400)' 格式的坐标"""
    nums = re.findall(r"-?\d+", raw)
    return [int(n) for n in nums]


def _norm_to_pixel(coord: int, screen_size: int) -> float:
    """0-999 归一化坐标转像素"""
    return coord / COORD_SCALE * screen_size


def _extract_start_box(action: str) -> tuple[float, float] | None:
    """从动作字符串提取 start_box 并转为像素坐标"""
    match = re.search(r"start_box\s*=\s*['\"]?\[([^\]]+)\]['\"]?", action)
    if not match:
        return None
    coords = _parse_coord_list(match.group(1))
    if len(coords) < 2:
        return None
    return coords[0], coords[1]


def _extract_end_box(action: str) -> tuple[float, float] | None:
    """从动作字符串提取 end_box 并转为像素坐标"""
    match = re.search(r"end_box\s*=\s*['\"]?\[([^\]]+)\]['\"]?", action)
    if not match:
        return None
    coords = _parse_coord_list(match.group(1))
    if len(coords) < 2:
        return None
    return coords[0], coords[1]


def _to_pixels(norm_x: float, norm_y: float, width: int, height: int) -> tuple[float, float]:
    return _norm_to_pixel(norm_x, width), _norm_to_pixel(norm_y, height)


def execute_glm_action(
    action: str,
    screen_width: int,
    screen_height: int,
) -> str:
    """
    执行 GLM 动作字符串，返回状态: done / fail / continue
    """
    if not action:
        print(">>> 动作为空，跳过")
        return "continue"

    action = action.strip()
    print(f">>> 执行动作: {action}")

    # 完成 / 失败
    if re.match(r"^DONE\s*\(\s*\)$", action, re.I):
        return "done"
    if re.match(r"^FAIL\s*\(\s*\)$", action, re.I):
        print(">>> 模型判定任务不可完成")
        return "fail"
    if re.match(r"^WAIT\s*\(\s*\)$", action, re.I):
        time.sleep(5)
        return "continue"

    # 点击类动作
    click_actions = {
        "left_click": "left",
        "right_click": "right",
        "middle_click": "middle",
    }
    for act_name, button in click_actions.items():
        if action.startswith(act_name):
            box = _extract_start_box(action)
            if not box:
                print(f">>> 无法解析 {act_name} 坐标")
                return "continue"
            x, y = _to_pixels(box[0], box[1], screen_width, screen_height)
            pyautogui.click(x, y, button=button)
            return "continue"

    if action.startswith("left_double_click"):
        box = _extract_start_box(action)
        if box:
            x, y = _to_pixels(box[0], box[1], screen_width, screen_height)
            pyautogui.doubleClick(x, y)
        return "continue"

    if action.startswith("hover"):
        box = _extract_start_box(action)
        if box:
            x, y = _to_pixels(box[0], box[1], screen_width, screen_height)
            pyautogui.moveTo(x, y)
        return "continue"

    # 拖拽
    if action.startswith("left_drag"):
        start = _extract_start_box(action)
        end = _extract_end_box(action)
        if start and end:
            sx, sy = _to_pixels(start[0], start[1], screen_width, screen_height)
            ex, ey = _to_pixels(end[0], end[1], screen_width, screen_height)
            pyautogui.moveTo(sx, sy)
            pyautogui.drag(ex - sx, ey - sy, duration=0.5, button="left")
        return "continue"

    # 键盘快捷键
    if action.startswith("key("):
        match = re.search(r"keys\s*=\s*['\"]([^'\"]+)['\"]", action)
        if match:
            keys = match.group(1).lower().replace(" ", "").split("+")
            key_map = {
                "ctrl": "ctrl",
                "control": "ctrl",
                "alt": "alt",
                "shift": "shift",
                "win": "win",
                "meta": "win",
                "enter": "enter",
                "return": "enter",
                "esc": "escape",
                "escape": "escape",
                "tab": "tab",
                "delete": "delete",
                "backspace": "backspace",
                "space": "space",
            }
            mapped = [key_map.get(k, k) for k in keys]
            if len(mapped) == 1:
                pyautogui.press(mapped[0])
            else:
                pyautogui.hotkey(*mapped)
        return "continue"

    # 输入文字
    if action.startswith("type("):
        match = re.search(r"content\s*=\s*['\"](.*?)['\"]\s*\)?$", action, re.DOTALL)
        if not match:
            # 尝试更宽松的匹配
            match = re.search(r"content\s*=\s*['\"](.+)", action)
        if match:
            content = match.group(1)
            # 去掉尾部引号和括号
            content = re.sub(r"['\"]?\)?$", "", content)
            content = content.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"')
            pyperclip.copy(content)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.3)
        return "continue"

    # 滚动
    if action.startswith("scroll("):
        box = _extract_start_box(action)
        dir_match = re.search(r"direction\s*=\s*['\"]?(up|down)['\"]?", action)
        step_match = re.search(r"step\s*=\s*(\d+)", action)
        direction = dir_match.group(1) if dir_match else "down"
        step = int(step_match.group(1)) if step_match else 5
        if box:
            x, y = _to_pixels(box[0], box[1], screen_width, screen_height)
            pyautogui.moveTo(x, y)
        clicks = step if direction == "up" else -step
        pyautogui.scroll(clicks)
        return "continue"

    print(f">>> 未识别的动作类型: {action}")
    return "continue"
