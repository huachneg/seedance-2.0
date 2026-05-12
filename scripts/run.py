#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "volcengine-python-sdk[ark]>=1.0.0",
#   "requests>=2.31",
# ]
# ///
"""Seedance 2.0 unified CLI.

Single entry point for Volcengine Ark Seedance 2.0 video generation:
text-to-video, image-to-video (first frame / first+last frame), and
video editing (reference image/video/audio). Mode is inferred from
the inputs you supply — you never pass a --mode flag.

Environment:
  ARK_API_KEY    required. Loaded from env or config files (in order):
                 1) process env
                 2) ~/.zhc-skills/seedance-2.0.env
                 3) ~/.zhc-skills/.env
                 4) ./.env
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

MAX_REFERENCE_IMAGES = 9
MAX_REFERENCE_VIDEOS = 3
MAX_REFERENCE_AUDIOS = 3
MAX_TOTAL_CONTENT = 12

# ---- config loading ---------------------------------------------------------

CONFIG_CANDIDATES = [
    Path.home() / ".zhc-skills" / "seedance-2.0.env",
    Path.home() / ".zhc-skills" / ".env",
    Path.cwd() / ".env",
]


def load_env_files() -> None:
    for path in CONFIG_CANDIDATES:
        if not path.is_file():
            continue
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)
        except OSError:
            pass


# ---- input normalization ----------------------------------------------------

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def is_url(value: str) -> bool:
    scheme = urlparse(value).scheme
    return scheme in {"http", "https", "data"}


def to_data_url(path: Path, kind: str) -> str:
    """Convert a local file to a data: URL.

    Images are always converted inline. Video/audio are rejected with a
    clear message because data URLs are impractical for those sizes —
    users must upload to a public URL (TOS, S3, CDN) themselves.
    """
    ext = path.suffix.lower()
    if kind == "image":
        if ext not in IMAGE_EXTS:
            raise SystemExit(f"[error] not a supported image file: {path}")
    elif kind == "video":
        raise SystemExit(
            f"[error] local video input not supported: {path}\n"
            "        upload to a public URL (TOS/S3/CDN) and pass the https URL."
        )
    elif kind == "audio":
        raise SystemExit(
            f"[error] local audio input not supported: {path}\n"
            "        upload to a public URL (TOS/S3/CDN) and pass the https URL."
        )
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def resolve_asset(value: str, kind: str) -> str:
    """Turn a URL or local path into a URL the API accepts."""
    if is_url(value):
        return value
    path = Path(value).expanduser()
    if not path.is_file():
        raise SystemExit(f"[error] {kind} not found: {value}")
    return to_data_url(path, kind)


# ---- content builder --------------------------------------------------------


@dataclass
class ContentPlan:
    prompt: str | None = None
    first_frame: str | None = None
    last_frame: str | None = None
    reference_images: list[str] = field(default_factory=list)
    reference_video: str | None = None
    reference_audio: str | None = None

    def detect_mode(self) -> str:
        if self.reference_video or self.reference_audio or self.reference_images:
            return "video-edit"
        if self.first_frame or self.last_frame:
            return "image-to-video"
        return "text-to-video"

    def validate_limits(self) -> None:
        if len(self.reference_images) > MAX_REFERENCE_IMAGES:
            raise SystemExit(
                f"[error] too many reference images: {len(self.reference_images)} "
                f"(max {MAX_REFERENCE_IMAGES})"
            )
        total = len(self.to_content_array())
        if total > MAX_TOTAL_CONTENT:
            raise SystemExit(
                f"[error] too many content items: {total} (max {MAX_TOTAL_CONTENT})\n"
                "        reduce references or drop the text prompt"
            )

    def to_content_array(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if self.prompt:
            items.append({"type": "text", "text": self.prompt})
        if self.first_frame:
            items.append({
                "type": "image_url",
                "image_url": {"url": self.first_frame},
                "role": "first_frame",
            })
        if self.last_frame:
            items.append({
                "type": "image_url",
                "image_url": {"url": self.last_frame},
                "role": "last_frame",
            })
        for url in self.reference_images:
            items.append({
                "type": "image_url",
                "image_url": {"url": url},
                "role": "reference_image",
            })
        if self.reference_video:
            items.append({
                "type": "video_url",
                "video_url": {"url": self.reference_video},
                "role": "reference_video",
            })
        if self.reference_audio:
            items.append({
                "type": "audio_url",
                "audio_url": {"url": self.reference_audio},
                "role": "reference_audio",
            })
        return items


# ---- top-level parameters ---------------------------------------------------


def build_params(args: argparse.Namespace) -> dict[str, Any]:
    p: dict[str, Any] = {}
    if args.ratio is not None:
        p["ratio"] = args.ratio
    if args.duration is not None:
        p["duration"] = args.duration
    if args.resolution is not None:
        p["resolution"] = args.resolution
    if args.fps is not None:
        p["fps"] = args.fps
    if args.watermark is not None:
        p["watermark"] = args.watermark
    if args.generate_audio is not None:
        p["generate_audio"] = args.generate_audio
    if args.seed is not None:
        p["seed"] = args.seed
    if args.camera_fixed is not None:
        p["camera_fixed"] = args.camera_fixed
    if args.callback_url:
        p["callback_url"] = args.callback_url
    if args.extra_json:
        try:
            extra = json.loads(args.extra_json)
        except json.JSONDecodeError as e:
            raise SystemExit(f"[error] --extra-json is not valid JSON: {e}")
        if not isinstance(extra, dict):
            raise SystemExit("[error] --extra-json must be a JSON object")
        p.update(extra)
    return p


# ---- model aliases ----------------------------------------------------------

MODEL_ALIASES = {
    "standard": "doubao-seedance-2-0-260128",
    "pro": "doubao-seedance-2-0-260128",
    "fast": "doubao-seedance-2-0-fast-260128",
    "lite": "doubao-seedance-2-0-fast-260128",
}


def resolve_model(value: str) -> str:
    return MODEL_ALIASES.get(value.lower(), value)


# ---- SDK wiring -------------------------------------------------------------


def get_client(api_key: str):
    try:
        from volcenginesdkarkruntime import Ark
    except ImportError:
        raise SystemExit(
            "[error] volcengine-python-sdk[ark] is not installed.\n"
            '        install:  pip install "volcengine-python-sdk[ark]"\n'
            '        or:       uv pip install "volcengine-python-sdk[ark]"\n'
            "        (or run this script via `uv run`, which auto-installs deps)"
        )
    return Ark(api_key=api_key)


# ---- polling + download -----------------------------------------------------


def poll_task(client, task_id: str, timeout_s: int, interval_s: int, quiet: bool):
    start = time.time()
    last_status = None
    while True:
        result = client.content_generation.tasks.get(task_id=task_id)
        status = getattr(result, "status", None)
        if status != last_status and not quiet:
            print(f"[{int(time.time() - start):>4}s] status: {status}")
            last_status = status
        if status == "succeeded":
            return result
        if status == "failed":
            err = getattr(result, "error", None)
            raise SystemExit(f"[error] task failed: {err}")
        if status == "cancelled":
            raise SystemExit("[error] task cancelled")
        if time.time() - start > timeout_s:
            raise SystemExit(f"[error] polling timeout after {timeout_s}s (task id: {task_id})")
        time.sleep(interval_s)


def download(url: str, dest: Path, quiet: bool) -> None:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        written = 0
        with dest.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
        if not quiet:
            size_mb = written / (1024 * 1024)
            total_mb = total / (1024 * 1024) if total else 0
            tail = f" ({size_mb:.1f} MB)" if not total else f" ({size_mb:.1f} / {total_mb:.1f} MB)"
            print(f"[download] saved -> {dest}{tail}")


def default_output_path() -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    return Path.cwd() / f"seedance-{ts}.mp4"


# ---- extend-from (ffmpeg-based video continuation) --------------------------


def check_ffmpeg_available() -> None:
    missing = [b for b in ("ffmpeg", "ffprobe") if not shutil.which(b)]
    if missing:
        raise SystemExit(
            f"[error] --extend-from requires {' and '.join(missing)} on PATH\n"
            "        install with: brew install ffmpeg  (macOS)  "
            "or  apt install ffmpeg  (Linux)"
        )


def extract_tail_frame(video: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="seedance-extend-"))
    frame = tmp / "tail.jpg"
    proc = subprocess.run(
        ["ffmpeg", "-sseof", "-0.5", "-i", str(video),
         "-update", "1", "-frames:v", "1", "-q:v", "2", "-y", str(frame)],
        capture_output=True,
    )
    if proc.returncode != 0 or not frame.is_file():
        stderr = proc.stderr.decode(errors="ignore")[-500:]
        raise SystemExit(f"[error] failed to extract tail frame from {video}\n{stderr}")
    return frame


def concat_videos(first: Path, second: Path, dest: Path, quiet: bool) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="seedance-concat-"))
    list_file = tmp / "list.txt"
    list_file.write_text(
        f"file '{first.resolve()}'\nfile '{second.resolve()}'\n",
        encoding="utf-8",
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", "-y", str(dest)],
        capture_output=True,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors="ignore")[-800:]
        raise SystemExit(f"[error] ffmpeg concat failed\n{stderr}")
    if not quiet:
        print(f"[extend] concatenated -> {dest}")


# ---- CLI --------------------------------------------------------------------


def tri_state_flag(parser: argparse.ArgumentParser, name: str, help_text: str) -> None:
    """Add --flag / --no-flag that produce True / False / None (unset)."""
    dest = name.lstrip("-").replace("-", "_")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(f"--{name}", dest=dest, action="store_const", const=True, help=help_text)
    group.add_argument(f"--no-{name}", dest=dest, action="store_const", const=False, help=argparse.SUPPRESS)
    parser.set_defaults(**{dest: None})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seedance-2.0",
        description="Seedance 2.0 video generation CLI (Volcengine Ark).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # text-to-video\n"
            "  run.py --prompt '夜色中霓虹城市的慢推镜头' --ratio 16:9 --duration 5\n\n"
            "  # image-to-video (first frame)\n"
            "  run.py --prompt '女孩回头微笑' --first-frame ./portrait.png\n\n"
            "  # image-to-video (first + last frame interpolation)\n"
            "  run.py --prompt '镜头从近景拉远' --first-frame start.png --last-frame end.png --duration 10\n\n"
            "  # video editing with reference image\n"
            "  run.py --prompt '把礼盒里的香水换成图片1里的面霜，运镜不变' \\\n"
            "         --reference-video https://.../src.mp4 \\\n"
            "         --reference-image https://.../cream.jpg\n\n"
            "  # extend an existing video (tail-frame continuation + ffmpeg concat)\n"
            "  run.py --prompt '继续走向大海' --extend-from ./orig.mp4 -o ./extended.mp4\n\n"
            "  # poll an existing task\n"
            "  run.py --task-id cgt-xxxx\n"
        ),
    )

    # prompt + inputs
    p.add_argument("--prompt", "-p", help="text prompt")
    p.add_argument("--first-frame", help="first-frame image (URL or local path)")
    p.add_argument("--last-frame", help="last-frame image (URL or local path)")
    p.add_argument(
        "--reference-image",
        action="append",
        default=[],
        help="reference image (URL or local path). May be repeated.",
    )
    p.add_argument("--reference-video", help="reference video URL (local files must be uploaded first)")
    p.add_argument("--reference-audio", help="reference audio URL (local files must be uploaded first)")
    p.add_argument(
        "--extend-from",
        help="continue an existing video: extract its tail frame as first_frame, "
             "then concat original + generated segment. requires ffmpeg.",
    )

    # model + generation params
    p.add_argument(
        "--model",
        default="standard",
        help="model alias (standard / fast), full model id, or endpoint id (ep-xxxx). default: standard",
    )
    p.add_argument("--ratio", help="aspect ratio, e.g. 16:9 / 9:16 / 1:1 / 4:3 / 3:4 / 21:9 / keep_ratio / adaptive")
    p.add_argument("--duration", type=int, help="duration in seconds (typically 5 or 10)")
    p.add_argument("--resolution", default="720p", help="resolution: 480p / 720p / 1080p (default: 720p)")
    p.add_argument("--fps", type=int, help="frames per second")
    p.add_argument("--seed", type=int, help="random seed for reproducibility")
    p.add_argument("--callback-url", help="webhook URL to receive task completion")
    p.add_argument("--extra-json", help="JSON object merged into top-level params (forward-compat escape hatch)")
    tri_state_flag(p, "watermark", "toggle watermark (default: provider default)")
    tri_state_flag(p, "generate-audio", "toggle audio generation")
    tri_state_flag(p, "camera-fixed", "lock camera (no motion)")

    # run control
    p.add_argument("--output", "-o", help="output mp4 path (default: ./seedance-<timestamp>.mp4)")
    p.add_argument("--task-id", help="poll an existing task instead of creating a new one")
    p.add_argument("--dry-run", action="store_true", help="print the request payload and exit")
    p.add_argument("--no-wait", action="store_true", help="submit and print task_id, don't poll")
    p.add_argument("--no-download", action="store_true", help="don't download the output video")
    p.add_argument("--poll-interval", type=int, default=15, help="polling interval seconds (default: 15)")
    p.add_argument("--poll-timeout", type=int, default=1800, help="polling timeout seconds (default: 1800)")
    p.add_argument("--json", dest="json_out", action="store_true", help="emit final result as JSON to stdout")
    p.add_argument("--quiet", action="store_true", help="suppress progress output")

    return p


def emit_json(obj: dict[str, Any]) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    load_env_files()
    args = build_parser().parse_args(argv)

    api_key = os.environ.get("ARK_API_KEY")
    if not api_key and not args.dry_run:
        raise SystemExit(
            "[error] ARK_API_KEY is not set.\n"
            "        set it in one of:\n"
            "          export ARK_API_KEY=ark-your-api-key\n"
            "          ~/.zhc-skills/seedance-2.0.env\n"
            "          ~/.zhc-skills/.env\n"
            "          ./.env"
        )

    # handle --extend-from: extract tail frame and use as first_frame
    if args.extend_from:
        if args.task_id:
            raise SystemExit("[error] --extend-from cannot be combined with --task-id")
        if args.no_wait:
            raise SystemExit("[error] --extend-from cannot be combined with --no-wait (need the segment to concat)")
        if args.no_download:
            raise SystemExit("[error] --extend-from cannot be combined with --no-download")
        if args.first_frame:
            raise SystemExit("[error] --extend-from and --first-frame are mutually exclusive")
        source = Path(args.extend_from).expanduser()
        if not source.is_file():
            raise SystemExit(f"[error] --extend-from file not found: {source}")
        check_ffmpeg_available()
        if not args.dry_run:
            if not args.quiet:
                print(f"[extend] extracting tail frame from {source}")
            tail = extract_tail_frame(source)
            args.first_frame = str(tail)

    plan = ContentPlan(
        prompt=args.prompt,
        first_frame=resolve_asset(args.first_frame, "image") if args.first_frame else None,
        last_frame=resolve_asset(args.last_frame, "image") if args.last_frame else None,
        reference_images=[resolve_asset(p, "image") for p in args.reference_image],
        reference_video=resolve_asset(args.reference_video, "video") if args.reference_video else None,
        reference_audio=resolve_asset(args.reference_audio, "audio") if args.reference_audio else None,
    )
    plan.validate_limits()

    # poll-only path
    if args.task_id:
        if args.dry_run:
            raise SystemExit("[error] --task-id and --dry-run are mutually exclusive")
        client = get_client(api_key)
        result = poll_task(client, args.task_id, args.poll_timeout, args.poll_interval, args.quiet)
        return _handle_result(result, args)

    if not plan.prompt and not (plan.first_frame or plan.reference_video):
        raise SystemExit("[error] nothing to generate: provide --prompt and/or input assets")

    mode = plan.detect_mode()
    content = plan.to_content_array()
    params = build_params(args)

    model_id = resolve_model(args.model)
    payload = {"model": model_id, "content": content, **params}

    if not args.quiet:
        print(f"[mode] {mode}")
        print(f"[model] {model_id}" + (f" (alias: {args.model})" if model_id != args.model else ""))

    if args.dry_run:
        emit_json(payload)
        return 0

    client = get_client(api_key)

    if not args.quiet:
        print("[submit] creating task...")
    try:
        create_result = client.content_generation.tasks.create(**payload)
    except Exception as e:
        raise SystemExit(f"[error] task creation failed: {e}")

    task_id = getattr(create_result, "id", None) or getattr(create_result, "task_id", None)
    if not task_id:
        raise SystemExit(f"[error] no task id in response: {create_result!r}")

    if not args.quiet:
        print(f"[submit] task id: {task_id}")

    if args.no_wait:
        if args.json_out:
            emit_json({"task_id": task_id, "mode": mode, "status": "submitted"})
        else:
            print(f"task_id={task_id}")
        return 0

    result = poll_task(client, task_id, args.poll_timeout, args.poll_interval, args.quiet)
    return _handle_result(result, args)


def _extract_video_url(result) -> str | None:
    content = getattr(result, "content", None)
    if content is None:
        return None
    url = getattr(content, "video_url", None)
    if url:
        return url
    if isinstance(content, dict):
        return content.get("video_url")
    return None


def _handle_result(result, args: argparse.Namespace) -> int:
    video_url = _extract_video_url(result)
    task_id = getattr(result, "id", None) or getattr(result, "task_id", None)
    payload_out: dict[str, Any] = {
        "task_id": task_id,
        "status": getattr(result, "status", None),
        "video_url": video_url,
    }

    if not video_url:
        if args.json_out:
            emit_json(payload_out)
        else:
            print("[warn] task completed but no video_url found")
        return 1

    if args.no_download:
        if args.json_out:
            emit_json(payload_out)
        else:
            print(f"video_url={video_url}")
        return 0

    dest = Path(args.output).expanduser() if args.output else default_output_path()
    if dest.is_dir():
        dest = dest / default_output_path().name

    if args.extend_from:
        tmp_dir = Path(tempfile.mkdtemp(prefix="seedance-segment-"))
        segment = tmp_dir / "segment.mp4"
        try:
            download(video_url, segment, args.quiet)
        except Exception as e:
            print(f"[warn] download failed: {e}")
            print(f"video_url={video_url}")
            return 1
        if not args.quiet:
            print(f"[extend] concatenating {args.extend_from} + segment -> {dest}")
        concat_videos(Path(args.extend_from).expanduser(), segment, dest, args.quiet)
        payload_out["segment_path"] = str(segment)
    else:
        try:
            download(video_url, dest, args.quiet)
        except Exception as e:
            print(f"[warn] download failed: {e}")
            print(f"video_url={video_url}")
            return 1

    payload_out["output_path"] = str(dest)
    if args.json_out:
        emit_json(payload_out)
    else:
        print(f"output_path={dest}")
        print(f"video_url={video_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
