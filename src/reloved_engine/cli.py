"""Operator CLI for the safe, local ReLoved weekly-content workflow."""

from __future__ import annotations

import argparse
import json
import os
import sys

from reloved_engine.assets import (
    export_instagram_images,
    generate_post_images,
    overlay_post_images,
    write_visual_plan,
)
from reloved_engine.image_generator import DEFAULT_IMAGE_MODEL, DEFAULT_IMAGE_QUALITY
from reloved_engine.instagram import (
    DEFAULT_GRAPH_API_VERSION,
    InstagramPublisher,
    InstagramPublishError,
    build_caption,
    final_slide_paths,
    image_urls_from_base,
    publish_post,
    validate_image_urls,
)
from reloved_engine.jobs import JobError, create_weekly_job, job_ready, load_job, review_post
from reloved_engine.market_config import TARGET_CITY
from reloved_engine.performance_tracker import HookPerformanceTracker, PostResult


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description=f"ReLoved Social Engine {TARGET_CITY} launch workflow"
    )
    subcommands = command.add_subparsers(dest="command", required=True)
    create = subcommands.add_parser("create", help="Create a seven-post weekly draft job")
    create.add_argument("--date", help="Job date in YYYY-MM-DD (defaults to today UTC)")
    create.add_argument("--seed", type=int, help="Seed for reproducible selection")
    create.add_argument("--force", action="store_true", help="Create a timestamped revision if the job exists")
    create.add_argument("--jobs-dir", default="jobs", help="Job storage directory")
    inspect = subcommands.add_parser("inspect", help="Show job review status")
    inspect.add_argument("job_file")
    review = subcommands.add_parser("review", help="Approve or reject a pending post")
    review.add_argument("job_file")
    review.add_argument("post_id")
    review.add_argument("decision", choices=("approve", "reject"))
    review.add_argument("--note", default="")
    visual_plan = subcommands.add_parser("visual-plan", help="Write deterministic textless image prompts")
    visual_plan.add_argument("job_file")
    visual_plan.add_argument("post_id")
    images = subcommands.add_parser(
        "generate-images", help="Generate three images and reuse them across six slides"
    )
    images.add_argument("job_file")
    images.add_argument("post_id")
    images.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL))
    images.add_argument(
        "--quality", default=os.environ.get("OPENAI_IMAGE_QUALITY", DEFAULT_IMAGE_QUALITY)
    )
    images.add_argument(
        "--force", action="store_true", help="Replace existing images with new billable calls"
    )
    overlay = subcommands.add_parser("overlay", help="Add local copy overlays to an approved post's images")
    overlay.add_argument("job_file")
    overlay.add_argument("post_id")
    instagram_assets = subcommands.add_parser(
        "instagram-assets", help="Render six API-compatible 4:5 JPEG slides"
    )
    instagram_assets.add_argument("job_file")
    instagram_assets.add_argument("post_id")
    account = subcommands.add_parser(
        "instagram-check", help="Verify the configured Instagram professional account"
    )
    account.add_argument(
        "--api-version",
        default=os.environ.get("INSTAGRAM_GRAPH_API_VERSION", DEFAULT_GRAPH_API_VERSION),
    )
    publish = subcommands.add_parser(
        "publish-instagram", help="Publish an approved six-image carousel through Instagram"
    )
    publish.add_argument("job_file")
    publish.add_argument("post_id")
    publish.add_argument(
        "--image-url",
        action="append",
        default=[],
        help="Public HTTPS slide URL in order; repeat exactly six times",
    )
    publish.add_argument(
        "--image-base-url",
        default=os.environ.get("INSTAGRAM_IMAGE_BASE_URL", ""),
        help="Public HTTPS directory containing slide-1.jpg through slide-6.jpg",
    )
    publish.add_argument(
        "--api-version",
        default=os.environ.get("INSTAGRAM_GRAPH_API_VERSION", DEFAULT_GRAPH_API_VERSION),
    )
    publish.add_argument(
        "--dry-run", action="store_true", help="Validate and print the publication plan only"
    )
    publish.add_argument(
        "--allow-republish",
        action="store_true",
        help="Allow a second Instagram post even when a receipt already exists",
    )
    metrics = subcommands.add_parser("metrics", help="Record observed post metrics")
    metrics.add_argument("post_id")
    metrics.add_argument("pillar", choices=("A_MACRO", "B_DONOR", "C_FINDER"))
    metrics.add_argument("hook_template_id")
    for metric in ("views", "likes", "comments", "shares", "saves"):
        metrics.add_argument(f"--{metric}", type=int, default=0)
    metrics.add_argument("--data-file", default="data/hook_performance.json")
    report = subcommands.add_parser("report", help="Show hook performance ranking")
    report.add_argument("--data-file", default="data/hook_performance.json")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "create":
            path = create_weekly_job(args.jobs_dir, args.date, args.seed, args.force)
            print(f"Created 7-post {TARGET_CITY} draft job at {path}")
        elif args.command == "inspect":
            job = load_job(args.job_file)
            print(json.dumps({
                "job_id": job["job_id"], "date": job["date"],
                "campaign": job["campaign"], "ready": job_ready(job),
                "posts": [{"id": post["id"], "day": post["day"], "status": post["status"], "hook": post["hook"]}
                          for post in job["posts"]],
            }, indent=2))
        elif args.command == "review":
            post = review_post(args.job_file, args.post_id, f"{args.decision.upper()}D", args.note)
            print(f"{post['id']} is {post['status']}")
        elif args.command == "visual-plan":
            print(f"Wrote deterministic image prompts to {write_visual_plan(args.job_file, args.post_id)}")
        elif args.command == "generate-images":
            paths = generate_post_images(
                args.job_file, args.post_id, args.model, args.quality, args.force
            )
            print(f"Generated 3 billable images and {len(paths)} raw slide files in {paths[0].parent}")
        elif args.command == "overlay":
            paths = overlay_post_images(args.job_file, args.post_id)
            print(f"Rendered {len(paths)} final images in {paths[0].parent}")
        elif args.command == "instagram-assets":
            paths = export_instagram_images(args.job_file, args.post_id)
            print(f"Rendered {len(paths)} Instagram JPEGs in {paths[0].parent}")
        elif args.command == "instagram-check":
            publisher = _instagram_publisher(args.api_version)
            print(json.dumps(publisher.account(), indent=2))
        elif args.command == "publish-instagram":
            urls = _instagram_urls(args.image_url, args.image_base_url)
            paths = final_slide_paths(args.job_file, args.post_id)
            caption = build_caption(args.job_file, args.post_id)
            if args.dry_run:
                print(json.dumps({
                    "post_id": args.post_id,
                    "local_images": [str(path) for path in paths],
                    "image_urls": urls,
                    "caption": caption,
                    "will_publish": False,
                }, indent=2))
            else:
                receipt = publish_post(
                    args.job_file,
                    args.post_id,
                    urls,
                    _instagram_publisher(args.api_version),
                    args.allow_republish,
                )
                print(json.dumps(receipt, indent=2))
        elif args.command == "metrics":
            tracker = HookPerformanceTracker(args.data_file)
            tracker.log(PostResult(args.post_id, args.pillar, args.hook_template_id, args.views,
                                   args.likes, args.comments, args.shares, args.saves))
            print(f"Recorded metrics for {args.post_id}")
        elif args.command == "report":
            print(json.dumps(HookPerformanceTracker(args.data_file).report(), indent=2))
    except (InstagramPublishError, JobError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


def _instagram_publisher(api_version: str) -> InstagramPublisher:
    return InstagramPublisher(
        os.environ.get("INSTAGRAM_USER_ID", ""),
        os.environ.get("INSTAGRAM_ACCESS_TOKEN", ""),
        api_version,
    )


def _instagram_urls(explicit_urls: list[str], base_url: str) -> list[str]:
    if explicit_urls and base_url:
        raise JobError("Use either --image-url or --image-base-url, not both")
    if explicit_urls:
        return validate_image_urls(explicit_urls)
    if base_url:
        return validate_image_urls(image_urls_from_base(base_url))
    raise JobError("Provide six --image-url values or --image-base-url")


if __name__ == "__main__":
    raise SystemExit(main())
