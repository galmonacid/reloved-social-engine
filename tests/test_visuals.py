import pytest
from PIL import Image

from reloved_engine.image_prompt_builder import build_image_prompts
from reloved_engine.overlay import CANVAS, render_overlays


def test_image_prompts_are_locked_textless_and_follow_scene_plan():
    prompts = build_image_prompts(
        "C_FINDER", "kettle", ["FLAT", "SHOP", "STREET", "STREET", "FLAT", "FLAT"]
    )

    assert len(prompts) == 6
    assert "UK charity shop" in prompts[1]
    assert all("No readable text" in prompt for prompt in prompts)


def test_image_prompt_builder_rejects_invalid_scene_plan():
    with pytest.raises(ValueError, match="scene_plan"):
        build_image_prompts("B_DONOR", "kettle", ["FLAT"])


def test_overlay_renders_six_9_by_16_pngs(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (600, 600), "steelblue").save(source)

    output = render_overlays([source] * 6, ["A short slide."] * 6, tmp_path / "final")

    assert len(output) == 6
    assert all(path.exists() and Image.open(path).size == CANVAS for path in output)


def test_overlay_rejects_copy_that_cannot_fit(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (600, 600), "steelblue").save(source)

    with pytest.raises(ValueError, match="will not fit"):
        render_overlays([source] * 6, ["verylongword" * 100] * 6, tmp_path / "final")
