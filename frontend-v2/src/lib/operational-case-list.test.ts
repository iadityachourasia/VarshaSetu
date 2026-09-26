import { afterEach, describe, expect, it, vi } from "vitest";
import { caseDisplayLabel, loadOperationalCaseList, type CaseListItem } from "./operational-case-list";

afterEach(() => vi.unstubAllGlobals());

const baseItem: CaseListItem = {
  case_id: "20250718_day2_24h", year: 2025, initialization_utc: "2025-07-18T00:00:00Z",
  lead_hours: 48, lead_label: "Day 2", valid_date: "2025-07-20", year_role: "FINAL_TEST_COMPLETED",
  month: 7, event_heavy: false, event_very_heavy: false, pseudo_regime_class: "ACTIVE_MONSOON",
  deterministic_source_eligible: true, probability_source_eligible: true, regime_source_eligible: true,
  ensemble_source_eligible: false, full_5_member_rainfall_qc_pass: false,
  m1_minus_raw_rmse_mm: -0.4, selected_model_improved_vs_raw: true,
};

describe("caseDisplayLabel", () => {
  it("shows date and lead without exposing the raw case_id as the primary label", () => {
    const label = caseDisplayLabel(baseItem);
    expect(label).toBe("18 Jul 2025 · Day 2");
    expect(label).not.toContain("20250718");
  });

  it("marks a very-heavy event over a heavy event when both are somehow set", () => {
    const label = caseDisplayLabel({ ...baseItem, event_heavy: true, event_very_heavy: true });
    expect(label).toContain("Very Heavy event");
  });

  it("marks a heavy event when only that flag is set", () => {
    const label = caseDisplayLabel({ ...baseItem, event_heavy: true });
    expect(label).toContain("Heavy event");
    expect(label).not.toContain("Very Heavy event");
  });

  it("adds no event marker when neither flag is set", () => {
    const label = caseDisplayLabel(baseItem);
    expect(label).not.toContain("event");
  });
});

describe("loadOperationalCaseList", () => {
  it("uses the live case-index endpoint as primary source", async () => {
    const payload = {
      year: 2025, total: 1, page: 1, page_size: 400,
      cases: [{
        case_id: "20250718_day2_24h", year: 2025, initialization_utc: "2025-07-18T00:00:00Z", lead_hours: 48,
        product: "day2_24h", year_role: "FINAL_TEST_COMPLETED", source_complete: true,
        deterministic_source_eligible: true, probability_source_eligible: true, regime_source_eligible: true,
        ensemble_source_eligible: false, c00_rainfall_qc_pass: true, full_5_member_rainfall_qc_pass: false,
        m1_rmse_mm: 5.1, raw_rmse_mm: 5.5, m1_minus_raw_rmse_mm: -0.4,
        initialization_date: "2025-07-18", month: 7, lead_label: "Day 2", valid_date: "2025-07-20",
        event_heavy: true, event_very_heavy: false, pseudo_regime_class: "ACTIVE_MONSOON",
        selected_model_improved_vs_raw: true,
      }],
    };
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => payload })));
    const result = await loadOperationalCaseList(2025);
    expect(result.mode).toBe("VERIFIED_API");
    expect(result.data).toHaveLength(1);
    expect(result.data?.[0].event_heavy).toBe(true);
  });

  it("never falls back on an integrity failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false, status: 503,
      json: async () => ({ code: "SCIENCE_INTEGRITY_FAILURE", detail: "hash mismatch" }),
    })));
    const result = await loadOperationalCaseList(2025);
    expect(result.mode).toBe("INTEGRITY_FAILURE");
    expect(result.data).toBeNull();
  });
});
