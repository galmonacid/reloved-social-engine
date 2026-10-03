"""Generate, host, and publish one ReLoved Instagram carousel."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from reloved_engine.assets import (
    export_instagram_images,
    generate_post_images,
    overlay_post_images,
    write_visual_plan,
)
from reloved_engine.firebase_hosting import FirebaseHostingError, deploy_instagram_assets
from reloved_engine.image_generator import DEFAULT_IMAGE_MODEL, DEFAULT_IMAGE_QUALITY
from reloved_engine.instagram import (
    DEFAULT_GRAPH_API_VERSION,
    InstagramPublisher,
    InstagramPublishError,
    final_slide_paths,
    publish_post,
)
from reloved_engine.jobs import JobError, create_daily_job, load_job, review_post

DEFAULT_NOTE = "Automatically approved by scripts/run_daily_carousel.py"


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Generate, host, and publish one daily carousel.")
    command.add_argument("--date", help="Job date in YYYY-MM-DD (defaults to today UTC)")
    command.add_argument("--resume-job", help="Resume an already rendered daily job")
    command.add_argument("--seed", type=int, help="Seed for reproducible post selection")
    command.add_argument("--jobs-dir", default="jobs", help="Job storage directory")
    command.add_argument("--force", action="store_true", help="Create a revision if the date exists")
    command.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL))
    command.add_argument(
        "--quality", default=os.environ.get("OPENAI_IMAGE_QUALITY", DEFAULT_IMAGE_QUALITY)
    )
    command.add_argument("--approval-note", default=DEFAULT_NOTE)
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
        help="Create, approve, and plan only; make no external calls",
    )
    return command


def run(args: argparse.Namespace) -> Path:
    resume = bool(args.resume_job)
    if resume:
        job_file = Path(args.resume_job)
        job = load_job(job_file)
        if len(job["posts"]) != 1 or job["posts"][0]["status"] != "APPROVED":
            raise JobError("A resumed daily job must contain one approved post")
        print(f"Resuming rendered job: {job_file}")
    else:
        job_file = create_daily_job(args.jobs_dir, args.date, args.seed, args.force)
        post_id = load_job(job_file)["posts"][0]["id"]
        review_post(job_file, post_id, "APPROVED", args.approval_note)
        plan_path = write_visual_plan(job_file, post_id)
        print(f"Created, approved, and planned: {post_id} ({plan_path})")

    if args.dry_run:
        print("Dry run complete: no images, Firebase deployment, or Instagram post was created.")
        return job_file

    _required_secret("OPENAI_API_KEY")
    instagram_user_id = _required_secret("INSTAGRAM_USER_ID")
    instagram_token = _required_secret("INSTAGRAM_ACCESS_TOKEN")
    _require_firebase(args)
    publisher = InstagramPublisher(instagram_user_id, instagram_token, args.instagram_api_version)
    account = publisher.account()
    print(f"Verified Instagram account: {account.get('username', account.get('id'))}")

    post_id = load_job(job_file)["posts"][0]["id"]
    if resume:
        final_slide_paths(job_file, post_id)
        print("Verified existing Instagram JPEGs; no images will be regenerated.")
    else:
        raw_paths = generate_post_images(job_file, post_id, args.model, args.quality)
        final_paths = overlay_post_images(job_file, post_id)
        instagram_paths = export_instagram_images(job_file, post_id)
        print(
            f"Rendered {len(raw_paths)} raw, {len(final_paths)} final PNGs, "
            f"and {len(instagram_paths)} Instagram JPEGs"
        )

    hosted = deploy_instagram_assets(
        job_file, [post_id], args.firebase_project, args.firebase_site
    )[post_id]
    receipt = publish_post(job_file, post_id, hosted, publisher)
    print(f"Published daily carousel: {receipt.get('permalink') or receipt['media_id']}")
    return job_file


def _required_secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise JobError(f"{name} is required unless --dry-run is used")
    return value


def _require_firebase(args: argparse.Namespace) -> None:
    if not args.firebase_project.strip():
        raise JobError("FIREBASE_PROJECT_ID or --firebase-project is required")
    if not args.firebase_site.strip():
        raise JobError("FIREBASE_HOSTING_SITE or --firebase-site is required")


def main(argv: list[str] | None = None) -> int:
    try:
        run(parser().parse_args(argv))
    except (FirebaseHostingError, InstagramPublishError, JobError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
