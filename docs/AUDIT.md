# Repository audit — 1 September 2026

## Verdict

**v1 is ready for local, human-reviewed weekly operation.** It is deliberately
not an unattended publishing system: publishing and media generation remain
manual, credential-free boundaries.

## Evidence from this audit

| Area | Status | Evidence / impact |
| --- | --- | --- |
| Python runtime | Ready | The planner runs successfully with the available Python 3.9.6; the package now declares that verified minimum. |
| Installation | Required | Running `python3 scripts/run_weekly.py` before installation fails with `ModuleNotFoundError: reloved_engine`. |
| Weekly planning | Ready | `reloved create` produces a reproducible seven-post job with unique object/context pairs. |
| Draft generation | Ready | Every post receives a deterministic, validated six-slide editable draft. |
| Image generation / overlays | Ready with operator API key | The engine writes deterministic textless prompts, calls the configured OpenAI image model only for approved posts, and renders local 9:16 overlays. |
| Publishing / scheduling | Missing | No Postiz client, platform integration, credentials template, or publishing command exists. |
| Metrics ingestion / analysis | Ready | `reloved metrics` validates and records results; `reloved report` ranks hooks. |
| Learning loop | Ready | New plans use stored hook performance with exploration. |
| Tests and CI | Local verification ready | Automated tests, lint, type check, and package build are configured; CI is not yet configured. |
| Repeatability | Ready | Jobs record a seed and cannot be overwritten without explicit `--force`. |
| Documentation | Repaired | The prior README referred to files and capabilities absent from the repository. The Codex runbook now describes the actual supported process. |

## v1 operating requirements and future scope

1. Install the package in a Python 3.9+ virtual environment and run the local
   verification commands before using a changed version.
2. Keep a human in the review and publishing loop. v1 does not possess
   publishing credentials or authority.
3. If ReLoved later authorises publishing automation, separately implement and
   test a platform/publisher integration, secret handling, platform
   idempotency, failure reporting, and CI.

## Risks that require human review every week

- The macro hooks contain factual claims (for example, recycling ratios) without a cited source.
- Objects, contexts, and hooks are random; the program cannot judge whether an idea is factually accurate, culturally suitable, or repetitive.
- The planned 60/35/5 mix is stochastic. A seven-post plan is not guaranteed to reflect those proportions exactly, and finder posts may be absent.
- A hook's score is a simple weighted engagement rate; it does not account for reach, audience, content quality, recency, or platform changes.

## Recommended operating model

Use Codex as the workspace and reviewer, not as an unattended publisher. Run the planner in Codex, ask Codex to inspect the generated draft against this runbook, then have a person approve creative and complete posting. Reassess automation only after the production blockers above are implemented and verified.
