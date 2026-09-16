import pytest

from reloved_engine.performance_tracker import HookPerformanceTracker, PostResult


def test_metrics_are_logged_ranked_and_protected_from_bad_input(tmp_path):
    tracker = HookPerformanceTracker(tmp_path / "metrics.json")
    tracker.log(PostResult("post-1", "B_DONOR", "B1_worked", 100, likes=2, shares=1))
    tracker.log(PostResult("post-2", "B_DONOR", "B2_unused", 100, likes=5))

    assert [entry["hook_template_id"] for entry in tracker.report()] == ["B1_worked", "B2_unused"]
    with pytest.raises(ValueError, match="already logged"):
        tracker.log(PostResult("post-1", "B_DONOR", "B1_worked", 100))
    with pytest.raises(ValueError, match="cannot be negative"):
        tracker.log(PostResult("post-3", "B_DONOR", "B1_worked", -1))
    with pytest.raises(ValueError, match="pillar must be supported"):
        tracker.log(PostResult("post-4", "not-a-pillar", "B1_worked", 1))
