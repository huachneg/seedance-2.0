---
name: seedance-2.0
description: 火山引擎方舟 Seedance 2.0 视频生成 Skill。当用户提到 Seedance、seedance2.0、豆包视频、doubao-seedance、方舟视频生成，或需求属于文生视频、图生视频（首帧/首尾帧）、视频编辑（替换元素 / 换装 / 换背景 / 换物体 / 运镜保留）、参考图/参考视频驱动生视频，都应该用这个 skill。统一调用 `content_generation.tasks.create`，自动识别三种模式，支持异步轮询、结果下载、本地图片转 data URL 自动提交。
---

# Seedance 2.0 视频生成

火山引擎方舟 Seedance 2.0 视频大模型的统一调用入口。

## 什么时候用

- 用户提到关键词：`seedance`、`Seedance 2.0`、`豆包视频`、`doubao-seedance`、`方舟视频`、`火山 视频生成`
- 需求是下列任意一种：
  - **文生视频**：一段文字生成视频
  - **图生视频**：首帧图/首尾帧图 + 文字 → 视频
  - **视频编辑**：对已有视频做替换/换装/换背景/换物体，保留运镜；或用参考图/参考音频驱动
  - **参考素材驱动**：多个参考图参与生成

不要混用 wan-2.7-gen、其它视频生成 skill。Seedance 是火山引擎 (Volcengine Ark)，和阿里云百炼 (Wan) 完全不同体系。

## 统一脚本

只有一个入口：

```
~/.claude/skills/seedance-2.0/scripts/run.py
```

优先用 `uv run`（脚本内置 PEP 723 依赖声明，零配置自动装 SDK）：

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py <args>
```

如果系统没有 uv：

```bash
pip install "volcengine-python-sdk[ark]" requests
python ~/.claude/skills/seedance-2.0/scripts/run.py <args>
```

## 模式识别（自动，无 `--mode` 参数）

脚本根据你传的输入素材自动判断模式：

| 传入素材 | 识别为 |
|---------|-------|
| 只有 `--prompt` | text-to-video |
| `--first-frame`（可选 `--last-frame`）| image-to-video |
| `--reference-video` 或 `--reference-image` 或 `--reference-audio` | video-edit |

## 调用模板

### 1. 文生视频

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "夜色中的霓虹城市，慢推镜头，电影感" \
  --ratio 16:9 \
  --duration 5 \
  --output ./city.mp4
```

### 2. 图生视频（首帧）

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "女孩回头微笑，然后走向窗边" \
  --first-frame ./portrait.png \
  --duration 5 \
  --output ./portrait.mp4
```

### 3. 图生视频（首尾帧插帧）

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "镜头从近景慢慢拉远，人物走向远方" \
  --first-frame ./start.png \
  --last-frame ./end.png \
  --duration 10 \
  --output ./pull-back.mp4
```

### 4. 视频编辑（替换物体，保留运镜）

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "将视频1礼盒中的香水替换成图片1中的面霜，运镜不变" \
  --reference-video "https://ark-project.tos-cn-beijing.volces.com/doc_video/r2v_edit_video1.mp4" \
  --reference-image "https://ark-project.tos-cn-beijing.volces.com/doc_image/r2v_edit_pic1.jpg" \
  --ratio 16:9 \
  --duration 5 \
  --generate-audio \
  --output ./edited.mp4
```

### 5. 多参考图驱动

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "图1的人物穿图2的衣服，在图3的场景中行走" \
  --reference-image ./person.png \
  --reference-image ./outfit.png \
  --reference-image ./scene.png \
  --output ./dressed.mp4
```

### 6. 带参考音频的视频编辑

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "给视频配上参考音频的音乐节奏" \
  --reference-video "https://.../src.mp4" \
  --reference-audio "https://.../bgm.mp3" \
  --output ./synced.mp4
```

### 7. 只提交不等（异步，返回 task_id）

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "..." \
  --no-wait
# -> task_id=cgt-xxxxxxxx
```

### 8. 查询/轮询已存在的任务

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --task-id cgt-xxxxxxxx \
  --output ./result.mp4
```

### 9. 只看请求 payload，不真调用

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "..." --first-frame ./a.png --dry-run
```

### 10. 视频续写（`--extend-from`，客户端拼接）

Seedance 2.0 本身没有原生「延长视频」接口。脚本用 ffmpeg 抽取原视频尾帧作为 `first_frame`，生成续段后再用 ffmpeg 把原视频 + 续段拼起来。

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "镜头继续推进，人物走向海边" \
  --extend-from ./original.mp4 \
  --duration 5 \
  -o ./extended.mp4
