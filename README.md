# ReLoved Social Engine

A local, human-in-the-loop workflow for ReLoved's UK TikTok and Instagram
content. It creates a reviewable seven-post weekly job, with a validated
British-English six-slide draft for every post; records approvals and observed
performance; and uses recorded hook performance in future plans.

## Current operational status

v1 is ready for local, human-reviewed weekly operation after a Python 3.9+
environment is installed. It can build deterministic textless image prompts,
generate source images through the OpenAI Images API when explicitly asked,
and add local text overlays. It does not publish posts. A person must verify
claims, final copy, visuals, and publication decisions.

Use [the weekly Codex runbook](docs/WEEKLY_RUNBOOK.md) for the supported workflow and [the audit](docs/AUDIT.md) for the complete readiness assessment.

## What works today

- Produces reproducible seven-post jobs with a seed, timestamps, unique
  object/context pairs, and the 60% donor / 35% macro / 5% finder strategy.
- Creates and validates editable six-slide copy drafts against the v1.2
  contract, including British-English and ReLoved CTA requirements.
- Preserves existing jobs by default; `--force` creates a new revision.
- Records individual approval/rejection decisions with notes.
- Logs non-negative metrics once per published-post ID and ranks hook templates
  by weighted engagement score.
- Generates six locked, textless UK visual prompts per approved post and can
  render six consistent 9:16 final PNGs from generated source images.

## One-time setup

This project is designed to be run from its repository folder in Codex's integrated terminal. It needs Python 3.9 or later; the system `python3` on this machine was Python 3.9.6 during the audit and is supported.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Then create a draft job (the seed makes the output reproducible):

```bash
reloved create --date 2026-09-08 --seed 42
```

Inspect and approve the individual drafts only after human review:

```bash
reloved inspect jobs/2026-09-08/weekly_plan.json
# Copy the generated post ID from `reloved inspect`, e.g. weekly-2026-09-08-ab12cd34-1
reloved review jobs/2026-09-08/weekly_plan.json weekly-2026-09-08-ab12cd34-1 approve --note "Copy checked"
```

Record verified platform metrics after publishing outside this tool, then review
the learning signal before the next plan:

```bash
reloved metrics tiktok-123 B_DONOR B1_worked --views 1000 --likes 40 --comments 4 --shares 3 --saves 8
reloved report
```

## Visual production

Review and approve a post first. You can inspect the prompt plan without API
credentials; it is deterministic and is written beside the job:

```bash
reloved visual-plan jobs/2026-09-08/weekly_plan.json <post-id>
```

To create the six billable source images, copy `.env.example` to `.env`, set
`OPENAI_API_KEY`, export it in your shell, then run:

```bash
reloved generate-images jobs/2026-09-08/weekly_plan.json <post-id>
reloved overlay jobs/2026-09-08/weekly_plan.json <post-id>
```

The final 1080×1920 PNGs are placed in the post's `assets/<post-id>/final/`
folder. See [the visual locks](docs/visual/visual_locks_textless.md) before
approving any visual output.

Use `reloved create --force` only when deliberately creating a timestamped
revision for the same date. The older compatibility command
`python scripts/run_weekly.py` still creates today's first job.

## Repository structure

- `GOAL.md`: current delivery criteria, evidence, and known risks.
- `docs/WEEKLY_RUNBOOK.md`: the operator procedure.
- `docs/prompts/`: prompt contract for a future copy-generation step.
- `src/reloved_engine/`: planning and performance-selection modules.
- `scripts/reloved.py`: CLI compatibility wrapper (the installed command is `reloved`).
- `jobs/`: locally generated weekly plans (ignored by Git).
- `data/`: locally generated performance data (ignored by Git).
