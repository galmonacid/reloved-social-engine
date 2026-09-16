"""Operator CLI for the safe, local ReLoved weekly-content workflow."""

from __future__ import annotations

import argparse
import json
import os
import sys

from reloved_engine.assets import generate_post_images, overlay_post_images, write_visual_plan
from reloved_engine.jobs import JobError, create_weekly_job, job_ready, load_job, review_post
from reloved_engine.performance_tracker import HookPerformanceTracker, PostResult


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="ReLoved Social Engine local workflow")
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
    images = subcommands.add_parser("generate-images", help="Generate six source images for an approved post")
    images.add_argument("job_file")
    images.add_argument("post_id")
    images.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1"))
    overlay = subcommands.add_parser("overlay", help="Add local copy overlays to an approved post's images")
    overlay.add_argument("job_file")
    overlay.add_argument("post_id")
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
            print(f"Created 7-post draft job at {path}")
        elif args.command == "inspect":
            job = load_job(args.job_file)
            print(json.dumps({
                "job_id": job["job_id"], "date": job["date"], "ready": job_ready(job),
                "posts": [{"id": post["id"], "day": post["day"], "status": post["status"], "hook": post["hook"]}
                          for post in job["posts"]],
            }, indent=2))
        elif args.command == "review":
            post = review_post(args.job_file, args.post_id, f"{args.decision.upper()}D", args.note)
            print(f"{post['id']} is {post['status']}")
        elif args.command == "visual-plan":
            print(f"Wrote deterministic image prompts to {write_visual_plan(args.job_file, args.post_id)}")
        elif args.command == "generate-images":
            paths = generate_post_images(args.job_file, args.post_id, args.model)
            print(f"Generated {len(paths)} raw images in {paths[0].parent}")
        elif args.command == "overlay":
            paths = overlay_post_images(args.job_file, args.post_id)
            print(f"Rendered {len(paths)} final images in {paths[0].parent}")
        elif args.command == "metrics":
            tracker = HookPerformanceTracker(args.data_file)
            tracker.log(PostResult(args.post_id, args.pillar, args.hook_template_id, args.views,
                                   args.likes, args.comments, args.shares, args.saves))
            print(f"Recorded metrics for {args.post_id}")
        elif args.command == "report":
            print(json.dumps(HookPerformanceTracker(args.data_file).report(), indent=2))
    except (JobError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
