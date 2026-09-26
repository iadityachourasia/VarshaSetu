// Phase 5A.3, section 36: the full multi-year Track-B holdout lifecycle, as
// a simple, visually clear step timeline. Distinct from the single-moment
// "final-test governance" flow already on /audit (SEALED -> AUTHORIZED ->
// UNSEALED ONCE -> FINAL TEST COMPLETED, the unsealing act itself); this is
// the years-long governance chain around it.
const STEPS = [
  { label: "2023", detail: "TRAIN / CROSS-FIT" },
  { label: "2024", detail: "VALIDATE / SELECT / CALIBRATE" },
  { label: "FREEZE", detail: "Model, calibration and thresholds frozen before 2025" },
  { label: "2025", detail: "ONE-TIME FINAL TEST" },
  { label: "CONSUMED", detail: "Holdout unsealed once; no post-test revision" },
] as const;

export function HoldoutGovernanceTimeline() {
  return <ol className="phase5-holdout-timeline" aria-label="Track-B holdout governance lifecycle">
    {STEPS.map((step, index) => <li key={step.label}>
      <strong>{step.label}</strong><span>{step.detail}</span>
      {index < STEPS.length - 1 ? <span className="phase5-holdout-arrow" aria-hidden="true">→</span> : null}
    </li>)}
  </ol>;
}
