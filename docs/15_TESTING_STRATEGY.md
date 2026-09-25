# Testing Strategy

## Testing philosophy

Scientific software needs more than endpoint/UI tests.

Tests must cover:
- data semantics,
- temporal alignment,
- leakage,
- metric mathematics,
- model behavior,
- API contracts,
- frontend scientific integrity.

## Test layers

### 1. Pure unit tests

#### Metrics
Hand-computed examples for:
- RMSE,
- POD,
- FAR,
- CSI,
- ETS,
- Brier,
- FSS.

For FSS include:
- perfect match,
- complete mismatch,
- slightly displaced event,
- multiple window sizes.

#### Accumulation
Test:
- four 6-hour periods aggregate correctly,
- missing period behavior,
- timezone/window boundaries.

#### Geography
Test:
- district weighting sums to 1 within tolerance,
- masked cells handled consistently.

### 2. Data-contract tests

For every forecast dataset:
- required metadata present,
- units recognized,
- init < valid,
- lead matches timestamp difference,
- accumulation duration valid,
- lat/lon/grid unique,
- no duplicate run/grid/valid records.

### 3. Leakage tests

Do not rely only on keyword matching.

Test feature registry:
- all dynamic features have source,
- all inference features `available_at_issue_time=true`,
- target/reference fields blocked.

### 4. Split tests

Check:
- no overlapping timestamps/events,
- final test period frozen,
- calibration fit excludes final test.

### 5. Model tests

- rainfall predictions nonnegative,
- probabilities ∈ [0,1],
- probability rows/classes sum correctly where required,
- serialization round-trip,
- deterministic seed where expected,
- no NaN outputs.

### 6. Integration tests

Historical replay:
```text
forecast source
→ processing
→ regime
→ correction
→ probability
→ verification
→ API response
```

District:
```text
grid
→ polygon aggregation
→ API
```

### 7. API contract tests

Use FastAPI test client.

Validate:
- status codes,
- response schemas,
- metadata,
- missing-run behavior,
- invalid lead behavior.

### 8. Frontend tests

At minimum:
- TypeScript build,
- lint,
- page renders against API fixtures.

Recommended:
- Playwright for critical demo path.

## Scientific regression tests

Freeze a tiny deterministic fixture containing:
- one dry case,
- one moderate rain case,
- one heavy case,
- a small 2-D FSS example.

These tests should catch accidental formula changes.

## Current test debt to fix first

Audited:
- import path failure during `pytest` collection,
- stale temporal split expectations,
- dependency on unavailable external dataset/hash.

Fix these before adding a large new test suite.

## CI target

Eventually run:

```bash
# backend
python -m pytest -q

# frontend
npm ci
npm run build
npm run lint
```

Plus scientific data-contract tests on small fixtures, not huge production datasets.
