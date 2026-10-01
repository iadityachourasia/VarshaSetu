# Phase 8C: independent regime validation, source and licence probe (no labelling)

Date: 2026-10-01. **No label was created, no data downloaded, no model touched.** This is the planned first step of independent regime validation: find out which independent, observation-based
sources could validate the three forecast-only pseudo-regimes, what they would cost, and what must be decided first. The coverage row `REGIME-INDEPENDENT-VALIDATION` stays **PLANNED**.

## 1. What needs validating, and why it is different from what exists

Today's "accuracy" for the regime classifier (about 0.94 on 2018, 0.88 out-of-fold on 2023) is **agreement with the project's own forecast-only labelling rule**, not meteorological
accuracy (`docs/55`, `docs/56`). Independent validation means comparing the classes with a source that is physically defined and does not use the project's rule. Such labels would be used
for **evaluation only**: never to retrain, retune or relabel, and 2019 and 2025 results would carry their post-hoc labels.

## 2. Candidate sources

| Regime | Independent source | What it is | Covers the project's years? | Status of access |
|---|---|---|---|---|
| Active monsoon, break monsoon | **Objective rainfall criteria of Rajeevan, Gadgil and Bhate (2010)**: the normalised rainfall anomaly averaged over the monsoon core zone (about 18–28° N, 65–88° E) above +1 (active) or below −1 (break) for at least three consecutive days, defined for the peak months of July and August ([source](https://repository.ias.ac.in/15911); criteria read from search summaries, to be checked in the paper) | Observation-based, published, reproducible | Yes: the IMD annual rainfall files for 2017, 2018, 2019, 2023, 2024 and 2025 are already on this machine and span 6.5–38.5° N, 66.5–100° E | Data in hand; **needs a multi-decade daily climatology** (see section 3) |
| Active, break | IITM real-time active and break classification page ([ERPAS](https://www.tropmet.res.in/erpas/files/active_break_selection.php)) | A maintained operational classification | Unverified | Unverified; format, history and terms unknown |
| Monsoon low or depression | **IMD RSMC New Delhi best-track records** for depressions and deep depressions (post-season analysis of position and intensity); an open-source parser, [imdtrack](https://imdtrack.readthedocs.io/), republishes them | Operational meteorological record | Years, disturbance classes and terms of use are **not stated** in the package documentation; unverified | Needs a small download after the source terms are checked |
| Monsoon low or depression | Objective low-pressure-system tracking of 850-hPa vorticity (Hurley and Boos 2015, [source](https://boos.berkeley.edu/publication/hurley2015)) | Reproducible method, ERA-Interim 1979–2012 | **No** (ends 2012). Applying the method to a newer reanalysis (ERA5) is a new acquisition and implementation | Not available as data for these years |
| Coastal or orographic | None | These zones are static geography (`docs/115`); there is no event to validate | n/a | n/a |
| All regimes | Expert review (for example NCMRWF forecasters) | Highest authority, small sample | n/a | Outside the repository; needs an owner contact |

## 3. Obstacles that must be stated

1. **Climatology.** The active and break criteria are standardised anomalies against a daily climatology. The published work used decades of data; this project holds six seasons. A climatology
   built from six seasons would be too short to call the result the published classification. A longer record (IMD publishes annual 0.25° files back to 1901) would be a new download of
   many files from IMD Pune, whose page carries no general redistribution permission (`docs/80`), so the terms need confirming before any large download.
2. **Class mismatch.** The project's "Break / Weak" class merges break with weak monsoon, and the published criteria define only active and break, not weak or neutral. A confusion matrix
   would therefore validate "active versus not active" and "break versus not break" and could not score the weak part of the class or a neutral state.
3. **Season mismatch.** The published criteria are defined for July and August; the project corpus is June to September. June and September days would be unlabelled.
4. **Geometry.** The core zone (north of 18° N, up to 28° N) lies mostly outside the 10–22° N rainfall verification domain; labels computed from the full IMD file are unaffected, and the
   forecast atmospheric context (5–30° N) does cover it. The IMD grid starts at 66.5° E, slightly east of the zone's 65° E edge, a small documented deviation.
5. **Support is unknown.** Without computing the labels it is impossible to say how many active, break and depression days exist in 2023–2025, and the existing support gate (at least 30
   cases and 30 events) may not be met for the depression class. A counting step must precede any protocol.

## 4. Recommended path (each step stops for approval)

| Step | Work | Needs |
|---|---|---|
| V0 | Owner decisions in section 5 | your choices; any download |
| V1 | Compute the active and break flags per day from the IMD files already held, using the agreed climatology; compute a depression indicator from the agreed track source; store with full provenance, evaluation-only | the climatology source; the track source |
| V2 | Count days and cases per class and year against the support gate; stop if too few | nothing |
| V3 | Report agreement of the frozen classifier with these labels: balanced accuracy, macro-F1, per-class precision and recall, confusion matrix and support, kept **separate** from the pseudo-label agreement figures, with the post-hoc label on 2019 and 2025 | a frozen protocol written first |
| V4 | Show the result in the compliance page and the regime page as a separate, labelled panel | none beyond V3 |

## 5. Decisions needed from the project owner

1. Climatology for the active and break criteria: download the long IMD record after confirming terms, accept a short in-sample climatology and label the result "provisional, not the published classification", or skip active and break validation.
2. Depression labels: approve checking the IMD best-track terms and then downloading that small record, or choose another source.
3. Is a partial validation acceptable (active versus not active, break versus not break, depression versus not), given the class mismatch?
4. Whether to seek expert review outside the repository.

Gate: `P1_7B_SOURCE_PROBE_DOCUMENTED_AWAITING_OWNER_DECISIONS`.
