"""Deterministic draft creation and validation for ReLoved carousel posts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from reloved_engine.hook_templates import Pillar

SCENES = ("FLAT", "STREET", "SHOP")
BANNED_TERMS = ("trash", "apartment", "thrift store", "dumpster", "yard sale", "$")


class ContentValidationError(ValueError):
    """Raised when a content package does not meet the v1.2 contract."""


@dataclass(frozen=True)
class DraftCreative:
    pillar: Pillar
    hook: str
    slides: list[str]
    object: str
    context: str
    cta: str
    caption: str
    hashtags: list[str]
    scene_plan: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": "v1.2",
            "market": "UK",
            "language": "en-GB",
            "platform": "tiktok",
            "format": "photo_slideshow_6",
            "pillar": self.pillar,
            "creative": {
                "hook": self.hook,
                "slides": self.slides,
                "object": self.object,
                "context": self.context,
                "cta": self.cta,
            },
            "caption": self.caption,
            "hashtags": self.hashtags,
            "assets": {"prompt_version": "visual_v1_textless_lock", "scene_plan": self.scene_plan},
        }


def build_draft(pillar: Pillar, object_name: str, context: str, hook: str) -> DraftCreative:
    """Create a concise, editable six-slide draft without an external model."""
    story = {
        "A_MACRO": [
            f"This {object_name} could still be useful.",
            "Not every unused thing is waste.",
            "Someone nearby may need it.",
            "Passing it on keeps it in use.",
        ],
        "B_DONOR": [
            f"This {object_name} still worked.",
            "I just did not need it anymore.",
            "Throwing it away did not feel right.",
            "Someone nearby could use it.",
        ],
        "C_FINDER": [
            f"A useful {object_name} was already nearby.",
            "I did not need to buy one new.",
            "Someone else was passing one on.",
            "That is better for my wallet too.",
        ],
    }[pillar]
    cta = "Find or pass on useful things with ReLoved."
    return DraftCreative(
        pillar=pillar,
        hook=hook,
        slides=[hook, *story, cta],
        object=object_name,
        context=context,
        cta=cta,
        caption=(
            f"A useful {object_name} can have a next home.\n"
            "Pass it on locally, free of charge.\n"
            "ReLoved makes room for what matters."
        ),
        hashtags=["#ReLoved", "#Reuse", "#GiveAway", "#Local"],
        scene_plan={
            "A_MACRO": ["STREET", "STREET", "FLAT", "STREET", "STREET", "STREET"],
            "B_DONOR": ["FLAT", "FLAT", "FLAT", "FLAT", "STREET", "STREET"],
            "C_FINDER": ["FLAT", "SHOP", "STREET", "STREET", "FLAT", "FLAT"],
        }[pillar],
    )


def validate_draft(draft: dict[str, Any], pillar: str, supplied_hook: str) -> list[str]:
    """Return every v1.2 contract violation; an empty list means valid."""
    if not isinstance(draft, dict):
        return ["draft must be an object"]
    errors: list[str] = []
    required_values = {
        "version": "v1.2", "market": "UK", "language": "en-GB", "platform": "tiktok",
        "format": "photo_slideshow_6", "pillar": pillar,
    }
    for key, expected in required_values.items():
        if draft.get(key) != expected:
            errors.append(f"{key} must equal {expected}")
    creative = draft.get("creative")
    if not isinstance(creative, dict):
        return ["creative must be an object"]
    slides = creative.get("slides")
    if not isinstance(slides, list) or len(slides) != 6 or not all(isinstance(x, str) for x in slides):
        errors.append("creative.slides must contain exactly six strings")
        slides = []
    if creative.get("hook") != supplied_hook:
        errors.append("creative.hook must equal the supplied hook")
    if slides and slides[0] != supplied_hook:
        errors.append("slide 1 must equal the supplied hook")
    if supplied_hook and len(supplied_hook.split()) >= 10:
        errors.append("slide 1 must contain fewer than ten words")
    if creative.get("cta") != (slides[5] if len(slides) == 6 else None):
        errors.append("creative.cta must equal slide 6")
    if len(slides) == 6 and "reloved" not in slides[5].lower():
        errors.append("slide 6 must mention ReLoved")
    if any(len(slide) >= 70 for slide in slides):
        errors.append("slides must be below 70 characters")
    if not isinstance(creative.get("object"), str) or not creative["object"].strip():
        errors.append("creative.object must be a non-empty string")
    if not isinstance(creative.get("context"), str) or not creative["context"].strip():
        errors.append("creative.context must be a non-empty string")
    if pillar not in {"A_MACRO", "B_DONOR", "C_FINDER"}:
        errors.append("pillar is not supported")
    for text in _strings(draft):
        lowered = text.lower()
        if "!" in text:
            errors.append("content must not use exclamation marks")
            break
        if any(term in lowered for term in BANNED_TERMS):
            errors.append("content uses a banned term")
            break
    hashtags = draft.get("hashtags")
    if not isinstance(hashtags, list) or len(hashtags) > 5 or not all(
        isinstance(tag, str) and tag.startswith("#") for tag in hashtags
    ):
        errors.append("hashtags must contain at most five hash-prefixed strings")
    caption = draft.get("caption")
    if not isinstance(caption, str) or len(caption.splitlines()) > 5:
        errors.append("caption must be a string containing at most five lines")
    assets = draft.get("assets", {})
    scenes = assets.get("scene_plan") if isinstance(assets, dict) else None
    if scenes is not None and (
        not isinstance(scenes, list) or len(scenes) != 6 or any(scene not in SCENES for scene in scenes)
    ):
        errors.append("scene_plan must contain six values from FLAT, STREET, SHOP")
    return errors


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)
