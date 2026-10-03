"""Safe Firebase Hosting deployment for generated Instagram assets."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import quote

from reloved_engine.instagram import final_slide_paths, image_urls_from_base
from reloved_engine.jobs import JobError, load_job
from reloved_engine.reel import reel_video_path

_FIREBASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{4,28}[a-z0-9]$")


class FirebaseHostingError(RuntimeError):
    """Raised when staging or deploying Firebase-hosted media fails."""


def deploy_instagram_assets(
    job_file: str | Path,
    post_ids: Sequence[str],
    project_id: str,
    site_id: str,
    *,
    firebase_binary: str = "firebase",
    runner: Callable[..., Any] = subprocess.run,
    binary_lookup: Callable[[str], str | None] = shutil.which,
) -> dict[str, list[str]]:
    """Stage a complete week, deploy it to a dedicated site, and return its URLs."""
    project = _validate_id("FIREBASE_PROJECT_ID", project_id)
    site = _validate_id("FIREBASE_HOSTING_SITE", site_id)
    if project == site:
        raise JobError(
            "FIREBASE_HOSTING_SITE must be a dedicated secondary site, not the project's "
            "default app site"
        )
    firebase = binary_lookup(firebase_binary)
    if firebase is None:
        raise JobError("Firebase CLI is required; install it before the full weekly run")

    job = load_job(job_file)
    known_post_ids = {post["id"] for post in job["posts"]}
    if not post_ids or any(post_id not in known_post_ids for post_id in post_ids):
        raise JobError("Firebase deployment contains an unknown or empty post list")

    deployment_root = Path(job_file).parent / "firebase-hosting"
    public_root = deployment_root / "public"
    hosted: dict[str, list[str]] = {}
    for post_id in post_ids:
        destination = public_root / "social-engine" / job["job_id"] / post_id
        destination.mkdir(parents=True, exist_ok=True)
        for source in final_slide_paths(job_file, post_id):
            shutil.copy2(source, destination / source.name)
        base_url = (
            f"https://{site}.web.app/social-engine/"
            f"{quote(job['job_id'], safe='')}/{quote(post_id, safe='')}"
        )
        hosted[post_id] = image_urls_from_base(base_url)

    config_path = deployment_root / "firebase.json"
    config_path.write_text(
        json.dumps(
            {
                "hosting": {
                    "site": site,
                    "public": "public",
                    "ignore": ["firebase.json", "**/.*"],
                    "headers": [
                        {
                            "source": "/social-engine/**",
                            "headers": [
                                {"key": "Cache-Control", "value": "public,max-age=604800,immutable"}
                            ],
                        }
                    ],
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    command = [
        firebase,
        "deploy",
        "--only",
        "hosting",
        "--project",
        project,
        "--config",
        str(config_path.resolve()),
        "--non-interactive",
    ]
    try:
        result = runner(
            command,
            cwd=deployment_root,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "FIREBASE_CLI_DISABLE_UPDATE_CHECK": "true"},
        )
    except OSError as error:
        raise FirebaseHostingError(f"Could not run Firebase CLI: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown Firebase CLI error").strip()
        raise FirebaseHostingError(f"Firebase Hosting deployment failed: {detail}")
    _write_manifest(deployment_root / "deployment.json", project, site, hosted)
    return hosted


def deploy_instagram_reel(
    job_file: str | Path,
    post_id: str,
    project_id: str,
    site_id: str,
    *,
    firebase_binary: str = "firebase",
    runner: Callable[..., Any] = subprocess.run,
    binary_lookup: Callable[[str], str | None] = shutil.which,
) -> str:
    """Deploy one rendered Reel to the dedicated site and return its public URL."""
    project = _validate_id("FIREBASE_PROJECT_ID", project_id)
    site = _validate_id("FIREBASE_HOSTING_SITE", site_id)
    if project == site:
        raise JobError(
            "FIREBASE_HOSTING_SITE must be a dedicated secondary site, not the project's "
            "default app site"
        )
    firebase = binary_lookup(firebase_binary)
    if firebase is None:
        raise JobError("Firebase CLI is required; install it before the full daily run")

    job = load_job(job_file)
    if post_id not in {post["id"] for post in job["posts"]}:
        raise JobError(f"Unknown post ID: {post_id}")
    source = reel_video_path(job_file, post_id)
    if not source.is_file() or source.stat().st_size == 0:
        raise JobError(f"Missing Reel video: {source}; render it first")

    deployment_root = Path(job_file).parent / "firebase-hosting"
    destination = deployment_root / "public" / "social-engine" / job["job_id"] / post_id
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination / "reel.mp4")
    video_url = (
        f"https://{site}.web.app/social-engine/"
        f"{quote(job['job_id'], safe='')}/{quote(post_id, safe='')}/reel.mp4"
    )
    config_path = deployment_root / "firebase.json"
    _write_firebase_config(config_path, site)
    _run_firebase_deploy(firebase, project, config_path, deployment_root, runner)
    _write_reel_manifest(deployment_root / "deployment.json", project, site, post_id, video_url)
    return video_url


def _validate_id(name: str, value: str) -> str:
    identifier = value.strip()
    if not _FIREBASE_ID.fullmatch(identifier):
        raise JobError(f"{name} must be a valid lowercase Firebase identifier")
    return identifier


def _write_firebase_config(path: Path, site_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "hosting": {
                    "site": site_id,
                    "public": "public",
                    "ignore": ["firebase.json", "**/.*"],
                    "headers": [
                        {
                            "source": "/social-engine/**",
                            "headers": [
                                {"key": "Cache-Control", "value": "public,max-age=604800,immutable"}
                            ],
                        }
                    ],
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _run_firebase_deploy(
    firebase: str,
    project_id: str,
    config_path: Path,
    deployment_root: Path,
    runner: Callable[..., Any],
) -> None:
    command = [
        firebase,
        "deploy",
        "--only",
        "hosting",
        "--project",
        project_id,
        "--config",
        str(config_path.resolve()),
        "--non-interactive",
    ]
    try:
        result = runner(
            command,
            cwd=deployment_root,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "FIREBASE_CLI_DISABLE_UPDATE_CHECK": "true"},
        )
    except OSError as error:
        raise FirebaseHostingError(f"Could not run Firebase CLI: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown Firebase CLI error").strip()
        raise FirebaseHostingError(f"Firebase Hosting deployment failed: {detail}")


def _write_manifest(
    path: Path, project_id: str, site_id: str, hosted: dict[str, list[str]]
) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "firebase_project_id": project_id,
                "firebase_hosting_site": site_id,
                "posts": hosted,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_reel_manifest(
    path: Path, project_id: str, site_id: str, post_id: str, video_url: str
) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "firebase_project_id": project_id,
                "firebase_hosting_site": site_id,
                "reel": {"post_id": post_id, "video_url": video_url},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
