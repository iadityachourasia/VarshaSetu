# VarshaSetu — Codex Start Here

## Current baseline

Phase 0 stabilization controls are implemented and must be preserved. The
scientific release gate remains open/not passed pending authoritative data
acquisition, forecast/reference provenance, reproducible regime labels, complete
forecast timing metadata, and accumulation-consistent training data.

Status update (2026-09-23): authoritative canonical-v2 2017/2018/2019
forecast/reference corpora and the bounded Phase 2B rainfall-model comparison
are now documented in `docs/53` and `docs/58`–`docs/62`. The Phase 2B work does
not clear the broader release gate or unblock the legacy CSV/API. The starter
prompt below is retained as historical Phase 0 guidance; its acquisition-first
next-task statement is no longer the current canonical-corpus status. Do not
start another phase without explicit authorization.

## First instruction to Codex

Paste this as the first task:

```text
Read AGENTS.md and docs/00_INDEX.md completely before changing code.

Then read:
- docs/01_SIH26080_PROBLEM_STATEMENT.md
- docs/02_PROJECT_AUDIT.md
- docs/03_CURRENT_IMPLEMENTATION.md
- docs/05_ROADMAP.md
- docs/11_SCIENTIFIC_CONSTRAINTS.md
- docs/14_ACCEPTANCE_CRITERIA.md

Do not implement new features yet.

First verify that the protected Phase 0 controls documented in
`docs/30_PHASE0_STABILIZATION_REPORT.md` remain enforced. Do not weaken the
readiness gate, restore quarantined artifacts, or expose unavailable scientific
outputs.

The next scientific task is authoritative paired forecast/reference dataset
acquisition and registration. Do not begin it until explicitly requested.

Preserve working components. Do not rewrite the architecture.

At the end, provide:
- files changed,
- tests/builds run,
- exact results,
- blockers still unresolved,
- the next single highest-priority task.
```

## Development workflow

For each next task:

1. Choose a backlog item from `docs/23_BACKLOG.md`.
2. Use a template from `docs/21_CODEX_TASK_TEMPLATES.md`.
3. Require acceptance criteria.
4. Require tests.
5. Require documentation updates.
6. Make one scientific/architectural concept stable before moving to the next.

## Do not begin with

- dashboard redesign,
- chatbot,
- authentication,
- alerts,
- deployment scaling,
- deep learning,
- “AI explanation” features.

The scientific foundation remains the bottleneck.
