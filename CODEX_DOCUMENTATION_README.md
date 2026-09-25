# VarshaSetu — Codex Development Documentation Pack

This folder is the documentation and scientific-governance pack for
**VarshaSetu — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts**,
implementing SIH26080. The original audit covered repository identities including
`DigiVarsha` and `Vrishti AI`; those names remain only where historical
traceability requires them.

It was generated after a code-level audit of the uploaded project ZIP, including:
- repository structure,
- backend/API code,
- ML models and training flow,
- serialized model artifacts,
- saved evaluation report,
- checked-in dataset,
- frontend pages and API usage,
- tests,
- scientific claims and verification logic.

## How to use

Copy:
- `AGENTS.md` into the **repository root**.
- the entire `docs/` directory into the repository root.

Recommended final structure:

```text
VarshaSetu/
├── AGENTS.md
├── README.md
├── docs/
│   ├── 00_INDEX.md
│   ├── 01_SIH26080_PROBLEM_STATEMENT.md
│   ├── 02_PROJECT_AUDIT.md
│   ├── ...
│   └── 21_CODEX_TASK_TEMPLATES.md
├── backend/
├── frontend/
├── data/
└── ...
```

Then instruct Codex:

> Read `AGENTS.md` and `docs/00_INDEX.md` before making changes. Begin with Phase 0 in `docs/05_ROADMAP.md`. Do not implement new visual/USP features until Phase 0 blockers and Phase 1 mandatory SIH requirements are addressed in dependency order.

## Most important current conclusion

The audited project already contains a genuine ML/post-processing skeleton, but it is not yet reproducible or fully scientifically defensible.

Preserve the useful architecture; fix the data and verification foundation before expanding the feature set.

## Evidence status convention

The documentation uses four evidence classes:

- **Verified** — directly established from checked-in code/data/artifacts.
- **Unverified** — claimed or implied by project content but not provable from the provided repository.
- **Planned** — desired target state.
- **External** — supported by official/research sources, not by the local repository itself.

Do not silently convert an unverified claim into a verified claim.
