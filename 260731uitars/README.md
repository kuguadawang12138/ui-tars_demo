# UI-TARS 桌面自动化 Agent

**默认连接本地部署的 UI-TARS-1.5-7B 模型**，不依赖外部云端 API。

架构：
```
Windows 本机（desktop_agent.py）          Linux 服务器（vLLM）
  截图 → 发请求 ──────────────────→  UI-TARS-1.5-7B 推理
  解析动作 ← 返回 Thought+Action ←
  pyautogui 执行鼠标键盘
```

## 快速开始

### 1. 服务器：部署 UI-TARS 模型

```bash
# 上传整个项目文件夹到服务器
tar czf uitars.tar.gz 260731uitars/
scp uitars.tar.gz user@server:/opt/

# 服务器上
cd /opt/260731uitars
bash install.sh
bash scripts/start_vllm.sh
```

模型服务地址：`http://服务器IP:8000/v1/`（需要约 24G 显存）

### 2. Windows 本机：安装 Agent

```bat
conda create -n ui-tars python=3.11 -y
conda activate ui-tars
install.bat
copy config.env.example config.env
```

编辑 `config.env`，填入服务器地址：

```env
UI_TARS_PROVIDER=local
UI_TARS_BASE_URL=http://你的服务器IP:8000/v1/
UI_TARS_API_KEY=EMPTY
UI_TARS_MODEL=UI-TARS-1.5-7B
UI_TARS_MODEL_TYPE=doubao
```

### 3. 测试 & 运行

```bat
python desktop_agent.py --test-api
python desktop_agent.py --dry-run --max-steps 5 "打开记事本"
python desktop_agent.py "回到桌面，右击新建记事本，写点AI文字，保存为123"
```

---

## 目录结构

```
260731uitars/
├── desktop_agent.py       # 主程序（自动识别 GLM / UI-TARS 模式）
├── uitars_agent.py        # UI-TARS 本地模型 Prompt + 动作执行
├── glm_prompt.py          # GLM 模式（可选，调试用）
├── glm_parser.py
├── project_paths.py       # 统一项目路径
├── config.env             # 配置文件（勿提交 Git）
├── install.bat / install.sh
├── run_agent.bat / run_agent.sh
├── scripts/start_vllm.sh  # 启动 UI-TARS 模型
└── UI-TARS/               # 官方源码（已内嵌）
```

---

## 配置说明

| 变量 | 本地 UI-TARS（默认） | 云端 GLM（调试） |
|------|---------------------|-----------------|
| `UI_TARS_PROVIDER` | `local` | `zhipu` |
| `UI_TARS_BASE_URL` | `http://IP:8000/v1/` | 智谱 API 地址 |
| `UI_TARS_API_KEY` | `EMPTY` | 你的 Key |
| `UI_TARS_MODEL` | `UI-TARS-1.5-7B` | `glm-4.6v` |
| `UI_TARS_MODEL_TYPE` | `doubao` | `glm` |

程序根据 `UI_TARS_MODEL_TYPE` 自动选择 Prompt 和动作解析方式：
- `doubao` → UI-TARS 官方格式（`Thought: ... Action: click(...)`）
- `glm` → 智谱 GLM PC Agent 格式

---

## 注意事项

- 路径请使用**纯英文**
- 桌面自动化在 **Windows** 运行，模型推理在 **Linux 服务器** 运行
- 鼠标移到屏幕左上角可紧急停止（pyautogui FAILSAFE）
- 建议单显示器环境
