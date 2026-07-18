from __future__ import annotations

import random

OBJECT_LIBRARY: dict[str, tuple[str, ...]] = {
    "kettle": ("moving flat", "upgrading the kitchen", "cost of living"),
    "toaster": ("kitchen clear-out", "barely used", "moving flat"),
    "microwave": ("downsizing", "flat-share change", "moving flat"),
    "blender": ("unused gift", "kitchen clear-out"),
    "coffee machine": ("unused gift", "upgrading the kitchen"),
    "air fryer": ("impulse purchase", "needing more worktop space"),
    "desk chair": ("home-office change", "office upgrade"),
    "dining chair": ("redecorating", "spare furniture"),
    "bedside table": ("downsizing", "moving flat"),
    "coffee table": ("saving space", "redecorating"),
    "floor lamp": ("style change", "decluttering"),
    "mirror": ("redecorating", "no longer fitting the space"),
    "chest of drawers": ("moving flat", "changing storage"),
    "bookshelf": ("decluttering", "moving flat"),
    "winter coat": ("wardrobe clear-out", "season change"),
    "puffer jacket": ("style change", "barely worn"),
    "trainers": ("wrong size", "barely worn"),
    "formal shoes": ("worn once", "no longer needed"),
    "handbag": ("unused gift", "style change"),
    "baby clothes bundle": ("child outgrown them", "season change"),
    "baby high chair": ("child outgrown it", "short-term use"),
    "pram": ("baby grown up", "no longer needed"),
    "baby cot": ("child outgrown it", "moving home"),
    "toy box": ("children getting older", "decluttering"),
    "children's bicycle": ("child outgrown it", "moving to a larger size"),
    "rug": ("redecorating", "style change"),
    "wall art": ("moving flat", "redecorating"),
    "plant pot": ("decluttering", "changing interior style"),
    "table lamp": ("unused spare", "style change"),
    "storage box": ("decluttering", "reducing possessions"),
}


def pick_random_object() -> tuple[str, str]:
    object_name = random.choice(tuple(OBJECT_LIBRARY))
    return object_name, random.choice(OBJECT_LIBRARY[object_name])
