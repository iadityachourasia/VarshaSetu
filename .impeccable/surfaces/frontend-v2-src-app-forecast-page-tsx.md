---
version: 1
slug: "frontend-v2-src-app-forecast-page-tsx"
primary_target: "frontend-v2/src/app/forecast/page.tsx"
related_targets: []
---

# Forecast Explorer

Mode: Operate. Primary target: `frontend-v2/src/app/forecast/page.tsx`.

Audience and job: meteorological/scientific reviewers compare one historical GEFS forecast with frozen correction and IMD observation, inspect exact 0.25-degree cells, and understand regime context without mistaking the system for live operations.

Proof and constraints: every value comes from the read-only science API; the three 49×49 maps share extent, scale, legend, and paired validity mask; frozen outputs, lineage, and limitations are preserved. The legacy frontend remains separate.

## Direction contract

THESIS: A disciplined weather-operations workspace makes the three-field comparison the working surface; it refuses a generic KPI-card dashboard.

OWN-WORLD: A near-navy scientific canvas, fine dividers, compact Geist typography, restrained teal interaction states, and shared rainfall colors. Map panels are peers; a collapsible evidence inspector carries metadata without crowding the domain.

STORY: Select a verified historical case, compare Raw GEFS with VarshaSetu correction and IMD observation, inspect one cell and regime probabilities, then follow the same case into extremes, districts, and verification.

FIRST VIEWPORT: At 1440×900, a narrow left rail and short contextual bar leave most of the screen to three aligned square map planes. The case strip sits immediately above them, a single shared rainfall legend and compact selected-cell readout below, and an inspector opens on demand. The primary action is case selection; the signature interaction is synchronized map motion with one exact cell readout across all three fields.

FORM: User-approved hybrid of Meteorological Operations Centre and Scientific Decision Platform, with Modern Earth Intelligence reserved for Overview. The Impeccable direction roll ran with seed `bbb42a64`; the explicit approved direction takes precedence over the assigned fifth candidate.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
