"""Durable, versioned weekly-job creation and review workflow."""

from __future__ import annotations

import json
import random
from datetime import date as calendar_date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from reloved_engine.content import build_draft, validate_draft
from reloved_engine.hook_templates import HOOK_TEMPLATES, Pillar, render_hook
from reloved_engine.object_library import OBJECT_LIBRARY
from reloved_engine.performance_tracker import HookPerformanceTracker
from reloved_engine.scheduler import weekly_plan


class JobError(ValueError):
    """Raised for unsafe job lifecycle operations."""


def create_weekly_job(
    jobs_dir: str | Path = "jobs", date: str | None = None, seed: int | None = None, force: bool = False
) -> Path:
    """Create a reproducible seven-post draft job, preserving existing jobs."""
    now = datetime.now(timezone.utc)
    plan_date = date or now.date().isoformat()
    _validate_date(plan_date)
    root = Path(jobs_dir) / plan_date
    original = root / "weekly_plan.json"
    if original.exists() and not force:
        raise JobError(f"Job already exists at {original}; use --force to create a revision")
    output = original if not original.exists() else root / f"weekly_plan-{now.strftime('%H%M%S%f')}-{uuid4().hex[:8]}.json"
    selected_seed = seed if seed is not None else random.SystemRandom().randrange(1, 2**63)
    job_id = f"weekly-{plan_date}-{uuid4().hex[:8]}"
    rng_state = random.getstate()
    random.seed(selected_seed)
    try:
        tracker = HookPerformanceTracker(Path(jobs_dir).parent / "data" / "hook_performance.json")
        combinations = [(name, context) for name, contexts in OBJECT_LIBRARY.items() for context in contexts]
        selected = random.sample(combinations, 7)
        posts = []
        for index, (pillar, (object_name, context)) in enumerate(zip(weekly_plan(7), selected), start=1):
            candidates = HOOK_TEMPLATES[pillar]
            template_id = tracker.choose([candidate.id for candidate in candidates])
            template = next(candidate for candidate in candidates if candidate.id == template_id)
            hook = render_hook(template)
            draft = build_draft(pillar, object_name, context, hook).as_dict()
            violations = validate_draft(draft, pillar, hook)
            if violations:
                raise JobError(f"Generated invalid draft: {'; '.join(violations)}")
            posts.append({
                "id": f"{job_id}-{index}", "day": index, "pillar": pillar, "object": object_name,
                "context": context, "hook_template_id": template.id, "hook": hook, "status": "PENDING_REVIEW",
                "review": None,
                "review_flags": (["Verify the factual claim and source before approval"]
                                 if template.id == "A1_ratio" else []),
                "draft": draft,
            })
    finally:
        random.setstate(rng_state)
    job = {"version": 1, "job_id": job_id, "created_at": now.isoformat(),
           "timezone": "Europe/London", "date": plan_date, "seed": selected_seed, "posts": posts}
    _atomic_json_write(output, job)
    return output


def load_job(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise JobError(f"Job file does not exist: {target}")
    try:
        job = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise JobError(f"Job file is invalid JSON: {target}") from error
    if not isinstance(job, dict) or job.get("version") != 1 or not isinstance(job.get("job_id"), str):
        raise JobError("Job has an invalid schema")
    if not isinstance(job.get("date"), str) or job.get("timezone") != "Europe/London":
        raise JobError("Job has an invalid date")
    _validate_date(job["date"])
    if not isinstance(job.get("seed"), int) or isinstance(job["seed"], bool):
        raise JobError("Job has an invalid seed")
    if not _is_aware_timestamp(job.get("created_at")):
        raise JobError("Job has an invalid creation timestamp")
    if not isinstance(job.get("posts"), list) or len(job["posts"]) != 7:
        raise JobError("Job must contain exactly seven posts")
    seen_ids = set()
    for expected_day, post in enumerate(job["posts"], start=1):
        if not isinstance(post, dict) or post.get("day") != expected_day:
            raise JobError("Job contains an invalid post record")
        post_id, status = post.get("id"), post.get("status")
        if not isinstance(post_id, str) or not post_id or post_id in seen_ids:
            raise JobError("Job contains duplicate or invalid post IDs")
        seen_ids.add(post_id)
        if status not in {"PENDING_REVIEW", "APPROVED", "REJECTED"}:
            raise JobError("Job contains an invalid post status")
        pillar, template_id = post.get("pillar"), post.get("hook_template_id")
        if not isinstance(pillar, str) or not isinstance(post.get("hook"), str):
            raise JobError("Job contains an invalid post record")
        if pillar not in HOOK_TEMPLATES:
            raise JobError("Job contains an invalid pillar")
        templates = {template.id for template in HOOK_TEMPLATES[cast(Pillar, pillar)]}
        if not isinstance(template_id, str) or template_id not in templates:
            raise JobError("Job contains an invalid hook template")
        if not isinstance(post.get("object"), str) or not isinstance(post.get("context"), str):
            raise JobError("Job contains an invalid post record")
        violations = validate_draft(post.get("draft", {}), post["pillar"], post["hook"])
        if violations:
            raise JobError(f"Job contains an invalid draft: {'; '.join(violations)}")
        creative = post["draft"]["creative"]
        if creative["object"] != post["object"] or creative["context"] != post["context"]:
            raise JobError("Job post and draft details do not match")
        review = post.get("review")
        if status == "PENDING_REVIEW" and review is not None:
            raise JobError("Pending post must not have a review")
        if status != "PENDING_REVIEW":
            if not isinstance(review, dict) or review.get("decision") != status:
                raise JobError("Reviewed post has an invalid review record")
            if not isinstance(review.get("note"), str) or not _is_aware_timestamp(review.get("reviewed_at")):
                raise JobError("Reviewed post has an invalid review record")
    return cast(dict[str, Any], job)


def review_post(path: str | Path, post_id: str, decision: str, note: str = "") -> dict[str, Any]:
    """Approve or reject one pending draft and record a timestamped review."""
    if decision not in {"APPROVED", "REJECTED"}:
        raise JobError("decision must be APPROVED or REJECTED")
    job = load_job(path)
    post = next((item for item in job["posts"] if item.get("id") == post_id), None)
    if post is None:
        raise JobError(f"Unknown post ID: {post_id}")
    if post["status"] != "PENDING_REVIEW":
        raise JobError(f"Post {post_id} is already {post['status']}")
    violations = validate_draft(post.get("draft", {}), post.get("pillar", ""), post.get("hook", ""))
    if violations:
        raise JobError(f"Cannot review invalid draft: {'; '.join(violations)}")
    post["status"] = decision
    post["review"] = {"decision": decision, "note": note, "reviewed_at": datetime.now(timezone.utc).isoformat()}
    _atomic_json_write(Path(path), job)
    return cast(dict[str, Any], post)


def job_ready(job: dict[str, Any]) -> bool:
    return all(post.get("status") == "APPROVED" for post in job["posts"])


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _validate_date(value: str) -> None:
    try:
        calendar_date.fromisoformat(value)
    except ValueError as error:
        raise JobError("date must use YYYY-MM-DD") from error


def _is_aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False
