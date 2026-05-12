# seedance-2.0 Agent Skill

[English](README.md)

这是一个面向火山引擎方舟 Seedance 2.0 视频大模型的 Agent skill。它提供统一 CLI 入口，支持文生视频、图生视频、参考素材驱动的视频编辑、异步轮询、结果下载，以及本地图片自动转 `data:` URL。

## 使用要求

- Python 3.10+
- 推荐安装 `uv`，因为 `scripts/run.py` 内置 PEP 723 依赖声明
- 已开通 Seedance 2.0 的火山引擎方舟 API Key
- 可选：使用 `--extend-from` 做视频续写时需要 `ffmpeg` 和 `ffprobe`

配置 API Key：

```bash
mkdir -p ~/.zhc-skills
printf '%s\n' 'ARK_API_KEY=ark-your-api-key' > ~/.zhc-skills/seedance-2.0.env
chmod 600 ~/.zhc-skills/seedance-2.0.env
```

## 安装

### 方式一：一行命令安装

```bash
npx skills add https://github.com/huachneg/seedance-2.0 --skill seedance-2.0
```

### 方式二：把下面这段话发给 AI

> 帮我从 `https://github.com/huachneg/seedance-2.0` 安装 `seedance-2.0` 这个 Agent skill。
>
> 1. 确保我的 agent 使用的 skills 目录存在，不存在就创建。
> 2. 把仓库 clone 到该目录下，文件夹名为 `seedance-2.0`。
> 3. 验证目录里存在 `SKILL.md` 和 `scripts/run.py`。
> 4. 给 `scripts/run.py` 添加可执行权限。

### 方式三：手动命令行

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/huachneg/seedance-2.0.git ~/.claude/skills/seedance-2.0
chmod +x ~/.claude/skills/seedance-2.0/scripts/run.py
```

如果你的 agent 使用的不是 `~/.claude/skills`，把它替换成实际的 skill 目录即可。

## 快速使用

文生视频：

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "夜色中的霓虹城市，慢推镜头，电影感" \
  --ratio 16:9 \
  --duration 5 \
  --output ./city.mp4
```

图生视频：

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "人物回头微笑，然后走向窗边" \
  --first-frame ./portrait.png \
  --duration 5 \
  --output ./portrait.mp4
```

参考素材编辑：

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "将视频1里的香水替换成图片1里的面霜，运镜不变" \
  --reference-video "https://example.com/source.mp4" \
  --reference-image ./cream.png \
  --ratio 16:9 \
  --duration 5 \
  --output ./edited.mp4
```

只检查 payload，不调用 API：

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "一个产品展示短片" \
  --dry-run
```

## 文件清单

- `SKILL.md`：Agent 触发文档和完整工作流说明
- `scripts/run.py`：统一 CLI 入口，负责生成、轮询、下载、续写
- `INSTALL.md`：中文安装指南

## 注意

本地图片会自动转成 `data:` URL 提交。本地视频和音频不会内联上传，需要先上传到公网 URL，再传给 `--reference-video` 或 `--reference-audio`。
