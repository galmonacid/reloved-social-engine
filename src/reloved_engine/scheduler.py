from __future__ import annotations

import random
from collections import Counter

from reloved_engine.hook_templates import Pillar

# Inventory-seeding phase: attract useful listings before promoting discovery heavily.
PILLAR_WEIGHTS: dict[Pillar, float] = {
    "B_DONOR": 0.60,
    "A_MACRO": 0.35,
    "C_FINDER": 0.05,
}


def pick_pillar() -> Pillar:
    pillars = list(PILLAR_WEIGHTS)
    weights = [PILLAR_WEIGHTS[pillar] for pillar in pillars]
    return random.choices(pillars, weights=weights, k=1)[0]


def weekly_plan(number_of_posts: int = 7) -> list[Pillar]:
    """Create a varied plan while preserving the current strategic weighting."""
    if number_of_posts < 1:
        raise ValueError("number_of_posts must be positive")

    plan = [pick_pillar() for _ in range(number_of_posts)]

    # Ensure a seven-post week contains the mission and supply sides.
    if number_of_posts >= 7:
        counts = Counter(plan)
        if counts["B_DONOR"] == 0:
            plan[0] = "B_DONOR"
        if counts["A_MACRO"] == 0:
            plan[-1] = "A_MACRO"

    random.shuffle(plan)
    return plan
