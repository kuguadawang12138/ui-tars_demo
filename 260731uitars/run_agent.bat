@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

REM 优先使用 conda 环境 ui-tars，否则使用 PATH 中的 python
where conda >nul 2>&1
if %ERRORLEVEL%==0 (
    call conda activate ui-tars 2>nul
)

python "%~dp0desktop_agent.py" %*
