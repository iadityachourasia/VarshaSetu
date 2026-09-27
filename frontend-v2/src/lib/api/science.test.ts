import { afterEach, describe, expect, it, vi } from "vitest";
import { getScience, rainfallSchema, statusSchema } from "./science";

afterEach(() => vi.unstubAllGlobals());

describe("read-only science API contract", () => {
  it("validates response shape and never invents a missing metric", async () => {
    const status = { readiness_state: "prototype_scientific_ready", operational_ready: false, case_count: 255, district_count: 188,
      provenance: { corpus_version: "v2", deterministic_model: "M2", deterministic_model_sha256: "x", probability_freeze_sha256: "y", artifact_manifest_sha256: "z", prototype_only: true } };
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => status })));
    await expect(getScience("/status", statusSchema)).resolves.toEqual(status);
    expect(fetch).toHaveBeenCalledWith("/api/science/status", { cache: "default", signal: expect.any(AbortSignal) });
    expect(statusSchema.safeParse({ ...status, case_count: "255" }).success).toBe(false);
  });
  it("requires spatial grid metadata and paired mask for rainfall maps", () => {
    const payload = { case_id: "case", initialization_utc: "2019-01-01", lead_hours: 24, product: "day1",
      valid_period_start_utc: "2019-01-02", valid_period_end_utc: "2019-01-03",
      provenance: { corpus_version: "v2", deterministic_model: "M2", deterministic_model_sha256: "x", probability_freeze_sha256: "y", artifact_manifest_sha256: "z", prototype_only: true },
      data: { raw: [[1]], corrected: [[2]], observed: [[3]], valid_mask: [[true]], unit: "mm/24h" } };
    expect(rainfallSchema.safeParse(payload).success).toBe(false);
  });
  it("surfaces unavailable artifacts as errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 503 })));
    await expect(getScience("/status", statusSchema)).rejects.toThrow("Scientific artifacts are unavailable");
  });
});
