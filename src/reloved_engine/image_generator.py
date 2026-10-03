"""OpenAI image-generation adapter. It writes assets locally and never publishes them."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, cast

DEFAULT_IMAGE_MODEL = "gpt-image-1-mini"
DEFAULT_IMAGE_QUALITY = "medium"
# Generate one visual for each two-slide story beat, then reuse it locally.
# This keeps the six-slide carousel format while halving billable image calls.
SOURCE_SLIDES = (1, 3, 6)
SLIDE_SOURCE = (1, 1, 3, 3, 6, 6)
ImageQuality = Literal["standard", "hd", "low", "medium", "high", "auto"]
IMAGE_QUALITIES = {"standard", "hd", "low", "medium", "high", "auto"}


class ImageGenerationError(RuntimeError):
    """Raised when the image provider cannot create a complete carousel."""


def generate_images(
    prompts: Sequence[str],
    output_dir: str | Path,
    api_key: str,
    model: str = DEFAULT_IMAGE_MODEL,
    quality: str = DEFAULT_IMAGE_QUALITY,
) -> list[Path]:
    """Generate three portrait images and map them onto six local slide paths.

    The caller must make the billable API call intentional; this function does
    not read environment variables or make publishing decisions.
    """
    if len(prompts) != 6:
        raise ValueError("exactly six image prompts are required")
    if not api_key.strip():
        raise ImageGenerationError("OPENAI_API_KEY is required to generate images")
    if quality not in IMAGE_QUALITIES:
        raise ValueError(f"unsupported image quality: {quality}")
    selected_quality = cast(ImageQuality, quality)
    try:
        from openai import OpenAI
    except ImportError as error:  # pragma: no cover - dependency is declared in pyproject
        raise ImageGenerationError("Install the project dependencies before generating images") from error

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=api_key)
    generated: dict[int, bytes] = {}
    for slide_number in SOURCE_SLIDES:
        prompt = prompts[slide_number - 1]
        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                size="1024x1536",
                quality=selected_quality,
                n=1,
            )
            if not response.data:
                raise ImageGenerationError("The image API did not return an image")
            encoded = response.data[0].b64_json
            if not encoded:
                raise ImageGenerationError("The image API did not return image bytes")
            generated[slide_number] = base64.b64decode(encoded)
        except Exception as error:  # The provider exception type varies by SDK release.
            raise ImageGenerationError(
                f"Image generation failed for source slide {slide_number}: {error}"
            ) from error

    paths: list[Path] = []
    for slide_number, source_slide in enumerate(SLIDE_SOURCE, start=1):
        path = directory / f"slide-{slide_number}.png"
        path.write_bytes(generated[source_slide])
        paths.append(path)
    return paths
