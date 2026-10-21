@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

echo ========================================
echo 安装 UI-TARS 桌面 Agent 依赖 (Windows)
echo 项目目录: %~dp0
echo ========================================

python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"
python -m pip install -e "%~dp0UI-TARS\codes"

echo.
echo 安装完成，运行环境检测:
python "%~dp0test_setup.py"
