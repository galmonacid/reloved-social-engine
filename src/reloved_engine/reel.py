"""Create an Instagram-compatible Reel video from six rendered slides."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image

from reloved_engine.jobs import JobError, load_job

SLIDE_COUNT = 6


class ReelRenderError(RuntimeError):
    """Raised when ffmpeg cannot produce a valid Reel video."""


def reel_slide_paths(job_file: str | Path, post_id: str) -> list[Path]:
    """Return the six approved 9:16 PNG slides used to render a Reel."""
    job = load_job(job_file)
    post = next((item for item in job["posts"] if item["id"] == post_id), None)
    if post is None:
        raise JobError(f"Unknown post ID: {post_id}")
    if post["status"] != "APPROVED":
        raise JobError("Only APPROVED posts can be rendered as Reels")
    directory = Path(job_file).parent / "assets" / post_id / "final"
    paths = [directory / f"slide-{index}.png" for index in range(1, SLIDE_COUNT + 1)]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise JobError(f"Missing Reel slides: {', '.join(missing)}; run reloved overlay first")
    for path in paths:
        try:
            with Image.open(path) as image:
                if image.width / image.height != 9 / 16:
                    raise JobError(f"Reel slide must use a 9:16 aspect ratio: {path}")
        except OSError as error:
            raise JobError(f"Cannot read Reel slide: {path}") from error
    return paths


def reel_video_path(job_file: str | Path, post_id: str) -> Path:
    return Path(job_file).parent / "assets" / post_id / "reel" / "reel.mp4"


def render_reel_video(
    job_file: str | Path,
    post_id: str,
    slide_seconds: float = 2.0,
    *,
    ffmpeg_binary: str = "ffmpeg",
    runner: Callable[..., Any] = subprocess.run,
    binary_lookup: Callable[[str], str | None] = shutil.which,
) -> Path:
    """Turn the six final slides into a silent H.264 Reel ready for catalog audio."""
    if slide_seconds < 0.5 or slide_seconds > 10:
        raise JobError("slide_seconds must be between 0.5 and 10")
    ffmpeg = binary_lookup(ffmpeg_binary)
    if ffmpeg is None:
        raise JobError("ffmpeg is required to render a Reel video")
    slides = reel_slide_paths(job_file, post_id)
    output = reel_video_path(job_file, post_id)
    if output.exists():
        raise JobError(f"Reel video already exists at {output}; use --resume-job to publish it")
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for slide in slides:
        command.extend(["-loop", "1", "-t", str(slide_seconds), "-i", str(slide)])
    filters = [f"[{index}:v]fps=30,format=yuv420p[v{index}]" for index in range(SLIDE_COUNT)]
    inputs = "".join(f"[v{index}]" for index in range(SLIDE_COUNT))
    filters.append(f"{inputs}concat=n={SLIDE_COUNT}:v=1:a=0[outv]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outv]",
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-level",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    try:
        result = runner(command, check=False, capture_output=True, text=True)
    except OSError as error:
        raise ReelRenderError(f"Could not run ffmpeg: {error}") from error
    if result.returncode != 0:
        output.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "unknown ffmpeg error").strip()
        raise ReelRenderError(f"Reel rendering failed: {detail}")
    if not output.is_file() or output.stat().st_size == 0:
        raise ReelRenderError("ffmpeg did not create a Reel video")
    return output
