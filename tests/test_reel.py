from types import SimpleNamespace

import pytest
from PIL import Image

from reloved_engine.jobs import JobError, create_daily_job, load_job, review_post
from reloved_engine.reel import render_reel_video


def prepared_daily_job(tmp_path):
    job_file = create_daily_job(tmp_path / "jobs", "2026-10-03", 42)
    post_id = load_job(job_file)["posts"][0]["id"]
    review_post(job_file, post_id, "APPROVED", "Ready")
    final = job_file.parent / "assets" / post_id / "final"
    final.mkdir(parents=True)
    for index in range(1, 7):
        Image.new("RGB", (1080, 1920), "white").save(final / f"slide-{index}.png")
    return job_file, post_id


def test_render_reel_uses_all_six_slides_and_instagram_video_settings(tmp_path):
    job_file, post_id = prepared_daily_job(tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        output = job_file.parent / "assets" / post_id / "reel" / "reel.mp4"
        output.write_bytes(b"video")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    output = render_reel_video(
        job_file,
        post_id,
        1.5,
        runner=runner,
        binary_lookup=lambda _: "/usr/local/bin/ffmpeg",
    )

    command = calls[0][0]
    assert output.read_bytes() == b"video"
    assert command.count("-i") == 6
    assert "concat=n=6:v=1:a=0" in command[command.index("-filter_complex") + 1]
    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"


def test_render_reel_requires_ffmpeg(tmp_path):
    job_file, post_id = prepared_daily_job(tmp_path)
    with pytest.raises(JobError, match="ffmpeg"):
        render_reel_video(job_file, post_id, binary_lookup=lambda _: None)
