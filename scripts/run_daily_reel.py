"""Generate six ReLoved slides, render a video, and publish a Reel with trending audio."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from reloved_engine.assets import generate_post_images, overlay_post_images, write_visual_plan
from reloved_engine.firebase_hosting import FirebaseHostingError, deploy_instagram_reel
from reloved_engine.image_generator import DEFAULT_IMAGE_MODEL, DEFAULT_IMAGE_QUALITY
from reloved_engine.instagram import (
    DEFAULT_GRAPH_API_VERSION,
    FACEBOOK_GRAPH_ROOT,
    InstagramPublisher,
    InstagramPublishError,
    publish_reel_post,
)
from reloved_engine.jobs import JobError, create_daily_job, load_job, review_post
from reloved_engine.market_config import TARGET_CITY
from reloved_engine.reel import ReelRenderError, reel_video_path, render_reel_video

DEFAULT_NOTE = f"Automatically approved for {TARGET_CITY} by scripts/run_daily_reel.py"


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description=(
            f"Generate, host, and publish one daily {TARGET_CITY} Reel with trending "
            "Instagram audio."
        )
    )
    command.add_argument("--date", help="Job date in YYYY-MM-DD (defaults to today UTC)")
    command.add_argument("--resume-job", help="Resume an approved daily Reel job")
    command.add_argument("--seed", type=int, help="Seed for reproducible post selection")
    command.add_argument("--jobs-dir", default="jobs", help="Job storage directory")
    command.add_argument("--force", action="store_true", help="Create a revision if the date exists")
    command.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL))
    command.add_argument(
        "--quality", default=os.environ.get("OPENAI_IMAGE_QUALITY", DEFAULT_IMAGE_QUALITY)
    )
    command.add_argument("--approval-note", default=DEFAULT_NOTE)
    command.add_argument("--slide-seconds", type=float, default=2.0)
    command.add_argument(
        "--audio-id",
        default="",
        help="Use a specific authorized audio ID instead of the first trending music result",
    )
    command.add_argument(
        "--firebase-project", default=os.environ.get("FIREBASE_PROJECT_ID", "")
    )
    command.add_argument("--firebase-site", default=os.environ.get("FIREBASE_HOSTING_SITE", ""))
    command.add_argument(
        "--instagram-api-version",
        default=os.environ.get("INSTAGRAM_GRAPH_API_VERSION", DEFAULT_GRAPH_API_VERSION),
    )
    command.add_argument(
        "--dry-run",
        action="store_true",
        help="Create, approve, and plan only; make no external calls or video",
    )
    command.add_argument(
        "--check-auth", action="store_true",
        help="Validate configuration and Meta access without creating or publishing a job",
    )
    return command


def run(args: argparse.Namespace) -> Path:
    publisher = None
    audio = {}
    if not args.dry_run or args.check_auth:
        publisher, audio = check_auth(args)
    if args.check_auth:
        print("Authentication checks passed; no content was created or published.")
        return Path(args.jobs_dir)
    resume = bool(args.resume_job)
    if resume:
        job_file = Path(args.resume_job)
        job = load_job(job_file)
        if len(job["posts"]) != 1 or job["posts"][0]["status"] != "APPROVED":
            raise JobError("A resumed daily job must contain one approved post")
        print(f"Resuming rendered Reel job: {job_file}")
    else:
        job_file = create_daily_job(args.jobs_dir, args.date, args.seed, args.force)
        post_id = load_job(job_file)["posts"][0]["id"]
        review_post(job_file, post_id, "APPROVED", args.approval_note)
        plan_path = write_visual_plan(job_file, post_id)
        print(f"Created, approved, and planned: {post_id} ({plan_path})")

    if args.dry_run:
        print("Dry run complete: no images, video, Firebase deployment, or Reel was created.")
        return job_file

    post_id = load_job(job_file)["posts"][0]["id"]
    video_path = reel_video_path(job_file, post_id)
    if resume and video_path.is_file():
        print("Verified existing Reel video; no images or video will be regenerated.")
    else:
        asset_root = job_file.parent / "assets" / post_id
        raw_paths = [asset_root / "raw" / f"slide-{index}.png" for index in range(1, 7)]
        final_paths = [asset_root / "final" / f"slide-{index}.png" for index in range(1, 7)]
        if resume and all(path.is_file() for path in final_paths):
            pass
        elif resume and all(path.is_file() for path in raw_paths):
            final_paths = overlay_post_images(job_file, post_id)
        else:
            raw_paths = generate_post_images(job_file, post_id, args.model, args.quality)
            final_paths = overlay_post_images(job_file, post_id)
        video_path = render_reel_video(job_file, post_id, args.slide_seconds)
        print(
            f"Rendered {len(raw_paths)} raw images, {len(final_paths)} final slides, "
            f"and Reel video {video_path}"
        )

    video_url = deploy_instagram_reel(
        job_file, post_id, args.firebase_project, args.firebase_site
    )
    assert publisher is not None
    receipt = publish_reel_post(job_file, post_id, video_url, audio, publisher)
    title = audio.get("title") or audio["audio_id"]
    print(
        f"Published daily {TARGET_CITY} Reel with audio {title}: "
        f"{receipt.get('permalink') or receipt['media_id']}"
    )
    return job_file


def check_auth(args: argparse.Namespace) -> tuple[InstagramPublisher, dict]:
    _required_secret("OPENAI_API_KEY")
    instagram_user_id = _required_secret("INSTAGRAM_USER_ID")
    instagram_token = _required_facebook_token(
        "INSTAGRAM_FACEBOOK_PAGE_ACCESS_TOKEN", "Page"
    )
    audio_token = _required_facebook_token(
        "INSTAGRAM_FACEBOOK_USER_ACCESS_TOKEN", "User"
    )
    _require_firebase(args)
    publisher = InstagramPublisher(
        instagram_user_id,
        instagram_token,
        args.instagram_api_version,
        graph_root=FACEBOOK_GRAPH_ROOT,
        audio_access_token=audio_token,
    )
    account = publisher.account()
    print(f"Verified Instagram account: {account.get('username', account.get('id'))}")

    audio = (
        {"audio_id": args.audio_id, "audio_type": "music"}
        if args.audio_id
        else publisher.trending_audio("music")
    )
    return publisher, audio


def _required_secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise JobError(f"{name} is required unless --dry-run is used")
    return value


def _required_facebook_token(name: str, token_kind: str) -> str:
    value = _required_secret(name)
    if value.startswith("IG"):
        raise JobError(
            f"{name} is an Instagram Login token, but trending Reel audio requires "
            f"a Facebook Login {token_kind} access token from graph.facebook.com"
        )
    return value


def _require_firebase(args: argparse.Namespace) -> None:
    if not args.firebase_project.strip():
        raise JobError("FIREBASE_PROJECT_ID or --firebase-project is required")
    if not args.firebase_site.strip():
        raise JobError("FIREBASE_HOSTING_SITE or --firebase-site is required")


def main(argv: list[str] | None = None) -> int:
    try:
        run(parser().parse_args(argv))
    except (
        FirebaseHostingError,
        InstagramPublishError,
        JobError,
        ReelRenderError,
        ValueError,
        RuntimeError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
