# Weekly runbook — ReLoved Social Engine v1

## Scope and guardrails

This tool produces local, editable **drafts**, not published content. It never
connects to TikTok, Instagram, or a scheduler. A human must check facts,
creative, brand fit, accessibility, final assets, and publication decisions.
Never add platform credentials to this repository.

## One-time setup

From the repository root, create the environment and install the operator CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Confirm the installation with `reloved --help`.

## Create and review the week

1. Create a dated job. Keep the printed path; the seed makes a plan reproducible.

   ```bash
   reloved create --date 2026-09-08 --seed 42
   ```

2. Inspect the job and read every full `draft` in
   `jobs/2026-09-08/weekly_plan.json`. In particular, resolve any
   `review_flags`; `A1_ratio` requires a current, credible source before it can
   be used. Check UK phrasing, appropriateness, repeated themes, all claims,
   slide progression, CTA, caption, visual treatment, and accessibility.

   ```bash
   reloved inspect jobs/2026-09-08/weekly_plan.json
   ```

3. Approve or reject every draft after that review. A job is ready only when all
   seven are approved. A decision is final in v1; create a new revision for
   revised creative rather than changing an approved/rejected record.

   ```bash
   # Copy each generated post ID from `reloved inspect`.
   reloved review jobs/2026-09-08/weekly_plan.json weekly-2026-09-08-ab12cd34-1 approve --note "Claims and copy checked"
   reloved review jobs/2026-09-08/weekly_plan.json weekly-2026-09-08-ab12cd34-2 reject --note "Replace unsupported claim"
   ```

4. For each approved post, first materialise and review the deterministic,
   textless visual prompts. This does not make an API call:

   ```bash
   reloved visual-plan jobs/2026-09-08/weekly_plan.json <post-id>
   ```

5. If the prompt plan is suitable and `OPENAI_API_KEY` is configured in the
   terminal, create the six source images and then render the copy overlay.
   `generate-images` is billable and intentionally only works after approval.

   ```bash
   reloved generate-images jobs/2026-09-08/weekly_plan.json <post-id>
   reloved overlay jobs/2026-09-08/weekly_plan.json <post-id>
   ```

6. Review all six final PNGs in `assets/<post-id>/final/`, then schedule or
   publish them manually in the appropriate platform. Retain the platform post
   ID for each published item.

## Record learning

When platform figures are meaningful and verified, log each post once:

```bash
reloved metrics tiktok-123 B_DONOR B1_worked --views 1000 --likes 40 --comments 4 --shares 3 --saves 8
reloved report
```

The weighted score is `(likes + 3*comments + 5*shares + 4*saves) / views`.
The report is only a lightweight learning signal; it does not establish causal
performance or replace creative judgement.

## Recovery

- Creating an existing date fails without changing its file. Use `--force` to
  create a timestamped revision deliberately; the original remains intact.
- Invalid data or duplicate platform post IDs fail with an error and do not
  overwrite stored data.
- `jobs/` and `data/` are local and ignored by Git. Back up approved plans and
  source metric exports where your team stores operational records.
