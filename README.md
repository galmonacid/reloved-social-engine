# ReLoved Social Engine

AI-assisted content engine for ReLoved's UK TikTok and Instagram marketing.

The engine prepares one six-slide photo carousel per day. It generates British-English copy, builds deterministic textless image prompts, renders consistent text overlays, records performance, and can hand drafts to a publishing integration.

## Current content mix

During the inventory-seeding phase:

- Donor: 60%
- Macro waste and reuse: 35%
- Finder: 5%

Increase Finder content once the app has enough useful listings to fulfil the promise made by the posts.

## Weekly workflow

1. Generate seven briefs with `python scripts/run_weekly.py`.
2. Review generated packages and images.
3. Upload or schedule drafts through the configured publishing integration.
4. Add a current TikTok sound manually and publish one post per day.
5. Record metrics in `data/performance.csv`.
6. Run `python scripts/analyse_performance.py` before the next batch.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Fill in the API credentials in `.env`.

## Project structure

- `docs/`: content doctrine, prompts, visual rules and operating playbook.
- `src/reloved_engine/`: reusable engine modules.
- `scripts/`: weekly generation and analytics entry points.
- `data/`: local performance data and generated state.
- `jobs/`: generated post packages and media.

## Status

The text generation, scheduling, deterministic prompt construction, overlay rendering and performance tracking are implemented. Image generation and Postiz are isolated behind clients so their API payloads can be updated without changing the rest of the engine.
