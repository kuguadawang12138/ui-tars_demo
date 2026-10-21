# -*- coding: utf-8 -*-
"""项目根目录路径，所有脚本统一从此模块读取（便于打包上传服务器）"""

from pathlib import Path

# 项目根目录（本文件所在目录）
PROJECT_ROOT = Path(__file__).resolve().parent

# UI-TARS 官方源码子目录
UI_TARS_REPO = PROJECT_ROOT / "UI-TARS"
UI_TARS_CODES = UI_TARS_REPO / "codes"

# 默认配置文件
CONFIG_ENV = PROJECT_ROOT / "config.env"
CONFIG_ENV_EXAMPLE = PROJECT_ROOT / "config.env.example"
