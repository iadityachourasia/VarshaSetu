# Architecture & Scientific Decision Log

Use this file to preserve why decisions were made.

## DEC-001 — Preserve React + FastAPI

**Status:** Accepted  
**Reason:** Existing architecture is appropriate for a Python ML service and already implemented.

## DEC-002 — Do not rewrite from scratch

**Status:** Accepted  
**Reason:** Existing baseline, classifier, specialist models, metrics, API, and UI are reusable.

## DEC-003 — Keep Linear MOS baseline

**Status:** Accepted  
**Reason:** Saved audit result indicates MOS currently has lower overall RMSE than the regime-aware model. It is a necessary control.

## DEC-004 — Regime-aware superiority is a hypothesis, not an assumption

**Status:** Accepted  
**Reason:** Must be demonstrated against non-regime baselines.

## DEC-005 — Move toward soft MoE

**Status:** Planned  
**Reason:** Existing architecture already has regime probabilities and specialist models. Soft weighting better handles uncertain transitions.

## DEC-006 — FSS requires gridded data

**Status:** Accepted  
**Reason:** Conventional FSS is spatial-neighbourhood verification and is an explicit PS deliverable.

## DEC-007 — Correct 24-hour heavy-rain product

**Status:** Accepted  
**Reason:** Current thresholds and 6-hour target are semantically mismatched.

## DEC-008 — No current claim of authoritative raw-NWP provenance

**Status:** Accepted until evidence changes  
**Reason:** Repository lacks source lineage sufficient to verify the claim.

## DEC-009 — Historical replay vs operational forecast

**Status:** Accepted  
**Reason:** Current endpoint uses historical rows including known observation. UI must call it replay until live forecast ingestion exists.

## DEC-010 — Frontend cannot originate scientific values

**Status:** Accepted  
**Reason:** Prevents misleading demo-only analytics.

## DEC-011 — Fail closed while Phase 0 scientific inputs are unresolved

**Status:** Accepted  
**Date:** 2026-09-19  
**Reason:** The checked-in dataset is not the dataset behind the saved artifacts,
has no reproducible regime labels, and lacks forecast-source/timing provenance.
Training, artifact inference, metrics, probabilities, and sandbox prediction are
therefore blocked. The API and frontend expose readiness/provenance status only.

## DEC-012 — Quarantine rather than delete legacy evidence

**Status:** Accepted  
**Date:** 2026-09-19  
**Reason:** The saved report and model files document the audited prototype but
cannot support reproducible claims. They remain in place with explicit warnings
and are excluded from executable current-results paths.

## DEC-013 — Product Identity Migration to VarshaSetu

**Status:** Accepted  
**Date:** 2026-09-19  
**Previous names:** DigiVarsha, Vrishti AI, NEPHOS AI, and the workspace label Varsha-NXT  
**Canonical product name:** VarshaSetu  
**Technical title:** Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Positioning line:** Bridging Raw NWP Forecasts and Actionable Rainfall Intelligence  
**Reason:** VarshaSetu expresses SIH26080's intended role as a bridge between raw
NWP guidance and actionable rainfall intelligence. The migration changes product
identity only; it does not change scientific readiness, data, models, or outputs.

---

## Decision template

```text
## DEC-XXX — Title

Status: Proposed | Accepted | Superseded | Rejected
Date:
Owner:

Context:
Decision:
Alternatives considered:
Scientific implications:
Engineering implications:
Acceptance evidence:
```
