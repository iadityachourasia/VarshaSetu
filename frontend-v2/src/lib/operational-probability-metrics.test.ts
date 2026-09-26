import { describe, expect, it } from "vitest";
import { extractProbabilityEventMetrics } from "./operational-probability-metrics";

const flatHeavy = {
  brier: 0.0198313,
  bss: 0.09483,
  pr_auc: 0.21736,
  roc_auc: 0.89455,
  observed_event_count: 6760,
  categorical: { decision_threshold_probability: 0.1, metrics: { POD: 0.27796, FAR: 0.69576, CSI: 0.16994, ETS: 0.15942 } },
  reliability: [{ bin_lower: 0, bin_upper: 0.1, mean_predicted_probability: 0.01, observed_event_frequency: 0.02, sample_count: 100 }],
};

describe("extractProbabilityEventMetrics", () => {
  it("reads a flat per-event shape (2024-style) directly", () => {
    const metrics = extractProbabilityEventMetrics({ heavy: flatHeavy, very_heavy: flatHeavy }, "heavy");
    expect(metrics?.brier).toBeCloseTo(0.0198313, 6);
    expect(metrics?.categorical.metrics.POD).toBeCloseTo(0.27796, 5);
  });

  it("unwraps a nested `.metrics` per-event shape (2025-manifest-style)", () => {
    const nested = { paired_cases: 232, metrics: flatHeavy };
    const metrics = extractProbabilityEventMetrics({ heavy: nested, very_heavy: nested }, "heavy");
    expect(metrics?.brier).toBeCloseTo(0.0198313, 6);
    expect(metrics?.reliability[0].sample_count).toBe(100);
  });

  it("returns undefined when the event key is absent", () => {
    expect(extractProbabilityEventMetrics({ heavy: flatHeavy }, "very_heavy")).toBeUndefined();
  });

  it("returns undefined for a missing metrics object", () => {
    expect(extractProbabilityEventMetrics(undefined, "heavy")).toBeUndefined();
  });
});
