import pytest
from PIL import Image

from reloved_engine.image_prompt_builder import build_image_prompts
from reloved_engine.overlay import (
    BOX,
    CANVAS,
    INSTAGRAM_CANVAS,
    render_instagram_overlays,
    render_overlays,
)


def test_image_prompts_are_locked_textless_and_follow_scene_plan():
    prompts = build_image_prompts(
        "C_FINDER", "kettle", ["FLAT", "SHOP", "STREET", "STREET", "FLAT", "FLAT"]
    )

    assert len(prompts) == 6
    assert "British family terraced house" in prompts[0]
    assert "comfortably cluttered" in prompts[0]
    assert "without looking dirty or hoarded" in prompts[0]
    assert "UK charity shop" in prompts[1]
    assert all("No readable text" in prompt for prompt in prompts)
    assert "bright, warm and quietly optimistic" in prompts[-1]
    assert "Avoid cloudy skies" in prompts[-1]
    assert "overcast" not in prompts[-1]
    assert "Avoid cloudy skies" not in prompts[0]


def test_image_prompt_builder_rejects_invalid_scene_plan():
    with pytest.raises(ValueError, match="scene_plan"):
        build_image_prompts("B_DONOR", "kettle", ["FLAT"])


def test_donor_home_prompt_places_unused_item_among_family_belongings():
    prompt = build_image_prompts("B_DONOR", "kettle")[2]

    assert "unused among the belongings in the family home" in prompt
    assert "UK flat" not in prompt


def test_street_closing_prompt_replaces_overcast_light():
    prompt = build_image_prompts("A_MACRO", "chair")[-1]

    assert "Bright, clear late-afternoon British daylight" in prompt
    assert "overcast" not in prompt


def test_overlay_renders_six_9_by_16_pngs(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (600, 600), "steelblue").save(source)

    output = render_overlays([source] * 6, ["A short slide."] * 6, tmp_path / "final")

    assert len(output) == 6
    assert all(path.exists() and Image.open(path).size == CANVAS for path in output)
    # The black panel must be composited over, rather than replace, the source
    # pixels: source colour remains visible beneath the 45%-opaque panel.
    panel_pixel = Image.open(output[0]).getpixel((BOX[2] - 60, BOX[1] + 60))
    assert panel_pixel == (38, 71, 99)


def test_overlay_rejects_copy_that_cannot_fit(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (600, 600), "steelblue").save(source)

    with pytest.raises(ValueError, match="will not fit"):
        render_overlays([source] * 6, ["verylongword" * 100] * 6, tmp_path / "final")


def test_instagram_overlay_renders_six_4_by_5_jpegs(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (600, 600), "steelblue").save(source)

    output = render_instagram_overlays(
        [source] * 6, ["A short slide."] * 6, tmp_path / "instagram"
    )

    assert len(output) == 6
    assert all(path.suffix == ".jpg" for path in output)
    assert all(Image.open(path).size == INSTAGRAM_CANVAS for path in output)
    assert all(Image.open(path).format == "JPEG" for path in output)
