"""File-system orchestration for ReLoved visual assets."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

from reloved_engine.image_generator import (
    DEFAULT_IMAGE_MODEL,
    DEFAULT_IMAGE_QUALITY,
    SLIDE_SOURCE,
    SOURCE_SLIDES,
    generate_images,
)
from reloved_engine.image_prompt_builder import build_image_prompts
from reloved_engine.jobs import JobError, load_job
from reloved_engine.overlay import render_instagram_overlays, render_overlays


def write_visual_plan(job_file: str | Path, post_id: str) -> Path:
    """Write the deterministic prompts next to a job without changing the job record."""
    post = _post(job_file, post_id)
    destination = _asset_dir(job_file, post_id) / "image_prompts.json"
    prompts = build_image_prompts(post["pillar"], post["object"], post["draft"]["assets"].get("scene_plan"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "post_id": post_id,
                "prompts": prompts,
                "generation": {
                    "billable_images": len(SOURCE_SLIDES),
                    "generated_slides": list(SOURCE_SLIDES),
                    "slide_source": list(SLIDE_SOURCE),
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return destination


def generate_post_images(
    job_file: str | Path,
    post_id: str,
    model: str = DEFAULT_IMAGE_MODEL,
    quality: str = DEFAULT_IMAGE_QUALITY,
    force: bool = False,
) -> list[Path]:
    """Generate three billable images and materialise six source slide files."""
    post = _post(job_file, post_id)
    if post["status"] != "APPROVED":
        raise JobError("Only APPROVED posts can generate billable images")
    raw_dir = _asset_dir(job_file, post_id) / "raw"
    existing = [raw_dir / f"slide-{index}.png" for index in range(1, 7)]
    if not force and any(path.exists() for path in existing):
        raise JobError("Raw images already exist; use --force to make new billable image calls")
    plan = write_visual_plan(job_file, post_id)
    prompts = json.loads(plan.read_text(encoding="utf-8"))["prompts"]
    return generate_images(
        prompts,
        raw_dir,
        os.environ.get("OPENAI_API_KEY", ""),
        model,
        quality,
    )


def overlay_post_images(job_file: str | Path, post_id: str) -> list[Path]:
    """Render local text overlays from an approved post's existing raw images."""
    post = _post(job_file, post_id)
    if post["status"] != "APPROVED":
        raise JobError("Only APPROVED posts can be rendered")
    raw = _asset_dir(job_file, post_id) / "raw"
    image_paths = [raw / f"slide-{index}.png" for index in range(1, 7)]
    missing = [str(path) for path in image_paths if not path.exists()]
    if missing:
        raise JobError(f"Missing raw images: {', '.join(missing)}")
    return render_overlays(image_paths, post["draft"]["creative"]["slides"], _asset_dir(job_file, post_id) / "final")


def export_instagram_images(job_file: str | Path, post_id: str) -> list[Path]:
    """Render API-compatible 1080x1350 JPEGs from an approved post's raw images."""
    post = _post(job_file, post_id)
    if post["status"] != "APPROVED":
        raise JobError("Only APPROVED posts can be exported")
    raw = _asset_dir(job_file, post_id) / "raw"
    image_paths = [raw / f"slide-{index}.png" for index in range(1, 7)]
    missing = [str(path) for path in image_paths if not path.exists()]
    if missing:
        raise JobError(f"Missing raw images: {', '.join(missing)}")
    return render_instagram_overlays(
        image_paths,
        post["draft"]["creative"]["slides"],
        _asset_dir(job_file, post_id) / "instagram",
    )


def _post(job_file: str | Path, post_id: str) -> dict[str, Any]:
    job = load_job(job_file)
    post = next((item for item in job["posts"] if item["id"] == post_id), None)
    if post is None:
        raise JobError(f"Unknown post ID: {post_id}")
    return cast(dict[str, Any], post)


def _asset_dir(job_file: str | Path, post_id: str) -> Path:
    return Path(job_file).parent / "assets" / post_id
