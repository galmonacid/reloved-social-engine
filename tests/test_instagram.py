import json

import pytest
from PIL import Image

from reloved_engine.assets import export_instagram_images
from reloved_engine.instagram import (
    FACEBOOK_GRAPH_ROOT,
    InstagramPublisher,
    image_urls_from_base,
    publication_receipt_path,
    publish_post,
    validate_image_urls,
)
from reloved_engine.jobs import JobError, create_weekly_job, load_job, review_post


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.posts = []
        self.gets = []
        self.next_id = 1

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        object_id = f"id-{self.next_id}"
        self.next_id += 1
        return FakeResponse({"id": object_id})

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        fields = kwargs["params"]["fields"]
        if fields == "status_code,status":
            return FakeResponse({"status_code": "FINISHED"})
        return FakeResponse({"id": "id-8", "permalink": "https://www.instagram.com/p/example/"})


def prepared_post(tmp_path):
    job_file = create_weekly_job(tmp_path / "jobs", "2026-09-29", 42)
    post_id = load_job(job_file)["posts"][0]["id"]
    review_post(job_file, post_id, "APPROVED", "Ready for Instagram")
    raw_dir = job_file.parent / "assets" / post_id / "raw"
    raw_dir.mkdir(parents=True)
    for index in range(1, 7):
        Image.new("RGB", (1024, 1024), "white").save(raw_dir / f"slide-{index}.png")
    export_instagram_images(job_file, post_id)
    return job_file, post_id


def test_publishes_six_image_carousel_and_writes_receipt(tmp_path):
    job_file, post_id = prepared_post(tmp_path)
    session = FakeSession()
    publisher = InstagramPublisher(
        "ig-user-1", "secret-token", session=session, poll_interval=0, sleep=lambda _: None
    )
    urls = image_urls_from_base("https://cdn.example.com/post")

    receipt = publish_post(job_file, post_id, urls, publisher)

    assert receipt["media_id"] == "id-8"
    assert receipt["permalink"] == "https://www.instagram.com/p/example/"
    assert len(session.posts) == 8
    child_posts = session.posts[:6]
    assert all(call[1]["data"]["is_carousel_item"] == "true" for call in child_posts)
    carousel_data = session.posts[6][1]["data"]
    assert carousel_data["media_type"] == "CAROUSEL"
    assert carousel_data["children"] == "id-1,id-2,id-3,id-4,id-5,id-6"
    assert "#ReLoved" in carousel_data["caption"]
    saved = json.loads(publication_receipt_path(job_file, post_id).read_text())
    assert saved["media_id"] == "id-8"
    assert "secret-token" not in publication_receipt_path(job_file, post_id).read_text()


def test_refuses_accidental_republication(tmp_path):
    job_file, post_id = prepared_post(tmp_path)
    receipt = publication_receipt_path(job_file, post_id)
    receipt.write_text('{"media_id": "existing"}\n')
    publisher = InstagramPublisher("ig-user-1", "token", session=FakeSession())

    with pytest.raises(JobError, match="already recorded"):
        publish_post(
            job_file,
            post_id,
            image_urls_from_base("https://cdn.example.com/post"),
            publisher,
        )


def test_requires_exactly_six_public_https_urls():
    with pytest.raises(JobError, match="Exactly 6"):
        validate_image_urls(["https://cdn.example.com/one.png"])
    with pytest.raises(JobError, match="public HTTPS"):
        validate_image_urls([f"http://localhost/slide-{index}.png" for index in range(1, 7)])


def test_selects_trending_audio_and_publishes_reel_with_audio_configuration():
    class ReelSession:
        def __init__(self):
            self.posts = []
            self.gets = []

        def get(self, url, **kwargs):
            self.gets.append((url, kwargs))
            if url.endswith("/ig_audio"):
                return FakeResponse(
                    {
                        "audio": [
                            {
                                "audio_id": "audio-1",
                                "title": "Trending track",
                                "audio_type": "music",
                            }
                        ]
                    }
                )
            if kwargs["params"]["fields"] == "status_code,status":
                return FakeResponse({"status_code": "FINISHED"})
            return FakeResponse({"permalink": "https://www.instagram.com/reel/example/"})

        def post(self, url, **kwargs):
            self.posts.append((url, kwargs))
            return FakeResponse({"id": f"id-{len(self.posts)}"})

    session = ReelSession()
    publisher = InstagramPublisher(
        "ig-user-1",
        "secret-token",
        graph_root=FACEBOOK_GRAPH_ROOT,
        session=session,
        poll_interval=0,
        sleep=lambda _: None,
    )

    audio = publisher.trending_audio()
    result = publisher.publish_reel(
        "https://cdn.example.com/reel.mp4", "Caption", audio["audio_id"]
    )

    assert audio["title"] == "Trending track"
    assert session.gets[0][1]["params"]["audio_type"] == "music"
    assert session.gets[0][1]["params"]["user_id"] == "ig-user-1"
    configuration = json.loads(session.posts[0][1]["data"]["audio_configuration"])
    assert configuration == {"audio_id": "audio-1", "audio_volume": 100, "video_volume": 0}
    assert session.posts[0][1]["data"]["media_type"] == "REELS"
    assert result["media_id"] == "id-2"


def test_cli_dry_run_does_not_require_instagram_credentials(tmp_path, capsys):
    from reloved_engine.cli import main

    job_file, post_id = prepared_post(tmp_path)
    result = main([
        "publish-instagram",
        str(job_file),
        post_id,
        "--image-base-url",
        "https://cdn.example.com/post",
        "--dry-run",
    ])

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["will_publish"] is False
    assert len(output["image_urls"]) == 6
