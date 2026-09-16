from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from reloved_engine.hook_templates import HOOK_TEMPLATES, Pillar


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

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "templates": {}, "posts": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid performance data: {self.path}") from error
        if not isinstance(data.get("templates"), dict) or not isinstance(data.get("posts"), list):
            raise ValueError(f"Invalid performance data structure: {self.path}")  # noqa: TRY004
        return cast(dict[str, Any], data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        temporary.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def log(self, result: PostResult) -> None:
        if not result.post_id.strip() or not result.hook_template_id.strip():
            raise ValueError("post_id and hook_template_id are required")
        if any(value < 0 for value in (result.views, result.likes, result.comments, result.shares, result.saves)):
            raise ValueError("metrics cannot be negative")
        if result.pillar not in HOOK_TEMPLATES:
            raise ValueError("pillar must be supported")
        templates = {template.id for template in HOOK_TEMPLATES[cast(Pillar, result.pillar)]}
        if result.hook_template_id not in templates:
            raise ValueError("hook_template_id must belong to the supplied pillar")
        if any(post["post_id"] == result.post_id for post in self.data["posts"]):
            raise ValueError(f"metrics already logged for post_id {result.post_id}")
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

    def report(self) -> list[dict[str, Any]]:
        """Return hook performance in descending weighted-score order."""
        return [
            {"hook_template_id": template_id, **stats}
            for template_id, stats in sorted(
                self.data["templates"].items(),
                key=lambda item: (-item[1]["average_score"], item[0]),
            )
        ]

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
