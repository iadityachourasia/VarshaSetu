// Phase 5A.3, section 38: one canonical known-limitations list, reused
// wherever this project needs to keep it prominently visible rather than
// each page re-typing (and risking drifting) its own subset.
export const KNOWN_LIMITATIONS: string[] = [
  "Historical research prototype; not a live forecast system or an official warning service.",
  "Raw GEFS retained better selected-model extreme-rain FSS at every tested Heavy and Very Heavy neighborhood size.",
  "Very-heavy calibrated probability had a high false-alarm ratio on the 2025 final test.",
  "Regime classes are forecast-derived pseudo-regimes, not independently observed meteorological truth.",
  "Track-B (2023-2025) district-level rainfall aggregates are not available in the frozen corpus.",
  "PR/ROC curve point arrays are not available anywhere in the audited corpus; only the scalar PR-AUC/ROC-AUC values are shown.",
  "Source-QC attrition reduces the operationally eligible population below the scheduled case count.",
  "IMD annual daily date labels do not explicitly encode accumulation bounds.",
  "2019 reforecast and 2025 operational-era benchmarks have different GEFS lineages and cannot be pooled.",
  "Six evaluated monsoon seasons are descriptive context, not a climatological trend analysis.",
];

export function LimitationsPanel() {
  return <ul className="phase5-limitations">{KNOWN_LIMITATIONS.map((item) => <li key={item}>{item}</li>)}</ul>;
}
