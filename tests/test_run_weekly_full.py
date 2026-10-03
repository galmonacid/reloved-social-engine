import importlib.util
from pathlib import Path

from PIL import Image

from reloved_engine.jobs import load_job

SCRIPT = Path(__file__).parents[1] / "scripts" / "run_weekly_full.py"
SPEC = importlib.util.spec_from_file_location("run_weekly_full", SCRIPT)
assert SPEC and SPEC.loader
weekly = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(weekly)


def test_dry_run_creates_approves_and_plans_every_post(tmp_path):
    jobs_dir = tmp_path / "jobs"

    assert weekly.main([
        "--date", "2026-09-16", "--seed", "13", "--jobs-dir", str(jobs_dir), "--dry-run"
    ]) == 0

    job_file = jobs_dir / "2026-09-16" / "weekly_plan.json"
    job = load_job(job_file)
    assert all(post["status"] == "APPROVED" for post in job["posts"])
    assert all(post["review"]["note"] == weekly.DEFAULT_NOTE for post in job["posts"])
    assert all(
        (jobs_dir / "2026-09-16" / "assets" / post["id"] / "image_prompts.json").exists()
        for post in job["posts"]
    )


def test_full_run_requires_key_after_safe_local_steps(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    jobs_dir = tmp_path / "jobs"

    assert weekly.main(["--date", "2026-09-17", "--jobs-dir", str(jobs_dir)]) == 2

    job = load_job(jobs_dir / "2026-09-17" / "weekly_plan.json")
    assert all(post["status"] == "APPROVED" for post in job["posts"])


def test_full_run_generates_hosts_and_publishes_all_posts(tmp_path, monkeypatch):
    jobs_dir = tmp_path / "jobs"
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("INSTAGRAM_USER_ID", "ig-user")
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "ig-token")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "reloved-project")
    monkeypatch.setenv("FIREBASE_HOSTING_SITE", "reloved-social-media")

    class Publisher:
        def __init__(self, *args):
            self.instagram_user_id = "ig-user"

        def account(self):
            return {"id": "ig-user", "username": "reloved"}

    def generate(job_file, post_id, model, quality):
        raw = Path(job_file).parent / "assets" / post_id / "raw"
        raw.mkdir(parents=True)
        paths = []
        for index in range(1, 7):
            path = raw / f"slide-{index}.png"
            Image.new("RGB", (800, 800), "white").save(path)
            paths.append(path)
        return paths

    hosted = []

    def deploy(job_file, post_ids, project_id, site_id):
        hosted.extend(post_ids)
        return {
            post_id: [f"https://reloved-social-media.web.app/{post_id}/slide-{n}.jpg" for n in range(1, 7)]
            for post_id in post_ids
        }

    published = []

    def publish(job_file, post_id, urls, publisher):
        published.append((post_id, urls))
        return {"media_id": f"media-{post_id}", "permalink": f"https://instagram.test/{post_id}"}

    monkeypatch.setattr(weekly, "InstagramPublisher", Publisher)
    monkeypatch.setattr(weekly, "generate_post_images", generate)
    monkeypatch.setattr(weekly, "deploy_instagram_assets", deploy)
    monkeypatch.setattr(weekly, "publish_post", publish)

    assert weekly.main([
        "--date", "2026-10-02", "--seed", "13", "--jobs-dir", str(jobs_dir)
    ]) == 0

    assert len(hosted) == 7
    assert len(published) == 7
    assert all(len(urls) == 6 for _, urls in published)
    assert all(
        (jobs_dir / "2026-10-02" / "assets" / post_id / "instagram" / "slide-6.jpg").exists()
        for post_id in hosted
    )
