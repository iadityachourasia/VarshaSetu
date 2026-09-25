# Contribution & Change Protocol

## Branch/task discipline

One task should address one coherent objective.

Avoid mixed commits containing:
- ML architecture change,
- frontend redesign,
- unrelated refactor,
- deployment changes.

## Before coding

Read:
- `AGENTS.md`,
- relevant docs,
- existing implementation.

State:
- problem,
- files likely affected,
- acceptance criteria.

## Scientific changes require

When changing:
- data,
- features,
- model,
- thresholds,
- split,
- metric,

also update:
- experiment record,
- relevant methodology doc,
- tests.

## API changes require

Update:
- Pydantic schemas,
- `docs/12_API_CONTRACT.md`,
- frontend type definitions,
- UI mapping if relevant.

## Frontend scientific changes require

Update:
- `docs/13_UI_DATA_CONTRACT.md`.

## Pull-request / task completion summary

Use:

```text
Summary:
Scientific/technical reason:
Files changed:
Tests:
Results:
Data/model implications:
Known limitations:
Follow-up:
```

## Review checklist

- [ ] Requirement traceability clear.
- [ ] No hidden data dependency.
- [ ] No new leakage.
- [ ] No fake scientific value.
- [ ] Tests updated.
- [ ] Docs updated.
- [ ] Claims match evidence.
