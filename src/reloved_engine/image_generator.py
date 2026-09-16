"""OpenAI image-generation adapter. It writes assets locally and never publishes them."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from pathlib import Path


class ImageGenerationError(RuntimeError):
    """Raised when the image provider cannot create a complete carousel."""


def generate_images(
    prompts: Sequence[str], output_dir: str | Path, api_key: str, model: str = "gpt-image-1"
) -> list[Path]:
    """Generate six portrait source images and return their local PNG paths.

    The caller must make the billable API call intentional; this function does
    not read environment variables or make publishing decisions.
    """
    if len(prompts) != 6:
        raise ValueError("exactly six image prompts are required")
    if not api_key.strip():
        raise ImageGenerationError("OPENAI_API_KEY is required to generate images")
    try:
        from openai import OpenAI
    except ImportError as error:  # pragma: no cover - dependency is declared in pyproject
        raise ImageGenerationError("Install the project dependencies before generating images") from error

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=api_key)
    paths: list[Path] = []
    for index, prompt in enumerate(prompts, start=1):
        try:
            response = client.images.generate(model=model, prompt=prompt, size="1024x1536", n=1)
            if not response.data:
                raise ImageGenerationError("The image API did not return an image")
            encoded = response.data[0].b64_json
            if not encoded:
                raise ImageGenerationError("The image API did not return image bytes")
            path = directory / f"slide-{index}.png"
            path.write_bytes(base64.b64decode(encoded))
            paths.append(path)
        except Exception as error:  # The provider exception type varies by SDK release.
            raise ImageGenerationError(f"Image generation failed for slide {index}: {error}") from error
    return paths
