import json

import pytest

from reloved_engine.jobs import JobError, create_weekly_job, job_ready, load_job, review_post


def test_create_job_is_valid_reproducible_and_immutable(tmp_path):
    first = create_weekly_job(tmp_path / "jobs", "2026-09-08", seed=27)
    job = load_job(first)

    assert len(job["posts"]) == 7
    assert len({(post["object"], post["context"]) for post in job["posts"]}) == 7
    assert all(post["status"] == "PENDING_REVIEW" for post in job["posts"])
    assert not job_ready(job)
    with pytest.raises(JobError, match="already exists"):
        create_weekly_job(tmp_path / "jobs", "2026-09-08", seed=27)

    revision = create_weekly_job(tmp_path / "jobs", "2026-09-08", seed=27, force=True)
    second_revision = create_weekly_job(tmp_path / "jobs", "2026-09-08", seed=27, force=True)
    revised = load_job(revision)
    assert revision != first
    assert second_revision not in {first, revision}
    assert [{key: post[key] for key in ("pillar", "object", "context", "hook")} for post in job["posts"]] == [
        {key: post[key] for key in ("pillar", "object", "context", "hook")} for post in revised["posts"]
    ]


def test_review_lifecycle_and_invalid_job(tmp_path):
    path = create_weekly_job(tmp_path / "jobs", "2026-09-09", seed=3)
    job = load_job(path)
    first_id = job["posts"][0]["id"]

    reviewed = review_post(path, first_id, "APPROVED", "Looks accurate")
    assert reviewed["status"] == "APPROVED"
    with pytest.raises(JobError, match="already APPROVED"):
        review_post(path, first_id, "REJECTED")
    with pytest.raises(JobError, match="Unknown post ID"):
        review_post(path, "not-here", "APPROVED")

    for post in load_job(path)["posts"][1:]:
        review_post(path, post["id"], "APPROVED")
    assert job_ready(load_job(path))

    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"posts": []}), encoding="utf-8")
    with pytest.raises(JobError, match="invalid schema"):
        load_job(invalid)


def test_malformed_post_is_a_safe_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({
        "version": 1, "job_id": "x", "date": "2026-09-09", "timezone": "Europe/London",
        "seed": 1, "created_at": "2026-09-09T00:00:00+00:00", "posts": [{}] * 7,
    }), encoding="utf-8")
    with pytest.raises(JobError, match="invalid post"):
        load_job(path)


def test_forged_approval_record_is_rejected(tmp_path):
    path = create_weekly_job(tmp_path / "jobs", "2026-09-10", seed=4)
    job = load_job(path)
    job["posts"][0]["status"] = "APPROVED"
    path.write_text(json.dumps(job), encoding="utf-8")

    with pytest.raises(JobError, match="invalid review record"):
        load_job(path)
