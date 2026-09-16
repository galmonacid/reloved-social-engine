"""Deterministic, textless image prompts for the ReLoved carousel format."""

from __future__ import annotations

from collections.abc import Sequence

from reloved_engine.hook_templates import Pillar

Scene = str

STREET_LOCK = (
    "Casual iPhone photo in a typical UK residential neighbourhood, portrait 9:16. "
    "Natural overcast British daylight, realistic phone camera grain, eye-level framing, "
    "brick terraced houses, parked cars, wheelie bins, worn pavements and small front gardens. "
    "Authentic lived-in feel. Not staged. Not cinematic. No AI-art style. No exaggerated colours. "
    "No American elements. No readable text, logos, labels, signs, notes, receipts or prices; "
    "any incidental writing is blurred and unreadable. "
)
FLAT_LOCK = (
    "Casual iPhone photo inside a modest UK flat, portrait 9:16. Natural daylight through a white "
    "UPVC window, realistic phone camera grain, neutral walls and practical furniture, with subtle "
    "signs of life such as a mug, shoes by the door or a remote control. Authentic and lived-in. "
    "Not staged. Not cinematic. No AI-art style. No exaggerated colours. No American elements. "
    "No readable text, logos, labels, signs, notes, receipts or prices; any incidental writing is "
    "blurred and unreadable. "
)
SHOP_LOCK = (
    "Casual iPhone photo inside a small UK charity shop or modest shop aisle, portrait 9:16. "
    "Natural indoor lighting, realistic phone camera grain, everyday shelves and a slightly cluttered "
    "but authentic atmosphere. Not staged. Not cinematic. No AI-art style. No exaggerated colours. "
    "No American elements. No readable text, logos, labels, signs, notes, receipts or prices; "
    "any incidental writing is blurred and unreadable. "
)
LOCKS = {"STREET": STREET_LOCK, "FLAT": FLAT_LOCK, "SHOP": SHOP_LOCK}

DEFAULT_SCENES: dict[Pillar, list[Scene]] = {
    "A_MACRO": ["STREET", "STREET", "FLAT", "STREET", "STREET", "STREET"],
    "B_DONOR": ["FLAT", "FLAT", "FLAT", "FLAT", "STREET", "STREET"],
    "C_FINDER": ["FLAT", "SHOP", "STREET", "STREET", "FLAT", "FLAT"],
}

BEATS: dict[Pillar, list[str]] = {
    "A_MACRO": [
        "Several ordinary, still-usable household items near collection bins, including a usable {object_name}.",
        "A close casual view of a usable {object_name} that has been left behind.",
        "A used {object_name} at home, clearly functional and naturally placed.",
        "A {object_name} placed neatly by a front gate as if ready to pass on, with no note or sign.",
        "The {object_name} in another ordinary home setting, suggesting it has a next use.",
        "A {object_name} being used naturally in a modest home, with no posed people.",
    ],
    "B_DONOR": [
        "A used but functional {object_name} in a normal home setting.",
        "A closer view of the {object_name}, with normal wear but clearly not broken.",
        "The {object_name} sitting unused in the flat, casually framed.",
        "The {object_name} by a hallway or front door during an ordinary clear-out.",
        "The {object_name} placed neatly outside a UK home for someone to take, with no sign or note.",
        "The {object_name} in use in a different modest home, casual and unposed.",
    ],
    "C_FINDER": [
        "A used {object_name} at home, as if considering whether to replace it, no visible branding.",
        "A similar {object_name} on a small UK charity-shop shelf; stickers and labels are unreadable.",
        "A usable {object_name} placed neatly outside a UK home for someone to take, with no sign or note.",
        "A close casual view of the usable {object_name} outside on the pavement.",
        "The {object_name} now at home, looking like part of ordinary daily life.",
        "The {object_name} being used naturally at home, warm but realistic everyday light.",
    ],
}


def build_image_prompts(
    pillar: Pillar, object_name: str, scene_plan: Sequence[Scene] | None = None
) -> list[str]:
    """Build six locked image prompts without allowing the copy model to invent them."""
    scenes = list(scene_plan) if scene_plan is not None else DEFAULT_SCENES[pillar]
    if len(scenes) != 6 or any(scene not in LOCKS for scene in scenes):
        raise ValueError("scene_plan must contain six values from FLAT, STREET, SHOP")
    return [
        f"{LOCKS[scene]}Main focus: {beat.format(object_name=object_name)}"
        for scene, beat in zip(scenes, BEATS[pillar])
    ]
