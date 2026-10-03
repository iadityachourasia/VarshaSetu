import { describe, expect, it } from "vitest";
import { liveCycleSchema, liveFieldSchema, liveStatusSchema } from "./live";

const summary = (kind: "live" | "replay") => ({
  kind, cycle: "20250926", initialization: "2025-09-26T00:00:00Z", label: kind === "live" ? "EXPERIMENTAL FORECAST: frozen models, no verification yet, not an official warning" : "HISTORICAL REPLAY of a stored cycle through the live code path: a pipeline proof, not a forecast",
  created_at_utc: "2026-10-03T00:00:00+00:00", age_days: 5, stale: kind === "live", products: ["day1_24h"], withheld_products: { day2_24h: "canonical rainfall reconstruction failed (x)" },
});
const grid = () => Array.from({ length: 49 }, () => Array.from({ length: 49 }, () => 1.5));
const cycle = (extra: Record<string, unknown> = {}) => ({
  summary: summary("replay"), manifest_sha256: "a".repeat(64), messages: 34, transferred_bytes: 8_675_564, frozen_models: { M1: "b".repeat(64) },
  applicability: { status: "WITHIN_TRAINING_RANGE", largest_share: { share: 0.04, product: "day1_24h", feature: "forecast_v850" } },
  replay_comparison: { date: "20250926", products: { day1_24h: { paired_cells: 1301, M1_max_abs_difference: 0 } } },
  regime_probabilities: { day1_24h: { ACTIVE_MONSOON: 0.2, BREAK_WEAK_MONSOON: 0.3, LOW_DEPRESSION_INFLUENCED: 0.5 } },
  domain_statistics: { day1_24h: { M1: { min: 0, max: 9, mean: 2 } } }, fields: { M1: "M1 linear MOS (frozen)" }, observation_read: false, caveats: ["x"], ...extra,
});

describe("experimental live cycle client schemas", () => {
  it("accepts an empty status and a status with a replay or a live cycle", () => {
    expect(liveStatusSchema.parse({ has_live_cycle: false, latest_live: null, cycles: [], message: "No experimental cycle has been published.", caveats: ["x"] }).cycles).toHaveLength(0);
    const both = liveStatusSchema.parse({ has_live_cycle: true, latest_live: summary("live"), cycles: [summary("live"), summary("replay")], message: "m", caveats: [] });
    expect(both.cycles.map((c) => c.kind)).toEqual(["live", "replay"]);
  });

  it("rejects an unknown kind and a malformed cycle date", () => {
    expect(() => liveStatusSchema.parse({ has_live_cycle: false, latest_live: null, cycles: [{ ...summary("live"), kind: "forecast" }], message: "m", caveats: [] })).toThrow();
    expect(() => liveStatusSchema.parse({ has_live_cycle: false, latest_live: null, cycles: [{ ...summary("live"), cycle: "2025-09-26" }], message: "m", caveats: [] })).toThrow();
  });

  it("accepts a cycle and refuses one that claims an observation was read", () => {
    expect(liveCycleSchema.parse(cycle()).messages).toBe(34);
    expect(() => liveCycleSchema.parse(cycle({ observation_read: true }))).toThrow();
  });

  it("accepts a 49 by 49 field and rejects any other shape", () => {
    const base = { kind: "replay", cycle: "20250926", product: "day1_24h", field: "M1", label: "M1", evidence_label: "e", units: "mm per 24 h", latitude: Array(49).fill(10), longitude: Array(49).fill(68), values: grid(), array_sha256: "c".repeat(64) };
    expect(liveFieldSchema.parse(base).values).toHaveLength(49);
    expect(() => liveFieldSchema.parse({ ...base, values: grid().slice(1) })).toThrow();
    expect(() => liveFieldSchema.parse({ ...base, values: grid().map((r) => r.slice(1)) })).toThrow();
  });
});
