from reloved_engine.cli import main


def test_cli_workflow(tmp_path, capsys):
    jobs = tmp_path / "jobs"
    assert main(["create", "--jobs-dir", str(jobs), "--date", "2026-09-10", "--seed", "99"]) == 0
    job_file = jobs / "2026-09-10" / "weekly_plan.json"
    assert main(["inspect", str(job_file)]) == 0
    assert '"ready": false' in capsys.readouterr().out
    from reloved_engine.jobs import load_job

    post_id = load_job(job_file)["posts"][0]["id"]
    assert main(["review", str(job_file), post_id, "approve"]) == 0
    assert main(["metrics", "published-1", "B_DONOR", "B1_worked", "--views", "100", "--likes", "2",
                 "--data-file", str(tmp_path / "metrics.json")]) == 0
    assert main(["report", "--data-file", str(tmp_path / "metrics.json")]) == 0


def test_cli_returns_useful_failure(tmp_path, capsys):
    assert main(["review", str(tmp_path / "missing.json"), "post", "approve"]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_cli_writes_deterministic_visual_plan(tmp_path, capsys):
    jobs = tmp_path / "jobs"
    assert main(["create", "--jobs-dir", str(jobs), "--date", "2026-09-11", "--seed", "12"]) == 0
    job_file = jobs / "2026-09-11" / "weekly_plan.json"
    from reloved_engine.jobs import load_job

    post_id = load_job(job_file)["posts"][0]["id"]
    assert main(["visual-plan", str(job_file), post_id]) == 0
    assert (jobs / "2026-09-11" / "assets" / post_id / "image_prompts.json").exists()
    assert "Wrote deterministic image prompts" in capsys.readouterr().out