```

- 需要本机安装 `ffmpeg` 和 `ffprobe`（`brew install ffmpeg` / `apt install ffmpeg`）
- 与 `--first-frame` / `--task-id` / `--no-wait` / `--no-download` 互斥
- 拼接用 `-c:v libx264 -c:a aac` 重编码，避免原视频与生成段编码参数不一致导致失败
- 想多段接龙：每次把上一次产物作为下一次的 `--extend-from`

## 参数速查

### 输入素材

| 参数 | 说明 |
|------|------|
| `--prompt`, `-p` | 文本提示词 |
| `--first-frame` | 首帧图（URL 或本地路径，本地路径自动转 data URL） |
| `--last-frame` | 尾帧图（同上） |
| `--reference-image` | 参考图；**可重复传多次**（最多 9 张）；本地路径会转 data URL |
| `--reference-video` | 参考视频 URL；**本地视频不支持**，须先上传到公网（TOS/OSS/CDN） |
| `--reference-audio` | 参考音频 URL；同上 |
| `--extend-from` | 续写已有视频：抽尾帧当 `first_frame`，生成后 ffmpeg 拼接原片+续段。需 ffmpeg |

### 生成参数

| 参数 | 说明 |
|------|------|
| `--model` | 别名 `standard`（默认，质量优先） / `fast`（速度/成本优先）；也可直接传完整 Model ID 或 Endpoint ID `ep-xxxx` |
| `--ratio` | 画面比例：`16:9` / `9:16` / `1:1` / `4:3` / `3:4` / `21:9` / `keep_ratio` / `adaptive` |
| `--duration` | 时长秒数，整数，范围 `4~15`，默认 `5` |
| `--resolution` | 分辨率：`480p` / `720p`（默认） / `1080p`（仅 standard 模型支持） |
| `--fps` | 帧率 |
| `--seed` | 随机种子（用于复现） |
| `--watermark` / `--no-watermark` | 水印开关 |
| `--generate-audio` / `--no-generate-audio` | 生成音频开关（Seedance 2.0 新增） |
| `--camera-fixed` / `--no-camera-fixed` | 锁定镜头（不做运镜） |
| `--callback-url` | 任务完成回调 Webhook |
| `--extra-json` | JSON 对象，合并到顶层参数，用于传脚本未显式支持的新字段 |

### 运行控制

| 参数 | 说明 |
|------|------|
| `--output`, `-o` | 输出 mp4 路径；默认 `./seedance-<时间戳>.mp4` |
| `--task-id` | 轮询已有任务而不是创建新任务 |
| `--dry-run` | 打印 payload 后退出 |
| `--no-wait` | 提交后立刻返回 task_id，不等待 |
| `--no-download` | 任务成功后只打印 URL，不下载 |
| `--poll-interval` | 轮询间隔秒（默认 15） |
| `--poll-timeout` | 轮询超时秒（默认 1800 = 30 分钟） |
| `--json` | 结果以 JSON 输出到 stdout |
| `--quiet` | 静默模式 |

## 多素材 prompt 引用规范

多张参考图 / 参考视频 / 参考音频要让模型正确"对号入座"，在 prompt 里用 **`@图片N` / `@视频N` / `@音频N`** 这类编号引用，序号 **严格按 CLI 传入的顺序**，从 1 开始。

**示例**：

```bash
uv run .../run.py \
  --prompt "让 @图片1 的人物穿上 @图片2 的衣服，在 @图片3 的场景里走动，动作参考 @视频1 的节奏" \
  --reference-image ./person.png \
  --reference-image ./outfit.png \
  --reference-image ./scene.png \
  --reference-video "https://.../motion.mp4"
```

- 第 N 个 `--reference-image` 对应 prompt 里的 `@图片N`（`图片1`/`图片2`/...）
- `--reference-video` 目前只允许 1 个，用 `@视频1`
- `--reference-audio` 目前只允许 1 个，用 `@音频1`
- 视频编辑场景建议也显式写"视频1 里的 X 换成 图片1 里的 Y"，比让模型靠位置推断稳

### 上限（脚本在提交前会校验）

| 类别 | 单次上限 |
|------|---------|
| `reference_image` | 9 |
| `reference_video` | 1（脚本层限制，CLI 只接收一个） |
| `reference_audio` | 1 |
| content 条目总数（prompt + 所有素材） | 12 |

超限会在提交前抛错（不浪费一次 API 调用）。

## 本地素材处理规则

- **图片**（first_frame / last_frame / reference_image）：支持本地路径，自动转成 Base64 `data:` URL 提交，无需手动上传
- **视频 / 音频**：不支持本地文件（Base64 体积过大）。**必须先上传到公网 URL**（火山 TOS、阿里 OSS、Cloudflare R2、公网 CDN 等），再把 URL 传给脚本
- 用户给了本地视频/音频时：告诉他需要先上传，给出 TOS 上传命令示例或建议其用 OSS 控制台拖拽

## API Key 配置

按优先级加载 `ARK_API_KEY`：

1. 进程环境变量
2. `~/.zhc-skills/seedance-2.0.env`（专用，推荐）
3. `~/.zhc-skills/.env`（共享）
4. `./.env`（项目）

创建专用配置：

```bash
mkdir -p ~/.zhc-skills
echo "ARK_API_KEY=ark-your-api-key" > ~/.zhc-skills/seedance-2.0.env
chmod 600 ~/.zhc-skills/seedance-2.0.env
```

Key 获取：火山引擎控制台 → 方舟 → API Key 管理。
需要提前在 [方舟控制台开通 Seedance 2.0 模型](https://console.volcengine.com/ark/region:ark+ap-southeast-1/openManagement?LLM=%7B%7D&advancedActiveKey=model&tab=ComputerVision)。

## 模型选择

| 别名 | 完整 ID | 适用场景 |
|------|---------|---------|
| `standard`（默认） | `doubao-seedance-2-0-260128` | 质量优先：成片、交付、关键镜头 |
| `fast` | `doubao-seedance-2-0-fast-260128` | 速度/成本优先：草稿、试 prompt、批量预览 |

调用示例：

```bash
# 默认就是 standard，不传 --model
uv run ~/.claude/skills/seedance-2.0/scripts/run.py --prompt "..."

