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
        HookTemplate("A1_ratio", "A_MACRO", "Could Milton Keynes reuse more?"),
        HookTemplate("A2_speed", "A_MACRO", "Milton Keynes bins things too quickly."),
        HookTemplate("A3_truth", "A_MACRO", "Milton Keynes, recycling isn't enough."),
        HookTemplate("A4_works", "A_MACRO", "Milton Keynes, this still works."),
        HookTemplate("A5_rubbish", "A_MACRO", "Milton Keynes, it wasn't rubbish."),
    ],
    "B_DONOR": [
        HookTemplate("B1_worked", "B_DONOR", "Milton Keynes, this still worked."),
        HookTemplate("B2_unused", "B_DONOR", "Milton Keynes, I no longer needed this."),
        HookTemplate("B3_space", "B_DONOR", "My Milton Keynes home was too full."),
        HookTemplate("B4_wrong", "B_DONOR", "Milton Keynes, binning it felt wrong."),
        HookTemplate("B5_pause", "B_DONOR", "Milton Keynes, pause before binning it."),
    ],
    "C_FINDER": [
        HookTemplate("C1_price", "C_FINDER", "Milton Keynes, why pay £{price}?"),
        HookTemplate("C2_almost", "C_FINDER", "Milton Keynes, I almost bought one."),
        HookTemplate("C3_spare", "C_FINDER", "Someone in Milton Keynes had one spare."),
        HookTemplate("C4_zero", "C_FINDER", "Milton Keynes, £0 felt better."),
        HookTemplate("C5_new", "C_FINDER", "Milton Keynes, why buy new?"),
    ],
}

PRICE_OPTIONS = (20, 30, 40, 50, 60, 80, 100)


def render_hook(hook: HookTemplate, price: int | None = None) -> str:
    if "{price}" not in hook.template:
        return hook.template
    return hook.template.format(price=price or choice(PRICE_OPTIONS))
