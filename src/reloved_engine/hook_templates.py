from __future__ import annotations

from dataclasses import dataclass
from random import choice
from typing import Literal

Pillar = Literal["A_MACRO", "B_DONOR", "C_FINDER"]


@dataclass(frozen=True)
class HookTemplate:
    id: str
    pillar: Pillar
    template: str


HOOK_TEMPLATES: dict[Pillar, list[HookTemplate]] = {
    "A_MACRO": [
        HookTemplate("A1_ratio", "A_MACRO", "Only 1 in 5 gets recycled."),
        HookTemplate("A2_speed", "A_MACRO", "We bin things too quickly."),
        HookTemplate("A3_truth", "A_MACRO", "Recycling isn't enough."),
        HookTemplate("A4_works", "A_MACRO", "Most of it still works."),
        HookTemplate("A5_rubbish", "A_MACRO", "It wasn't rubbish."),
    ],
    "B_DONOR": [
        HookTemplate("B1_worked", "B_DONOR", "It still worked."),
        HookTemplate("B2_unused", "B_DONOR", "I didn't need it anymore."),
        HookTemplate("B3_space", "B_DONOR", "My flat was too full."),
        HookTemplate("B4_wrong", "B_DONOR", "Binning it felt wrong."),
        HookTemplate("B5_pause", "B_DONOR", "I paused before binning it."),
    ],
    "C_FINDER": [
        HookTemplate("C1_price", "C_FINDER", "Why pay £{price}?"),
        HookTemplate("C2_almost", "C_FINDER", "I almost bought one."),
        HookTemplate("C3_spare", "C_FINDER", "Someone else didn't need it."),
        HookTemplate("C4_zero", "C_FINDER", "£0 felt better."),
        HookTemplate("C5_new", "C_FINDER", "Why buy new?"),
    ],
}

PRICE_OPTIONS = (20, 30, 40, 50, 60, 80, 100)


def render_hook(hook: HookTemplate, price: int | None = None) -> str:
    if "{price}" not in hook.template:
        return hook.template
    return hook.template.format(price=price or choice(PRICE_OPTIONS))