# 快速草稿用 fast
uv run ~/.claude/skills/seedance-2.0/scripts/run.py --prompt "..." --model fast
```

**建议流程**：默认 `standard` 直接出成片；只有需要快速试 prompt / 批量预览时才显式切 `fast`。

## 参数选择建议

- **`--ratio`**：
  - 文生视频：默认用 `16:9`（横版）
  - 视频编辑：**强烈建议传** `keep_ratio`，否则可能裁剪原视频
  - 竖屏内容（短视频、手机壁纸）用 `9:16`

### 从用户话里提取比例（严格）

**只识别显式的数字比例**（形如 `N:M`），不要从"横屏/竖屏/小红书封面/抖音"之类的描述词里猜比例，避免多个关键词打架导致尺寸错配。

- 用户 prompt 里出现 `16:9` / `9:16` / `3:4` / `1:1` / `21:9` / `4:3` 等数字比例 → 抽到 `--ratio`，原 prompt 里可以保留也可以剥离
- 用户没给数字比例 → **不传 `--ratio`**，让模型按默认出（文生视频默认横版；图生视频跟首帧；视频编辑想保留原比例传 `keep_ratio`）
- 用户说"竖屏"、"横屏"、"小红书封面"这类口语词而**没带数字** → 不要自动映射，按原 prompt 直接发，必要时反问一句确认目标比例

**示例**：

- 「3:4 的海浪镜头」→ `--ratio 3:4`
- 「生成 9:16 竖屏的城市夜景」→ `--ratio 9:16`
- 「做一个横屏的城市夜景」→ **不抽取**（没给数字），prompt 原样发
- 视频编辑想保留原视频比例 → 显式传 `--ratio keep_ratio`
- **`--duration`**：范围 `4~15` 秒整数，默认 `5`。长视频成本和出错率都更高，用户没明确要求时不要主动超过 `10`
- **`--resolution`**：默认 `720p`（速度/质量平衡）；`standard` 模型支持 `480p/720p/1080p`，`fast` 模型只支持 `480p/720p`；用户明确要求"1080/高清"且使用 standard 模型时才传 `1080p`，预览场景可降到 `480p`
- **`--generate-audio`**：Seedance 2.0 亮点能力，默认开启比较好；若用户只要纯画面（后期配音）再 `--no-generate-audio`
- **`--seed`**：用户说"再来一版一样风格的"才传；随意重新生成时别传
- **`--camera-fixed`**：人像访谈、商品静物展示等不需要运镜的场景传；剧情/叙事场景不要传
- **`--watermark`**：默认跟随模型配置；用户明确要求"去水印"才传 `--no-watermark`

## 执行后的汇报

完成一次调用后，简短告诉用户：

- 用的是哪种模式（text-to-video / image-to-video / video-edit）
- 模型 ID
- 输出保存到哪个路径
- 任务 ID（方便用户在控制台排查或继续轮询）
- 失败时：错误原因 + 排查建议（API Key 错 / 模型未开通 / 触发内容审核 / 素材 URL 不可访问）

## 常见失败

| 现象 | 原因 | 处理 |
|------|------|------|
| `task creation failed: ... 404` | 模型未开通或 Region 不对 | 去控制台开通 Seedance 2.0 |
| `task failed: DataInspectionFailed` 类似字样 | 提示词或素材触发内容审核 | 用中性词重写 prompt，不要无脑重试 |
| `401 / 403` | API Key 无效或未获公测权限 | 检查 Key；申请 Seedance 2.0 公测权限 |
| 本地视频报错 | 脚本不支持本地视频 | 上传到公网 URL 再传 |
| 轮询超时 | 服务排队或任务复杂 | 加大 `--poll-timeout`，或用 `--no-wait` 后续补查 |

## 输出位置规则

**绝不**把生成的视频写到 `~/.claude/` 任何路径下。默认路径是当前工作目录 `./seedance-<时间戳>.mp4`，用户没指定 `--output` 时保持这个行为。如果用户明确说"放到下载"或没有工作目录上下文，用 `~/Downloads/`。
