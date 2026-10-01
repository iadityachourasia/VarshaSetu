# Phase 4L — Scientific Communication Alignment

## 1. Executive Summary

This phase aligns current documentation, demo narration, and `frontend-v2` copy with the completed independent Phase 4K audit. The two historical experiments are now visibly separate. Interactive maps remain frozen 2019 GEFSv12 reforecast artifacts; the completed 2025 operational-era result is a non-interactive, hash-pinned report summary. No scientific result, model, calibrator, threshold, observation, QC rule, dataset, or API numerical response was changed. Decision: **`PRESENTATION_READY_WITH_MINOR_NOTES`**, subject to the external map-tile availability note in §17.

## 2. Phase 4K Audit Basis

Phase 4K decided `AUDIT_PASSED_WITH_DOCUMENTATION_CORRECTIONS`. Its [audit manifest](../experiments/recent_historical/phase4k_independent_final_audit_v1/artifact_manifest.json) has SHA-256 `074975ebeafa3d4c11a89fb45f0661dfd6e28dd973a500b0c73914ba7344c24f`. The [claim audit](../experiments/recent_historical/phase4k_independent_final_audit_v1/claim_audit.json), [documentation ledger](../experiments/recent_historical/phase4k_independent_final_audit_v1/documentation_discrepancy_ledger.json), and [frontend audit](../experiments/recent_historical/phase4k_independent_final_audit_v1/frontend_claim_audit.json) governed each wording change. The [Phase 4L resolution ledger](../experiments/recent_historical/phase4l_communication_alignment_v1/documentation_correction_ledger.json) addresses every Phase 4K documentation entry, including its misnamed `docs/78` filename.

## 3. Scientific Freeze

Only copy, presentation metadata, tests, and this new documentation/artifact set changed. Phase 2/4A–4K model, data, prediction, metric, selection, calibration, threshold, QC, feature, source, manifest, and API files remain protected. The 2025 holdout is consumed; neither test was reopened for tuning. The 2025 UI metadata is pinned to `FINAL_TEST_RESULT.json` SHA-256 `04a7fc2a434d24449365e2cb9978cbc8584f5cc87ea4f132cfaf6e7fc7a4abca`, and a frontend unit test compares every displayed value with that file.

## 4. Canonical Experiment Definitions

| Track | Source and truth | Development | Final evaluation | Current display |
|---|---|---|---|---|
| A, retrospective | NOAA GEFSv12 **reforecast** + IMD | 2017 train; 2018 validate/calibrate | Completed 2019; 255 cases | Interactive 2019 historical maps and verification |
| B, operational era | Historical NOAA **operational GEFS** + IMD | 2023 train/cross-fit; 2024 validate/calibrate/select | Completed and consumed 2025; 232 cases, 301,832 paired cells | Separate non-interactive frozen-report summary |

The tracks have different GEFS lineages, populations, and preselected models. No pooled score or combined percentage is presented.

## 5. Canonical 2019 Claims

On the completed frozen 2019 GEFSv12 reforecast final test, M2 Global XGBoost reduced common-population RMSE from **19.7735 to 17.8487 mm**, or **9.73%**, across **255 cases**. It had the best deterministic RMSE in that retrospective ladder. These figures are API-derived on Overview/Verification and do not imply improvement on every extreme-event metric or every case. The historical 2019 probability and district maps retain their source and limitations.

## 6. Canonical 2025 Claims

On the one-time completed 2025 historical operational-era final test, **M1 Ridge MOS**, selected by 2024 validation before outcome access, reduced RMSE from **16.1657 to 15.5736 mm**, or **3.6631%**, across **232 cases / 301,832 paired cells**. M2's **15.0022 mm** is a predeclared *secondary* 2025 comparator; it does not replace M1 as the primary headline. This is not live forecast issuance or operational deployment.

## 7. Extreme-Rain Limitations

The 2025 M1 continuous-RMSE improvement coexists with **Raw GEFS better heavy and very-heavy spatial FSS** at all frozen 1×1, 3×3, 5×5, and 9×9 scales, and lower selected-M1 heavy/very-heavy CSI/ETS than Raw. Verification now makes the spatial caveat visible next to the separate 2025 summary rather than hiding it in a tooltip. Heavy and very-heavy thresholds are inclusive **≥64.5** and **≥115.6 mm per 24 h**; the 2019 Extreme Rain page continues to show its own frozen threshold results, not 2025 scores.

