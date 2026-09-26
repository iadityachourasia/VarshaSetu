// Phase 5A.2D: `/api/science/operational/{year}/metrics/probability` serves
// the frozen `metrics/probability.json` artifact "verbatim" for 2025 and an
// assembled {heavy, very_heavy} object built from two flat frozen files for
// 2024 (see docs/92 section 15-16 and backend/app/api/operational.py's
// metrics_probability). The 2024 files are known-flat (brier/bss/pr_auc/... at
// the top level, confirmed from public/science/operational-v1/
// probability_validation_2024.json, which is generated from the same
// artifacts). The 2025 presentation manifest wraps the identical fields one
// level deeper under a `.metrics` key. This repository's checked-in tree does
// not contain the raw `experiments/` corpus, so the exact top-level shape of
// the live 2025 `metrics/probability.json` file itself has not been directly
// inspected here -- this helper tolerates either shape rather than assuming
// one, so a real shape difference is never silently misread as "unavailable".
export type ProbabilityCategorical = {
  decision_threshold_probability: number;
  metrics: { POD: number; FAR: number; CSI: number; ETS: number };
};
export type ProbabilityReliabilityBin = {
  bin_lower: number;
  bin_upper: number;
  mean_predicted_probability: number | null;
  observed_event_frequency: number | null;
  sample_count: number;
};
export type ProbabilityEventMetrics = {
  brier: number;
  bss: number;
  pr_auc: number;
  roc_auc: number;
  observed_event_count: number;
  categorical: ProbabilityCategorical;
  reliability: ProbabilityReliabilityBin[];
};

export function extractProbabilityEventMetrics(
  metrics: Record<string, unknown> | undefined,
  event: "heavy" | "very_heavy",
): ProbabilityEventMetrics | undefined {
  const raw = metrics?.[event];
  if (!raw || typeof raw !== "object") return undefined;
  const record = raw as Record<string, unknown>;
  const unwrapped = record.metrics && typeof record.metrics === "object" ? record.metrics : record;
  return unwrapped as ProbabilityEventMetrics;
}
