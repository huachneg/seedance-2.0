# seedance-2.0 skill 安装指南

这个 skill 把火山引擎方舟 Seedance 2.0 视频大模型包装成 Agent 工具，支持文生视频、图生视频（首帧/首尾帧）、视频编辑（参考图/参考视频/参考音频）、以及客户端视频续写。

## 1. 放到 skills 目录

```bash
mkdir -p ~/.claude/skills
cp -r seedance-2.0 ~/.claude/skills/
chmod +x ~/.claude/skills/seedance-2.0/scripts/run.py
```

## 2. 配置 ARK_API_KEY

```bash
mkdir -p ~/.zhc-skills
cat > ~/.zhc-skills/seedance-2.0.env <<'EOF'
ARK_API_KEY=ark-你的-api-key
EOF
chmod 600 ~/.zhc-skills/seedance-2.0.env
```

Key 获取：火山引擎控制台 → 方舟 → API Key 管理。
使用前需要在 [方舟控制台](https://console.volcengine.com/ark/region:ark+ap-southeast-1/openManagement?LLM=%7B%7D&advancedActiveKey=model&tab=ComputerVision) 开通 Seedance 2.0 模型（标准版和 fast 版都要开）。

## 3. 依赖

脚本用 PEP 723 内嵌依赖声明，推荐用 `uv run`（零配置，自动装 SDK）：

```bash
# 装 uv（如果没有）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

或者传统方式：

```bash
pip install "volcengine-python-sdk[ark]>=1.0.0" requests
```

### 可选：ffmpeg

只有用 `--extend-from <video>` 做视频续写功能时需要：

```bash
brew install ffmpeg       # macOS
sudo apt install ffmpeg   # Debian/Ubuntu
```

## 4. 验证

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "一个穿红色连衣裙的女孩在樱花树下旋转，慢镜头" \
  --duration 5 \
  --ratio 9:16 \
  -o ~/Downloads/test.mp4
```

成功后在支持 skills 的 Agent 里提「用 seedance 生成一个...的视频」就会自动触发。

## 文件清单

- `SKILL.md`：Agent 触发文档，包含所有模式模板、参数速查、提示词规范
- `scripts/run.py`：统一 CLI 入口（文生/图生/视频编辑/续写/查询任务）
- `INSTALL.md`：本文件
