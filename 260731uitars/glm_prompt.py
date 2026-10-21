# -*- coding: utf-8 -*-
"""智谱 GLM-4.6V 桌面 GUI Agent Prompt 模板（Windows 版）"""

PC_ACTION_SPACE = """
### {left,right,middle}_click
Call rule: `{left,right,middle}_click(start_box='[x,y]', element_info='')`
Coordinates [x,y] normalized to 0-999 range.

### left_double_click
Call rule: `left_double_click(start_box='[x,y]', element_info='')`

### left_drag
Call rule: `left_drag(start_box='[x1,y1]', end_box='[x2,y2]', element_info='')`

### key
Call rule: `key(keys='ctrl+c')`
Use '+' to separate keys. Common: ctrl+s, ctrl+a, alt+f4, win+d, enter, escape, tab, delete

### type
Call rule: `type(content='要输入的文字')`
Type into the currently focused input field. Use \\n for Enter.

### scroll
Call rule: `scroll(start_box='[x,y]', direction='down', step=5, element_info='')`
direction: 'up' or 'down'

### WAIT
Call rule: `WAIT()`

### DONE
Call rule: `DONE()`

### FAIL
Call rule: `FAIL()`
"""

PC_USER_TEMPLATE_HEAD = """You are a GUI Agent for Windows desktop automation. Your task is to complete the user's request by analyzing screenshots and performing GUI operations. All coordinates use thousandths (0-999) normalized to screen width/height.

# Task:
{task}

# Task Platform
Windows

# Action Space
{action_space}

# Historical Actions and Current Memory
History:"""

PC_USER_TEMPLATE_TAIL = """
Memory:
{memory}

# Output Format
You MUST output exactly ONE action per response. Do NOT output multiple actions.

Format:
<|begin_of_box|>single_action_here<|end_of_box|>
Memory: []

Example (step 1 - go to desktop):
<|begin_of_box|>key(keys='win+d')<|end_of_box|>
Memory: []

Example (step 2 - right click desktop):
<|begin_of_box|>right_click(start_box='[500,500]', element_info='桌面')<|end_of_box|>
Memory: []

IMPORTANT:
- Output ONLY ONE action, then wait for the next screenshot
- Do NOT output DONE until ALL steps are truly completed
- Do NOT plan ahead or output future actions
- Use 0-999 normalized coordinates based on the CURRENT screenshot

# Windows Tips
- Use win+d to show desktop
- Right-click desktop: right_click(start_box='[x,y]')
- Create new file: right-click -> 新建 -> 文本文档
- Notepad save: key(keys='ctrl+s'), then type filename
- Notepad rename in save dialog: type(content='123')
- Execute ONE action per step
- If an action fails, try an alternative approach

Current Screenshot:
"""


def build_glm_pc_messages(
    task: str,
    history: list[str],
    memory: str,
    history_image_urls: list[str],
    current_image_url: str,
) -> list[dict]:
    """构建发送给智谱 API 的消息（PC 模式）"""
    head = PC_USER_TEMPLATE_HEAD.format(task=task, action_space=PC_ACTION_SPACE)
    content: list[dict] = []
    current_text = head

    total_steps = len(history)
    history_image_count = len(history_image_urls)

    for step_idx in range(total_steps):
        step_num = step_idx + 1
        history_response = history[step_idx]
        # 历史记录中只保留动作摘要
        action_line = history_response[:200] if history_response else ""

        if step_idx < total_steps - history_image_count:
            current_text += f"\nstep {step_num}: Screenshot:(Omitted) Action: {action_line}"
        else:
            current_text += f"\nstep {step_num}: Screenshot:"
            content.append({"type": "text", "text": current_text})
            img_idx = step_idx - (total_steps - history_image_count)
            if img_idx < len(history_image_urls):
                content.append(
                    {"type": "image_url", "image_url": {"url": history_image_urls[img_idx]}}
                )
            current_text = f" Action: {action_line}"

    tail = PC_USER_TEMPLATE_TAIL.format(memory=memory or "[]")
    current_text += tail
    content.append({"type": "text", "text": current_text})
    content.append({"type": "image_url", "image_url": {"url": current_image_url}})

    return [{"role": "user", "content": content}]
