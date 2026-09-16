"""Consistent, local Pillow overlays for final TikTok carousel images."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS = (1080, 1920)
BOX = (90, 160, 990, 680)
FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def render_overlays(image_paths: Sequence[str | Path], slides: Sequence[str], output_dir: str | Path) -> list[Path]:
    """Crop six source images to 9:16 and add readable, consistent copy overlays."""
    if len(image_paths) != 6 or len(slides) != 6:
        raise ValueError("exactly six images and six slides are required")
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    results: list[Path] = []
    for index, (image_path, text) in enumerate(zip(image_paths, slides), start=1):
        canvas = _cover(Image.open(image_path).convert("RGB"), CANVAS).convert("RGBA")
        _draw_copy(canvas, text, is_hook=index == 1)
        target = directory / f"slide-{index}.png"
        canvas.convert("RGB").save(target, "PNG", optimize=True)
        results.append(target)
    return results


def _cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    scale = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def _draw_copy(canvas: Image.Image, text: str, is_hook: bool) -> None:
    draw = ImageDraw.Draw(canvas, "RGBA")
    max_size = 104 if is_hook else 76
    font, lines, line_height = _fit_text(draw, text, max_size)
    text_height = line_height * len(lines)
    box_height = max(120, text_height + 56)
    left, top, right, _ = BOX
    bottom = top + box_height
    draw.rounded_rectangle((left, top, right, bottom), radius=28, fill=(0, 0, 0, 115))
    y = top + 28
    for line in lines:
        draw.text((left + 34, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height


def _fit_text(draw: ImageDraw.ImageDraw, text: str, maximum: int) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    for size in range(maximum, 57, -2):
        font = _font(size)
        lines = _wrap(draw, text, font, 832)
        line_height = round(size * 1.12)
        if (
            len(lines) <= 3
            and all(draw.textlength(line, font=font) <= 832 for line in lines)
            and line_height * len(lines) + 56 <= 520
        ):
            return font, lines, line_height
    raise ValueError("slide text will not fit the overlay at the minimum font size")


def _font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.truetype("DejaVuSans-Bold.ttf", size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        proposed = f"{current} {word}".strip()
        if current and draw.textlength(proposed, font=font) > width:
            lines.append(current)
            current = word
        else:
            current = proposed
    if current:
        lines.append(current)
    return lines
