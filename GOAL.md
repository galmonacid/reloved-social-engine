# ReLoved Social Engine v1 delivery log

## Objective

Deliver a reliable, local, human-in-the-loop workflow for producing, reviewing,
approving, measuring, and learning from ReLoved's seven-post weekly social
content plan. v1 deliberately does **not** publish posts or generate media:
both require credentials and human creative approval outside this repository.

## Measurable acceptance criteria

1. A command creates a seven-post weekly job with a stable ID, UTC/London
   timestamps, seed, strategic pillar mix, unique object/context combinations,
   and a six-slide British-English draft for every post.
2. Every generated draft is validated against the documented v1.2 content
   contract: six concise slides, supplied hook on slide one, ReLoved CTA on
   slide six, supported pillars, no banned terms, five-or-fewer hashtags, and
   valid optional scene-plan values.
3. A job is immutable by default: a second command cannot silently replace it;
   an explicit force option creates a timestamped revision while preserving the
   original.
4. A reviewer can list drafts, approve/reject an individual post with a note,
   and the system only reports a job ready when all seven posts are approved.
5. A command records validated post metrics and a report ranks hook templates
   by observed performance, including use count and average weighted score.
6. Invalid arguments, malformed plans, unknown IDs, duplicate metric records,
   and invalid status transitions fail with useful errors and leave durable
   data valid.
7. Automated tests cover core planning, validation, job lifecycle, approvals,
   metrics, and CLI behaviour. Ruff and package build pass. A real CLI
   smoke-run demonstrates the intended workflow.
8. Documentation gives a new operator exact setup, review, approval, metrics,
   and recovery steps, and accurately states v1's non-goals.

## Delivery plan and backlog

- [x] Inspect the starting repository and audit its current behaviour.
- [x] Establish v1 scope and measurable acceptance criteria.
- [x] Design the versioned job schema, deterministic planner, and validation.
- [x] Implement the operator CLI: create, inspect, review, metrics, report.
- [x] Add automated test suite and packaging/quality configuration.
- [x] Run verification, perform independent code review, and fix findings.
- [x] Reassess every acceptance criterion with recorded evidence.

## Completed work

- 2026-09-01: Audited baseline. It contained only stochastic weekly ideation
  and a low-level hook tracker; it had no tests, content creation, approval
  workflow, CLI lifecycle, metrics command, reporting command, or build tool.
- 2026-09-01: Defined a safe v1 boundary: local draft creation and learning
  loop, never unattended publishing.
- 2026-09-01: Implemented `reloved` CLI and versioned job model, generated
  validated draft packages, terminal review decisions, atomic metric persistence
  and hook reporting. Force revisions have collision-proof names and posts have
  revision-specific IDs.
- 2026-09-01: Added strict type checking and ten regression tests. Two
  independent reviews found contract, malformed-data, ID collision, and atomic
  persistence issues; all material findings were fixed and retested. Final
  re-reviews found no remaining material issues.

## Discovered work / risks

- Existing hook `A1_ratio` makes an uncited factual claim. Generated posts flag
  it for source verification before approval; human review remains mandatory.
- Repository had uncommitted pre-existing edits to README, pyproject, scripts,
  and .gitignore. Preserve them unless a v1 implementation change intentionally
  supersedes them.
- Isolated package builds need network access to fetch standard build tooling;
  this was permitted for the recorded verification below.

## Evidence

- Baseline: `.venv/bin/python -m pytest -q` found no tests.
- Final gate (2026-09-01): `pytest -q` — 10 passed; `ruff check .` — passed;
  `mypy src` — no issues in 8 source files; `python -m build --wheel` — wheel
  built successfully.
- Final CLI smoke run: created a seed-202 dated job, validated all seven drafts
  and their unique IDs, approved a post, logged metrics, displayed ranked hook
  performance, and rejected a malformed job through a useful CLI error.

## Blockers

None. Publishing/media generation remain intentional v1 non-goals because no
publisher credentials, target API, brand assets, or publication authority were
provided.
