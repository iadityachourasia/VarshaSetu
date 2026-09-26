// `/api/science/operational/{year}/metrics/probability` serves the frozen
// artifact for each year with a genuinely different nesting: 2025's
// `metrics/probability.json` wraps the scalar fields one level deeper under
// a `.metrics` key; 2024's `validation/probability_{heavy,very_heavy}_2024.json`
// wraps them under `.full_2024_descriptive_metrics` (verified directly
// against the real live backend -- the object at the un-nested level is a
// truthy but scalar-metric-free bag of calibration/candidate-model metadata,
// which previously made this helper silently return the wrong object rather
// than "unavailable"). This helper checks both known nesting keys before
// falling back to the record itself.
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
  const nested = record.metrics ?? record.full_2024_descriptive_metrics;
  const unwrapped = nested && typeof nested === "object" ? nested : record;
  if (typeof (unwrapped as { pr_auc?: unknown }).pr_auc !== "number") return undefined;
  return unwrapped as ProbabilityEventMetrics;
}
