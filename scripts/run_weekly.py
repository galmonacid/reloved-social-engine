from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from reloved_engine.hook_templates import HOOK_TEMPLATES, render_hook
from reloved_engine.object_library import pick_random_object
from reloved_engine.performance_tracker import HookPerformanceTracker
from reloved_engine.scheduler import weekly_plan


def main() -> None:
    tracker = HookPerformanceTracker()
    posts = []

    for index, pillar in enumerate(weekly_plan(7), start=1):
        object_name, context = pick_random_object()
        candidates = HOOK_TEMPLATES[pillar]
        template_id = tracker.choose([candidate.id for candidate in candidates])
        template = next(candidate for candidate in candidates if candidate.id == template_id)

        posts.append(
            {
                "day": index,
                "pillar": pillar,
                "object": object_name,
                "context": context,
                "hook_template_id": template.id,
                "hook": render_hook(template),
                "status": "IDEA",
            }
        )

    output_dir = Path("jobs") / date.today().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "weekly_plan.json"
    output_file.write_text(json.dumps({"posts": posts}, indent=2), encoding="utf-8")

    print(f"Created {len(posts)}-post weekly plan at {output_file}")
    for post in posts:
        print(
            f"{post['day']}: {post['pillar']} | {post['object']} | "
            f"{post['hook_template_id']} | {post['hook']}"
        )


if __name__ == "__main__":
    main()
