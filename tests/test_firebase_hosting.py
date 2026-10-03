import json
from types import SimpleNamespace

import pytest
from PIL import Image

from reloved_engine.assets import export_instagram_images
from reloved_engine.firebase_hosting import deploy_instagram_assets
from reloved_engine.jobs import JobError, create_weekly_job, load_job, review_post


def prepared_post(tmp_path):
    job_file = create_weekly_job(tmp_path / "jobs", "2026-10-01", 42)
    post_id = load_job(job_file)["posts"][0]["id"]
    review_post(job_file, post_id, "APPROVED", "Ready")
    raw_dir = job_file.parent / "assets" / post_id / "raw"
    raw_dir.mkdir(parents=True)
    for index in range(1, 7):
        Image.new("RGB", (800, 800), "white").save(raw_dir / f"slide-{index}.png")
    export_instagram_images(job_file, post_id)
    return job_file, post_id


def test_deploys_to_dedicated_firebase_site_and_returns_urls(tmp_path):
    job_file, post_id = prepared_post(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="deployed", stderr="")

    urls = deploy_instagram_assets(
        job_file,
        [post_id],
        "reloved-project",
        "reloved-social-media",
        runner=runner,
        binary_lookup=lambda _: "/usr/local/bin/firebase",
    )

    assert urls[post_id][0].startswith("https://reloved-social-media.web.app/social-engine/")
    assert urls[post_id][-1].endswith("/slide-6.jpg")
    assert calls[0][0][:3] == ["/usr/local/bin/firebase", "deploy", "--only"]
    assert calls[0][0][calls[0][0].index("--config") + 1] == str(
        (job_file.parent / "firebase-hosting" / "firebase.json").resolve()
    )
    deployment = job_file.parent / "firebase-hosting"
    config = json.loads((deployment / "firebase.json").read_text())
    assert config["hosting"]["site"] == "reloved-social-media"
    assert (deployment / "public" / "social-engine" / load_job(job_file)["job_id"] / post_id / "slide-1.jpg").exists()
    manifest = json.loads((deployment / "deployment.json").read_text())
    assert manifest["firebase_project_id"] == "reloved-project"


def test_refuses_to_replace_the_default_app_hosting_site(tmp_path):
    job_file, post_id = prepared_post(tmp_path)

    with pytest.raises(JobError, match="dedicated secondary site"):
        deploy_instagram_assets(
            job_file,
            [post_id],
            "reloved-project",
            "reloved-project",
            binary_lookup=lambda _: "/usr/local/bin/firebase",
        )
