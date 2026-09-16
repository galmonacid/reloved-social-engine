"""Create a fresh weekly-plan revision via the compatibility command.

``jobs/YYYY-MM-DD/weekly_plan.json`` may already exist from an earlier run (or
from a legacy planner).  The engine preserves that file and writes a timestamped
revision instead, so an intentional weekly run never silently replaces work.
For the full operator workflow, prefer ``reloved create``.
"""

from reloved_engine.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["create", "--force"]))
