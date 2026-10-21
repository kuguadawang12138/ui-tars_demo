# -*- coding: utf-8 -*-
from glm_parser import parse_glm_pc_response

tests = [
    "key(keys='win+d')",
    "<tool_call>type(content='新建')",
    "key(keys='win+d')\nMemory: []\n\nright_click(start_box='[500,500]')",
    "<|begin_of_box|>left_click(start_box='[500,400]')<|end_of_box|>\nMemory: []",
    "DONE()\nMemory: []",
]
for t in tests:
    r = parse_glm_pc_response(t)
    print(f"输入: {t[:60]!r}")
    print(f"  -> action: {r['action']!r}, memory: {r['memory']!r}\n")