Scope addendum (Phases 4M and 6A, `docs/106`, `docs/108`): every "Raw has better FSS" claim must name its track. Track A (2018 and 2019): Raw beats **all four** corrected models M1-M4 at every scale and threshold (`docs/108`). Track B 2025: the frozen statement concerns the **selected M1** only (`docs/89`), not M3/M4. Post-hoc diagnostics show regime-aware heavy-rain CSI/FSS above Raw in the Low/Depression pseudo-regime on **Track B only** (2024, 2025); that pattern does **not** replicate on Track A. So "corrected models lose on extremes", "regime awareness improves extreme skill" and "regime awareness never helps" are all forbidden unqualified generalisations. Existing UI copy already scopes the statement to the selected M1 and needs no change.

## 8. Probability Claims

Both frozen 2025 calibrated probability models achieved positive Brier Skill Score against the frozen 2023-prevalence reference: heavy **+0.09483**, very heavy **+0.02652**. At frozen decision thresholds 0.10/0.05, FAR remained **0.69576/0.85492**. PR-AUC weakened from 2024 to 2025, and upper reliability bins were sparse. “Calibrated” identifies the fitted 2024 method; it does not mean 2025 probabilities were perfectly reliable. The interactive probability map remains the separate 2019 model, calibrated on 2018, and is explicitly not a live warning.

## 9. Regime Terminology

The UI and claim registry use **forecast-only pseudo-regime**, **deterministic pseudo-label**, or **regime classifier output**. The 2023 out-of-fold balanced agreement **0.8806** is agreement with forecast-only pseudo-labels, not independent meteorological accuracy. In both benchmark narratives, global/non-regime ML retains the appropriate comparator; hard/soft routing is not advertised as an overall winner.

## 10. Holdout Terminology

Current UI and demo instructions say **completed 2019 held-out evaluation** and **consumed 2025 one-time final test**. They no longer call either evaluated period presently untouched. Older Phase 4D–4I sealed-state records remain truthful dated snapshots of their pre-unseal phase, not current-status pages. The current status is in `89_OPERATIONAL_FINAL_TEST_2025.md` and `90_INDEPENDENT_FINAL_SCIENTIFIC_AUDIT.md`.

## 11. Packing/QC Terminology

An append-only interpretation note in `81_SEVEN_DAY_OPERATIONAL_EVALUATION_2024.md` distinguishes that report's historical 0.055-mm calculation from the canonical **per-source-message packing-quantum-derived** tolerance. The Phase 4C audit documents encountered tolerances including **0.01, 0.055, and 0.1 mm**. The original seven-day QC counts and conclusions were not rewritten.

## 12. Rainfall-Window Terminology

`AGENTS.md` now identifies 6-hour rainfall as the quarantined legacy CSV target, while active Phase 1F–4J experiments use **24-hour accumulations**. The operational-era Day 1/2/3 forecast windows are **+3→+27 h**, **+27→+51 h**, and **+51→+75 h**. The old template in `docs/21` remains for history but carries an explicit warning not to apply it to frozen modern corpora. No accumulation or threshold semantics changed.

## 13. Frontend Corrections

Overview scopes its 9.73% hero to the 2019 retrospective reforecast and 255 cases. Forecast Explorer says 2019 historical/non-live. Extreme Rain identifies 2019 probabilities and their 2018 calibration; District Intelligence identifies historical analysis, not advisories. Verification separates 2019 API-backed charts from a 2025 non-interactive report summary, names preselected M1 and secondary M2, and displays Raw-better FSS. Methodology now shows both independent temporal tracks. The global shell clarifies 2019 maps versus separate 2025 benchmark. Map values, interactions, legends, and API requests were preserved.

## 14. Documentation Corrections

