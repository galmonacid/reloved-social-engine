# Weekly runbook — ReLoved Social Engine v1

## Scope and guardrails

This tool produces local, editable drafts for ReLoved's Milton Keynes launch
and can publish one approved carousel through the official Instagram API after
an explicit operator command. A human must check facts, local relevance,
creative, brand fit, accessibility, final assets, and every publication
decision. Never add platform credentials to this repository.

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
   `review_flags`. Check that Milton Keynes appears naturally, that the post is
   useful to local donors or finders, and that `#MiltonKeynes` and `#MKLocal`
   are present. Also check UK phrasing, appropriateness, repeated themes, all
   claims, slide progression, CTA, caption, visual treatment, and accessibility.

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
   terminal, create three source visuals and then render the copy overlay.
   Each visual is reused for two adjacent slides, so the six-slide format is
   preserved with half as many billable image requests.
   `generate-images` is billable and intentionally only works after approval.

   ```bash
   reloved generate-images jobs/2026-09-08/weekly_plan.json <post-id>
   reloved overlay jobs/2026-09-08/weekly_plan.json <post-id>
   ```

   The default is `gpt-image-1-mini` at `medium` quality. Only override
   `--model` or `--quality` for posts where review shows that extra fidelity is
   worth the additional cost. The command refuses to overwrite existing raw
   images unless `--force` is supplied, preventing an accidental second set of
   billable calls.

6. Review all six final PNGs in `assets/<post-id>/final/`. Confirm that the
   scenes feel plausible for Milton Keynes without relying on generated text,
   logos or false landmark specificity. Then render the
   Instagram-specific 4:5 JPEG exports and review those too:

   ```bash
   reloved instagram-assets jobs/2026-09-08/weekly_plan.json <post-id>
   ```

   Upload the files from `assets/<post-id>/instagram/` to a public HTTPS
   directory without changing the filenames. Meta must be able to fetch
   `slide-1.jpg` through `slide-6.jpg` without authentication.

7. Confirm that the Instagram account is Professional (Business or Creator)
   and that its Meta app token has `instagram_business_basic` and
   `instagram_business_content_publish`. Set `INSTAGRAM_USER_ID`,
   `INSTAGRAM_ACCESS_TOKEN`, and `INSTAGRAM_IMAGE_BASE_URL` in the shell. Do
   not use the Instagram password and do not save the token in the repository.

8. Verify the target and preview the exact payload before publishing:

   ```bash
   reloved instagram-check
   reloved publish-instagram jobs/2026-09-08/weekly_plan.json <post-id> --dry-run
   reloved publish-instagram jobs/2026-09-08/weekly_plan.json <post-id>
   ```

   The final command creates six child containers, waits for each one, creates
   and waits for the carousel container, publishes it, and saves its media ID
   and permalink in `assets/<post-id>/instagram_publication.json`. It will not
   publish the same post a second time unless `--allow-republish` is supplied.

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

- Do not resume generic UK jobs created before the Milton Keynes localisation.
  The validator rejects them; create a fresh dated job with the current config.
- Creating an existing date fails without changing its file. Use `--force` to
  create a timestamped revision deliberately; the original remains intact.
- Invalid data or duplicate platform post IDs fail with an error and do not
  overwrite stored data.
- `jobs/` and `data/` are local and ignored by Git. Back up approved plans and
  source metric exports where your team stores operational records.

## End-to-end weekly command

For the authorised automatic workflow, create a dedicated secondary Firebase
Hosting site once. Never target the existing app's default site:

```bash
firebase login
firebase hosting:sites:create reloved-social-media --project <firebase-project-id>
export FIREBASE_PROJECT_ID="<firebase-project-id>"
export FIREBASE_HOSTING_SITE="reloved-social-media"
export INSTAGRAM_USER_ID="<professional-account-id>"
export INSTAGRAM_ACCESS_TOKEN="<access-token>"
export OPENAI_API_KEY="<openai-key>"
```

Then run:

```bash
python scripts/run_weekly_full.py --date 2026-10-05 --seed 42
```

This generates and approves seven posts, renders the TikTok and Instagram
assets, deploys all 42 Instagram JPEGs in one Firebase release, and publishes
all seven carousels immediately. `--dry-run` stops before every external API
or deployment action. The command refuses to deploy to a site whose ID equals
the Firebase project ID, which protects the original app's default Hosting
release.
