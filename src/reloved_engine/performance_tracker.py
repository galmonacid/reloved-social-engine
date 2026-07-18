from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PostResult:
    post_id: str
    pillar: str
    hook_template_id: str
    views: int
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0

    @property
    def score(self) -> float:
        views = max(self.views, 1)
        weighted_engagement = self.likes + 3 * self.comments + 5 * self.shares + 4 * self.saves
        return weighted_engagement / views


class HookPerformanceTracker:
    def __init__(self, path: str | Path = "data/hook_performance.json") -> None:
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"version": 1, "templates": {}, "posts": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def log(self, result: PostResult) -> None:
        template = self.data["templates"].setdefault(
            result.hook_template_id,
            {"pillar": result.pillar, "uses": 0, "average_score": 0.0},
        )
        uses = template["uses"]
        template["average_score"] = (
            template["average_score"] * uses + result.score
        ) / (uses + 1)
        template["uses"] = uses + 1
        self.data["posts"].append({**asdict(result), "score": result.score})
        self.save()

    def choose(self, template_ids: list[str], exploration: float = 0.25) -> str:
        if not template_ids:
            raise ValueError("template_ids cannot be empty")
        if random.random() < exploration:
            return random.choice(template_ids)

        values = []
        for template_id in template_ids:
            stats = self.data["templates"].get(template_id)
            average = stats["average_score"] if stats else 0.02
            uses = stats["uses"] if stats else 0
            # A small confidence adjustment, capped to prevent one hook dominating forever.
            values.append(average * (1 + min(uses, 10) / 20))

        maximum = max(values)
        weights = [math.exp(value - maximum) for value in values]
        return random.choices(template_ids, weights=weights, k=1)[0]