`README.md` now distinguishes blocked legacy CSV routes from read-only frozen 2019 science and the separate completed 2025 benchmark. `docs/72`, `76`, `77`, and the actual `78_SIH_RECORDING_SHOT_LIST.md` now bound the interactive demo to 2019 and allow only a separately sourced 2025 report/slide. `docs/00_INDEX.md` replaces its obsolete future-unseal instruction and adds docs/90–91. `docs/81` has a Phase 4C packing interpretation; `docs/21` has a legacy-target qualifier. All nine Phase 4K documentation ledger entries have explicit `FIXED` resolutions in the machine-readable Phase 4L ledger. Historic pre-Phase 4J records themselves remain unchanged.

## 15. Claim Registry

The [canonical registry](../experiments/recent_historical/phase4l_communication_alignment_v1/canonical_claim_registry.json) provides four reusable supported claims, five classes requiring precise qualification, and five prohibited overclaims. Presentation authors should copy the experiment, year, source lineage, model, metric, and denominator together. The [benchmark summary](../experiments/recent_historical/phase4l_communication_alignment_v1/benchmark_summary.json) contains separate machine-readable tracks; [demo claims](../experiments/recent_historical/phase4l_communication_alignment_v1/demo_claims.json) constrain narration and imagery.

## 16. Remaining Historical Discrepancies

Past Phase 4D–4I documents and manifests appropriately retain their then-sealed 2025 state; changing them would falsify sequence evidence. The historical `docs/21` template still contains its quoted legacy “current 6-hour” prompt inside the example, but the immediately preceding explicit qualifier prevents current use. Phase 4K's `docs/78_SIH_VIDEO_SHOT_LIST.md` path was a ledger typo; the real `docs/78_SIH_RECORDING_SHOT_LIST.md` is annotated. These are **historical/contextual**, not unresolved current public claims.

## 17. Verification

Frontend TypeScript, ESLint, Vitest, and Next.js production build passed. The focused Playwright production demo path, accessibility/responsive sweep and six-page screenshot run passed; the full Playwright suite passed **10/11**. Its sole failure was the external online vector-tile availability assertion: this environment received no HTTP 200 `.pbf` tiles from the provider within 25 seconds. The explicitly labeled offline geography fallback, local scientific layers, district interaction, and map readability passed. This is an external service/recording preflight note, not evidence of scientific-data or copy failure. The affected Overview, Forecast Explorer, Extreme Rain, Verification, and Methodology screenshots were inspected at recording/laptop resolutions. Recheck online tile availability immediately before video capture; retain visible offline attribution if unavailable.

## 18. Presentation Guidance

Lead with the 2019 reforecast UI as a historical visual demonstration. On a separate Verification/report screen, state the 2025 preselected M1 RMSE result and immediately show the opposing Raw-better extreme FSS conclusion. Mention positive probability BSS together with high FAR and reliability limits. Do not point to a 2019 case map while narrating a 2025 score. Do not call the app live, operationally proven, or an official forecast replacement. The corrected storyboard and optional narration line are source-scoped, and extra video time must be allocated if the 2025 segment is used.

## 19. Artifact Integrity

The protected Phase 4J result SHA-256 is `04a7fc2a434d24449365e2cb9978cbc8584f5cc87ea4f132cfaf6e7fc7a4abca`; Phase 4I readiness is `67170a350abb0663aedb2ea129d4eac3ce10ce9d77863af43b4f5c22700b2b48`; Phase 4H protocol is `cfe273d765ae943ea0dc394439436af09391a4c25e3684629732394801582770`; Phase 4G feature freeze is `f1520a32aadef460249ba26a39c106f9593fcd3407c23d2967ddc90d889ed67b`. The Phase 4K audit manifest remains `074975ebeafa3d4c11a89fb45f0661dfd6e28dd973a500b0c73914ba7344c24f`. The [Phase 4L artifact manifest](../experiments/recent_historical/phase4l_communication_alignment_v1/artifact_manifest.json) hashes the new communication outputs; it does not alter protected lineage.

## 20. Decision Gate

**`PRESENTATION_READY_WITH_MINOR_NOTES`**. Material Phase 4K current-copy discrepancies are corrected, the two studies remain distinct, and the frozen scientific evidence is unchanged. The remaining note is to verify external vector-tile connectivity before recording; the labeled offline fallback is scientifically safe if tiles are unavailable. No model work, API change, or deployment is authorized by this decision.
