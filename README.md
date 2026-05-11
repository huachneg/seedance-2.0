# seedance-2.0 Agent Skill

[中文说明](README.zh-CN.md)

An Agent skill for Volcengine Ark Seedance 2.0 video generation. It provides a single CLI entry point for text-to-video, image-to-video, reference-driven video editing, async polling, result download, and local image-to-data-URL submission.

## Requirements

- Python 3.10+
- `uv` recommended, because `scripts/run.py` includes PEP 723 dependency metadata
- A Volcengine Ark API key with Seedance 2.0 enabled
- Optional: `ffmpeg` and `ffprobe` for `--extend-from` video continuation

Configure your API key:

```bash
mkdir -p ~/.zhc-skills
printf '%s\n' 'ARK_API_KEY=ark-your-api-key' > ~/.zhc-skills/seedance-2.0.env
chmod 600 ~/.zhc-skills/seedance-2.0.env
```

## Installation

### Option 1: One-line install

```bash
npx skills add https://github.com/huachneg/seedance-2.0 --skill seedance-2.0
```

### Option 2: Ask your agent to install it

> Install the `seedance-2.0` Agent skill from `https://github.com/huachneg/seedance-2.0`.
>
> 1. Create the skills directory used by my agent if it does not exist.
> 2. Clone the repository into that skills directory as `seedance-2.0`.
> 3. Verify that `SKILL.md` and `scripts/run.py` exist.
> 4. Make `scripts/run.py` executable.

### Option 3: Manual install

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/huachneg/seedance-2.0.git ~/.claude/skills/seedance-2.0
chmod +x ~/.claude/skills/seedance-2.0/scripts/run.py
```

If your agent uses a different skill directory, replace `~/.claude/skills` with that directory.

## Usage

Text to video:

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "A neon city at night, slow dolly-in, cinematic lighting" \
  --ratio 16:9 \
  --duration 5 \
  --output ./city.mp4
```

Image to video:

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "The character turns back and smiles, then walks toward the window" \
  --first-frame ./portrait.png \
  --duration 5 \
  --output ./portrait.mp4
```

Reference-driven edit:

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "Replace the perfume in video 1 with the cream from image 1, keep camera motion unchanged" \
  --reference-video "https://example.com/source.mp4" \
  --reference-image ./cream.png \
  --ratio 16:9 \
  --duration 5 \
  --output ./edited.mp4
```

Dry run without calling the API:

```bash
uv run ~/.claude/skills/seedance-2.0/scripts/run.py \
  --prompt "A short product shot" \
  --dry-run
```

## Files

- `SKILL.md`: Agent-facing trigger and workflow instructions
- `scripts/run.py`: Unified CLI for generation, polling, download, and continuation
- `INSTALL.md`: Chinese install guide

## Notes

Local images are converted to `data:` URLs automatically. Local video and audio files are intentionally rejected; upload them to a public URL first and pass the URL to `--reference-video` or `--reference-audio`.
