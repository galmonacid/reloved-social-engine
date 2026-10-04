"""Run weekly production through Firebase Hosting and Instagram publication.

This is the one-command end-to-end operator path. It creates a seven-post job,
records an automatic approval for every generated draft, creates and renders
all media, deploys the Instagram JPEGs to a dedicated Firebase Hosting site,
and publishes all seven carousels.

Automatic approval deliberately bypasses the normal human-review checkpoint.
Only use it when the generated copy and claims are already acceptable under
your operating policy. Image generation and Instagram publication are
external, billable actions.
"""

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
from reloved_engine.jobs import JobError, create_weekly_job, load_job, review_post
from reloved_engine.market_config import TARGET_CITY

DEFAULT_NOTE = f"Automatically approved for {TARGET_CITY} by scripts/run_weekly_full.py"


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description=f"Generate and publish one complete {TARGET_CITY} ReLoved Instagram week."
    )
    command.add_argument("--date", help="Job date in YYYY-MM-DD (defaults to today UTC)")
    command.add_argument(
        "--resume-job",
        help="Resume Firebase deployment and publication for an already rendered weekly job",
    )
    command.add_argument("--seed", type=int, help="Seed for reproducible post selection")
    command.add_argument("--jobs-dir", default="jobs", help="Job storage directory (default: jobs)")
    command.add_argument(
        "--force", action="store_true", help="Create a timestamped revision when this date already exists"
    )
    command.add_argument(
        "--model",
        default=os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        help="OpenAI image model",
    )
    command.add_argument(
        "--quality",
        default=os.environ.get("OPENAI_IMAGE_QUALITY", DEFAULT_IMAGE_QUALITY),
        help="OpenAI image quality",
    )
    command.add_argument("--approval-note", default=DEFAULT_NOTE, help="Approval note recorded on every post")
    command.add_argument(
        "--firebase-project",
        default=os.environ.get("FIREBASE_PROJECT_ID", ""),
        help="Firebase project ID (or FIREBASE_PROJECT_ID)",
    )
    command.add_argument(
        "--firebase-site",
        default=os.environ.get("FIREBASE_HOSTING_SITE", ""),
        help="Dedicated secondary Hosting site ID (or FIREBASE_HOSTING_SITE)",
    )
    command.add_argument(
        "--instagram-api-version",
        default=os.environ.get("INSTAGRAM_GRAPH_API_VERSION", DEFAULT_GRAPH_API_VERSION),
    )
    command.add_argument(
        "--dry-run",
        action="store_true",
        help="Create, approve, and plan only; make no image, Firebase, or Instagram calls",
    )
    return command


def run(args: argparse.Namespace) -> Path:
    """Execute the runbook workflow and return the created job file."""
    resume = bool(args.resume_job)
    if resume:
        job_file = Path(args.resume_job)
        job = load_job(job_file)
        if not all(post["status"] == "APPROVED" for post in job["posts"]):
            raise JobError("A resumed job must have every post approved")
        print(f"Resuming rendered job: {job_file}")
    else:
        job_file = create_weekly_job(args.jobs_dir, args.date, args.seed, args.force)
        job = load_job(job_file)
        print(f"Created {TARGET_CITY} campaign job: {job_file}")

        for post in job["posts"]:
            post_id = post["id"]
            review_post(job_file, post_id, "APPROVED", args.approval_note)
            plan_path = write_visual_plan(job_file, post_id)
            print(f"Approved and planned: {post_id} ({plan_path})")

    if args.dry_run:
        print("Dry run complete: no images, Firebase deployment, or Instagram posts were created.")
        return job_file

    _required_secret("OPENAI_API_KEY")
    instagram_user_id = _required_secret("INSTAGRAM_USER_ID")
    instagram_token = _required_secret("INSTAGRAM_ACCESS_TOKEN")
    if not args.firebase_project.strip():
        raise JobError("FIREBASE_PROJECT_ID or --firebase-project is required")
    if not args.firebase_site.strip():
        raise JobError("FIREBASE_HOSTING_SITE or --firebase-site is required")

    publisher = InstagramPublisher(
        instagram_user_id,
        instagram_token,
        args.instagram_api_version,
    )
    account = publisher.account()
    print(f"Verified Instagram account: {account.get('username', account.get('id', instagram_user_id))}")

    if resume:
        for post in load_job(job_file)["posts"]:
            final_slide_paths(job_file, post["id"])
        print("Verified existing Instagram JPEGs; no images will be regenerated.")
    else:
        for post in load_job(job_file)["posts"]:
            post_id = post["id"]
            raw_paths = generate_post_images(job_file, post_id, args.model, args.quality)
            final_paths = overlay_post_images(job_file, post_id)
            instagram_paths = export_instagram_images(job_file, post_id)
            print(
                f"Rendered {post_id}: {len(raw_paths)} raw, {len(final_paths)} final PNGs, "
                f"and {len(instagram_paths)} Instagram JPEGs"
            )

    posts = load_job(job_file)["posts"]
    post_ids = [post["id"] for post in posts]
    hosted_urls = deploy_instagram_assets(
        job_file,
        post_ids,
        args.firebase_project,
        args.firebase_site,
    )
    print(f"Deployed {len(post_ids) * 6} images to https://{args.firebase_site}.web.app")

    for post_id in post_ids:
        receipt = publish_post(job_file, post_id, hosted_urls[post_id], publisher)
        print(f"Published {post_id}: {receipt.get('permalink') or receipt['media_id']}")

    print(f"{TARGET_CITY} weekly production and publication complete: {job_file}")
    return job_file


def _required_secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise JobError(f"{name} is required unless --dry-run is used")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        run(args)
    except (
        FirebaseHostingError,
        InstagramPublishError,
        JobError,
        ValueError,
        RuntimeError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
