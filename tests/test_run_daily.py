import importlib.util
from pathlib import Path

import pytest
from PIL import Image

from reloved_engine.jobs import load_job


def load_script(name):
    script = Path(__file__).parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_daily_carousel_dry_run_creates_only_one_post(tmp_path):
    daily = load_script("run_daily_carousel")
    jobs = tmp_path / "jobs"

    assert daily.main(["--date", "2026-10-03", "--jobs-dir", str(jobs), "--dry-run"]) == 0
    job = load_job(jobs / "2026-10-03" / "daily_plan.json")
    assert len(job["posts"]) == 1
    assert job["posts"][0]["status"] == "APPROVED"
    assert job["posts"][0]["review"]["note"] == daily.DEFAULT_NOTE


def test_daily_reel_dry_run_creates_only_one_post(tmp_path):
    daily = load_script("run_daily_reel")
    jobs = tmp_path / "jobs"

    assert daily.main(["--date", "2026-10-04", "--jobs-dir", str(jobs), "--dry-run"]) == 0
    job = load_job(jobs / "2026-10-04" / "daily_plan.json")
    assert len(job["posts"]) == 1
    assert job["posts"][0]["status"] == "APPROVED"


def test_daily_reel_rejects_instagram_login_token(monkeypatch):
    daily = load_script("run_daily_reel")
    monkeypatch.setenv(
        "INSTAGRAM_FACEBOOK_PAGE_ACCESS_TOKEN", "IGQ-instagram-login-token"
    )

    with pytest.raises(daily.JobError, match="Instagram Login token"):
        daily._required_facebook_token("INSTAGRAM_FACEBOOK_PAGE_ACCESS_TOKEN", "Page")


def test_daily_carousel_full_run_publishes_one_post(tmp_path, monkeypatch):
    daily = load_script("run_daily_carousel")
    jobs = tmp_path / "jobs"
    for name, value in {
        "OPENAI_API_KEY": "openai-test",
        "INSTAGRAM_USER_ID": "ig-user",
        "INSTAGRAM_ACCESS_TOKEN": "ig-token",
        "FIREBASE_PROJECT_ID": "reloved-project",
        "FIREBASE_HOSTING_SITE": "reloved-social-media",
    }.items():
        monkeypatch.setenv(name, value)

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

    published = []
    monkeypatch.setattr(daily, "InstagramPublisher", Publisher)
    monkeypatch.setattr(daily, "generate_post_images", generate)
    monkeypatch.setattr(
        daily,
        "deploy_instagram_assets",
        lambda job, ids, project, site: {
            ids[0]: [f"https://example.test/slide-{index}.jpg" for index in range(1, 7)]
        },
    )
    monkeypatch.setattr(
        daily,
        "publish_post",
        lambda job, post_id, urls, publisher: published.append(post_id)
        or {"media_id": "media-1"},
    )

    assert daily.main(["--date", "2026-10-05", "--jobs-dir", str(jobs)]) == 0
    assert len(published) == 1


def test_daily_reel_full_run_renders_and_publishes_one_post(tmp_path, monkeypatch):
    daily = load_script("run_daily_reel")
    jobs = tmp_path / "jobs"
    for name, value in {
        "OPENAI_API_KEY": "openai-test",
        "INSTAGRAM_USER_ID": "ig-user",
        "INSTAGRAM_FACEBOOK_PAGE_ACCESS_TOKEN": "facebook-page-token",
        "INSTAGRAM_FACEBOOK_USER_ACCESS_TOKEN": "facebook-user-token",
        "FIREBASE_PROJECT_ID": "reloved-project",
        "FIREBASE_HOSTING_SITE": "reloved-social-media",
    }.items():
        monkeypatch.setenv(name, value)

    class Publisher:
        def __init__(self, *args, **kwargs):
            self.instagram_user_id = "ig-user"

        def account(self):
            return {"id": "ig-user", "username": "reloved"}

        def trending_audio(self, audio_type):
            return {"audio_id": "audio-1", "title": "Trending track"}

    def generate(job_file, post_id, model, quality):
        raw = Path(job_file).parent / "assets" / post_id / "raw"
        raw.mkdir(parents=True)
        paths = []
        for index in range(1, 7):
            path = raw / f"slide-{index}.png"
            Image.new("RGB", (800, 800), "white").save(path)
            paths.append(path)
        return paths

    def render(job_file, post_id, seconds):
        path = Path(job_file).parent / "assets" / post_id / "reel" / "reel.mp4"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"video")
        return path

    published = []
    monkeypatch.setattr(daily, "InstagramPublisher", Publisher)
    monkeypatch.setattr(daily, "generate_post_images", generate)
    monkeypatch.setattr(daily, "render_reel_video", render)
    monkeypatch.setattr(
        daily, "deploy_instagram_reel", lambda *args: "https://example.test/reel.mp4"
    )
    monkeypatch.setattr(
        daily,
        "publish_reel_post",
        lambda job, post_id, url, audio, publisher: published.append((post_id, audio))
        or {"media_id": "media-1"},
    )

    assert daily.main(["--date", "2026-10-06", "--jobs-dir", str(jobs)]) == 0
    assert len(published) == 1
    assert published[0][1]["audio_id"] == "audio-1"


@pytest.mark.parametrize("failure_stage", ["account", "audio"])
def test_reel_auth_failure_creates_no_job(tmp_path, monkeypatch, failure_stage):
    daily = load_script("run_daily_reel")
    for name in (
        "OPENAI_API_KEY", "INSTAGRAM_USER_ID", "INSTAGRAM_FACEBOOK_PAGE_ACCESS_TOKEN",
        "INSTAGRAM_FACEBOOK_USER_ACCESS_TOKEN", "FIREBASE_PROJECT_ID", "FIREBASE_HOSTING_SITE",
    ):
        monkeypatch.setenv(name, "test-value")

    class Publisher:
        def __init__(self, *args, **kwargs):
            pass

        def account(self):
            if failure_stage == "account":
                raise daily.InstagramPublishError("Page token expired")
            return {"id": "ig-user"}

        def trending_audio(self, audio_type):
            raise daily.InstagramPublishError("User token expired")

    monkeypatch.setattr(daily, "InstagramPublisher", Publisher)
    jobs = tmp_path / "jobs"
    assert daily.main(["--jobs-dir", str(jobs)]) == 2
    assert not jobs.exists()


def test_reel_check_auth_creates_no_job(tmp_path, monkeypatch):
    daily = load_script("run_daily_reel")
    monkeypatch.setattr(daily, "check_auth", lambda args: (object(), {"audio_id": "audio-1"}))
    jobs = tmp_path / "jobs"
    assert daily.main(["--jobs-dir", str(jobs), "--check-auth"]) == 0
    assert not jobs.exists()
