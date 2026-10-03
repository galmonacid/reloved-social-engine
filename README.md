# ReLoved Social Engine

A local, human-in-the-loop workflow for ReLoved's UK TikTok and Instagram
content. It creates a reviewable seven-post weekly job, with a validated
British-English six-slide draft for every post; records approvals and observed
performance; and uses recorded hook performance in future plans.

## Current operational status

v1 is ready for local, human-reviewed weekly operation after a Python 3.9+
environment is installed. It can build deterministic textless image prompts,
generate source images through the OpenAI Images API when explicitly asked,
and add local text overlays. An approved carousel can be published through
Meta's official Instagram API with an explicit operator command. A person must
verify claims, final copy, visuals, and every publication decision.

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
- Generates six locked, textless UK visual prompts per approved post, creates
  three source visuals, and reuses them across six consistent 9:16 final PNGs.

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

To create the three billable source images, copy `.env.example` to `.env`, set
`OPENAI_API_KEY`, export it in your shell, then run:

```bash
reloved generate-images jobs/2026-09-08/weekly_plan.json <post-id>
reloved overlay jobs/2026-09-08/weekly_plan.json <post-id>
```

The final 1080×1920 PNGs are placed in the post's `assets/<post-id>/final/`
folder. See [the visual locks](docs/visual/visual_locks_textless.md) before
approving any visual output.

The economical defaults are `gpt-image-1-mini` at `medium` quality. Each visual
is reused for two adjacent slides, reducing billable image requests from 42 to
21 per seven-post week before the cheaper-model saving. Override deliberately
with `--model` and `--quality`, or `OPENAI_IMAGE_MODEL` and
`OPENAI_IMAGE_QUALITY`, when a particular post needs more fidelity.
Existing raw images are protected from accidental regeneration; the per-post
command requires an explicit `--force` before it will make replacement calls.

## Instagram publication

The publisher uses the Instagram API with Instagram Login and Graph API
`v26.0`. The Instagram account must be a **Professional** account (Business or
Creator), connected to a Meta developer app that has Instagram API access. The
app/account authorisation needs `instagram_business_basic` and
`instagram_business_content_publish`. The account email and password are never
used by this project. Start with Meta's
[Instagram Login setup guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started)
and [content-publishing reference](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing).

Meta's image publishing endpoint requires JPEG, no more than 8 MiB, and an
aspect ratio from 4:5 through 1.91:1. The existing 9:16 PNGs are retained for
TikTok. After reviewing them, create dedicated 1080×1350 Instagram JPEGs:

```bash
reloved instagram-assets jobs/2026-09-08/weekly_plan.json <post-id>
```

Meta fetches carousel images from the internet; it does not accept files
directly from this machine. Upload the six files in
`assets/<post-id>/instagram/` to a public HTTPS directory, preserving the names
`slide-1.jpg` through `slide-6.jpg`. The URLs must remain reachable until Meta
has created the containers.

Set these values in the shell (or load them from a local `.env`; never commit
the token):

```bash
export INSTAGRAM_USER_ID="<Instagram professional account ID>"
export INSTAGRAM_ACCESS_TOKEN="<Instagram user access token>"
export INSTAGRAM_IMAGE_BASE_URL="https://cdn.example.com/reloved/<post-id>"
```

Verify the authorised account, validate the publication without making API
changes, and then publish deliberately:

```bash
reloved instagram-check
reloved publish-instagram jobs/2026-09-08/weekly_plan.json <post-id> --dry-run
reloved publish-instagram jobs/2026-09-08/weekly_plan.json <post-id>
```

Instead of `INSTAGRAM_IMAGE_BASE_URL`, pass `--image-url` exactly six times in
slide order. A successful call writes
`assets/<post-id>/instagram_publication.json`, including the Instagram media ID
and permalink but no access token. The command refuses to post again while
that receipt exists unless `--allow-republish` is supplied explicitly.

### One-command weekly production and publication

When automatic approval is permitted by your operating policy, run all of
the production steps together. The command creates and approves the seven
drafts, generates both image formats, deploys 42 JPEGs to Firebase Hosting,
and immediately publishes all seven Instagram carousels.

Use a dedicated secondary Hosting site in the existing Firebase project. Do
not use the project's default site because a Hosting deployment replaces that
site's current release. Create and authenticate the secondary site once:

```bash
firebase login
firebase hosting:sites:create reloved-social-media --project <firebase-project-id>
export FIREBASE_PROJECT_ID="<firebase-project-id>"
export FIREBASE_HOSTING_SITE="reloved-social-media"
```

The weekly runner deliberately rejects a Hosting site ID that equals the
Firebase project ID, protecting the original app's default Hosting site. It
also verifies the Instagram account before making the billable image calls.

```bash
python scripts/run_weekly_full.py --date 2026-09-08 --seed 42
```

Use `--dry-run` to verify creation, approvals, and visual plans without image
generation, Firebase deployment, or Instagram publication. Use `--force` to
create a timestamped revision for an existing date. A live run requires
`OPENAI_API_KEY`, `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN`,
`FIREBASE_PROJECT_ID`, and `FIREBASE_HOSTING_SITE`.

Important: this command publishes all seven posts immediately; it does not
schedule them across seven days. Successful Instagram receipts remain under
each post's asset directory, and the Firebase deployment manifest is written
to the job's `firebase-hosting/deployment.json`.

### One-command daily carousel or Reel

The daily runners create a one-post `daily_plan.json` and perform the same
approval, generation, hosting, and publication flow for that post only:

```bash
python scripts/run_daily_carousel.py --date 2026-10-03 --seed 42
python scripts/run_daily_reel.py --date 2026-10-04 --seed 43
```

The Reel runner requires `ffmpeg`. It turns the six 9:16 final slides into a
12-second H.264 MP4 by default (`--slide-seconds` changes the per-slide time),
then selects the first music result from Instagram's current authorized
trending list and attaches it when publishing. Pass `--audio-id <id>` to pin a
specific authorized track instead.

Instagram's Audio API is only available with Facebook Login. For the Reel
runner, the account must be linked to a Facebook Page and the Reel calls use
`graph.facebook.com`. Set `INSTAGRAM_FACEBOOK_PAGE_ACCESS_TOKEN` to that Page's
Facebook Login access token and `INSTAGRAM_FACEBOOK_USER_ACCESS_TOKEN` to the
corresponding Facebook User access token; the authorization needs
`instagram_basic` and `instagram_content_publish`. An `IG...` Instagram Login
token cannot be used for this flow. `INSTAGRAM_ACCESS_TOKEN` remains the token
for the carousel and weekly Instagram Login runners. The authorized API
catalog can differ from the audio visible in the Instagram app.

Both commands support `--dry-run`, `--force`, and `--resume-job`. A successful
Reel writes `instagram_reel_publication.json`; the carousel continues to write
`instagram_publication.json`.

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
