import { afterEach, describe, expect, it, vi } from "vitest";
import {
  OperationalApiError,
  getOperationalAtmosphere,
  getOperationalAvailability,
  getOperationalCases,
  getOperationalDistricts,
  getOperationalDistrictsCompare,
  getOperationalDistrictHistory,
  getOperationalEnsemble,
  getOperationalFSS,
  getOperationalProbability,
  getOperationalProvenance,
  getOperationalQuality,
  getOperationalRainfall,
  getOperationalRegime,
  getOperationalStatus,
  operationalGridFieldSchema,
  operationalAtmosphericFieldSchema,
} from "./operational";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

const okJson = (body: unknown) => vi.fn(async () => ({ ok: true, json: async () => body }));

describe("operational status/availability parsing", () => {
  it("classifies an aborted request as a network failure eligible for the existing fallback", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new DOMException("Request timed out", "TimeoutError"); }));
    await expect(getOperationalStatus()).rejects.toMatchObject({ kind: "NETWORK_FAILURE" });
  });

  it("times out a stalled client request and preserves network-failure classification", async () => {
    const nativeTimeout = AbortSignal.timeout.bind(AbortSignal);
    const timeout = vi.spyOn(AbortSignal, "timeout").mockImplementation(() => nativeTimeout(5));
    vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal!.addEventListener("abort", () => reject(init.signal!.reason));
    })));
    await expect(getOperationalStatus()).rejects.toMatchObject({ kind: "NETWORK_FAILURE" });
    expect(timeout).toHaveBeenCalledWith(20_000);
  });

  it("classifies an aborted response body as a network failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => { throw new DOMException("signal timed out", "TimeoutError"); },
    })));
    await expect(getOperationalStatus()).rejects.toMatchObject({ kind: "NETWORK_FAILURE" });
  });

  it("parses status and hits the operational path under /api/science", async () => {
    const status = {
      experiment: "operational_gefs_2023_2025", label: "Historical Operational GEFS (Track B)",
      forecast_source: "NOAA operational GEFS (historical archive)", observation_source: "IMD 0.25 degree gridded rainfall",
      years: { "2023": "TRAIN_CROSSFIT", "2024": "VALIDATION_SELECTION", "2025": "FINAL_TEST_COMPLETED" },
      api_version: "phase5a.1", integrity_model: "hash-verified where a frozen manifest+digest exists",
    };
    vi.stubGlobal("fetch", okJson(status));
    await expect(getOperationalStatus()).resolves.toEqual(status);
    expect(fetch).toHaveBeenCalledWith("/api/science/operational/status", { cache: "default", signal: expect.any(AbortSignal) });
  });

  it("parses year capability responses and preserves unavailable/false literals", async () => {
    const availability = {
      year: 2023, role: "TRAIN_CROSSFIT", role_label: "Training / cross-fit year",
      raw_rainfall: true, imd_observation: true,
      m1: "unavailable", m2: "out_of_fold_case_grid", m3: "unavailable", m4: "unavailable",
      heavy_probability: "unavailable", very_heavy_probability: "unavailable",
      regime_probability: "per_case", atmosphere_fields: true, ensemble_members: "eligible_subset_only",
      case_level_metrics: false, per_cell_metrics: false, fss: false, reliability_bins: false,
      pr_roc_curve_arrays: "unavailable", district_aggregates: false, notes: ["2023 is train/cross-fit only"],
    };
    vi.stubGlobal("fetch", okJson(availability));
    const parsed = await getOperationalAvailability(2023);
    expect(parsed.m2).toBe("out_of_fold_case_grid");
    expect(parsed.district_aggregates).toBe(false);
    expect(parsed.pr_roc_curve_arrays).toBe("unavailable");
  });

  it("accepts district_aggregates=true (2024/2025 district product) but rejects a non-boolean value", async () => {
    const payload = {
      year: 2025, role: "FINAL_TEST_COMPLETED", role_label: "x", raw_rainfall: true, imd_observation: true,
      m1: "case_grid", m2: "case_grid", m3: "case_grid", m4: "case_grid",
      heavy_probability: "case_grid", very_heavy_probability: "case_grid", regime_probability: "per_case",
      atmosphere_fields: true, ensemble_members: "eligible_subset_only", case_level_metrics: true,
      per_cell_metrics: true, fss: true, reliability_bins: true, pr_roc_curve_arrays: "unavailable",
      district_aggregates: true, notes: [],
    };
    vi.stubGlobal("fetch", okJson(payload));
    expect((await getOperationalAvailability(2025)).district_aggregates).toBe(true);
    vi.stubGlobal("fetch", okJson({ ...payload, district_aggregates: "yes" }));
    await expect(getOperationalAvailability(2025)).rejects.toThrow();
  });
});

describe("district product parsing", () => {
  const row = {
    district_id: "D1", district_name: "Raigarh", valid_grid_cells: 21, raw_mean_mm: 14.3, raw_max_mm: 30,
    corrected_mean_mm: 13.3, corrected_max_mm: 28, heavy_probability: 0.006, very_heavy_probability: null,
    heavy_area_fraction: 0, very_heavy_area_fraction: 0, observed_mean_mm: 100.1, observed_max_mm: 150,
    observed_heavy_area_fraction: 0.9, observed_very_heavy_area_fraction: 0.2,
  };
  const body = {
    case_id: "20250714_day2_24h", year: 2025, year_role: "FINAL_TEST_COMPLETED", model: "m1", model_role: "Ridge MOS",
    units: "mm/24h", heavy_threshold_mm: 64.5, very_heavy_threshold_mm: 115.6, predicted_regime: "ACTIVE_MONSOON",
    districts: [row], source_district_count: 188, method: "x", weights_sha256: "a".repeat(64),
    geometry_sha256: "b".repeat(64), geometry_source: "geoBoundaries IND ADM2 2021", geometry_license: "ODbL 1.0", caveats: ["c"],
  };

  it("requests the year/case/model route and keeps nullable probabilities null", async () => {
    const fetchMock = okJson(body);
    vi.stubGlobal("fetch", fetchMock);
    const parsed = await getOperationalDistricts(2025, "20250714_day2_24h", "m3");
    expect(String((fetchMock as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0])).toContain("/operational/2025/cases/20250714_day2_24h/districts?model=m3");
    expect(parsed.districts[0].very_heavy_probability).toBeNull();
    expect(parsed.districts[0].observed_mean_mm).toBe(100.1);
  });

  it("rejects a payload missing the observed replay fields or with an unknown model", async () => {
    const partial: Partial<typeof row> = { ...row };
    delete partial.observed_mean_mm;
    vi.stubGlobal("fetch", okJson({ ...body, districts: [partial] }));
    await expect(getOperationalDistricts(2025, "20250714_day2_24h")).rejects.toThrow();
    vi.stubGlobal("fetch", okJson({ ...body, model: "m9" }));
    await expect(getOperationalDistricts(2025, "20250714_day2_24h")).rejects.toThrow();
  });
});

describe("district compare and history parsing", () => {
  const cell = { mean_mm: 13.3, max_mm: 28, heavy_area_fraction: 0, very_heavy_area_fraction: 0, error_mm: -86.8, improvement_vs_raw_mm: -1 };
  const compareBody = {
    case_id: "20250714_day2_24h", year: 2025, year_role: "FINAL_TEST_COMPLETED", models: ["m1", "m2", "m3", "m4"],
    model_roles: { m1: "Ridge MOS" }, units: "mm/24h", heavy_threshold_mm: 64.5, very_heavy_threshold_mm: 115.6, predicted_regime: null,
    improvement_definition: "closer to IMD than Raw", source_district_count: 188, method: "x", weights_sha256: "a".repeat(64), geometry_sha256: "b".repeat(64), caveats: ["c"],
    districts: [{ district_id: "D1", district_name: "Raigarh", valid_grid_cells: 21, raw_mean_mm: 14.3, raw_max_mm: 30, raw_error_mm: -85.8, observed_mean_mm: 100.1,
      observed_max_mm: 150, observed_heavy_area_fraction: 0.9, observed_very_heavy_area_fraction: 0.2, heavy_probability: 0.006, very_heavy_probability: null,
      models: { m1: cell, m2: cell, m3: cell, m4: cell } }],
  };

  it("requests the compare route and keeps nullable probabilities null", async () => {
    const fetchMock = okJson(compareBody);
    vi.stubGlobal("fetch", fetchMock);
    const parsed = await getOperationalDistrictsCompare(2025, "20250714_day2_24h");
    expect(String((fetchMock as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0])).toContain("/operational/2025/cases/20250714_day2_24h/districts/compare");
    expect(parsed.districts[0].very_heavy_probability).toBeNull();
    expect(parsed.districts[0].models.m3.improvement_vs_raw_mm).toBe(-1);
  });

  it("rejects a compare payload that is missing one of the four models", async () => {
    const broken = structuredClone(compareBody) as unknown as { districts: { models: Record<string, unknown> }[] };
    delete broken.districts[0].models.m4;
    vi.stubGlobal("fetch", okJson(broken));
    await expect(getOperationalDistrictsCompare(2025, "20250714_day2_24h")).rejects.toThrow();
  });

  it("requests the history route with an encoded district id and model", async () => {
    const history = { year: 2025, year_role: "FINAL_TEST_COMPLETED", district_id: "D 1", district_name: "Raigarh", model: "m3", model_role: "hard", case_count: 1,
      points: [{ case_id: "20250601_day1_24h", initialization_utc: "2025-06-01T00:00:00Z", lead_hours: 24, valid_grid_cells: 21, raw_mean_mm: 5, model_mean_mm: 17, observed_mean_mm: 12 }],
      descriptive_only_note: "Descriptive history only", method: "x", weights_sha256: "a".repeat(64), caveats: [] };
    const fetchMock = okJson(history);
    vi.stubGlobal("fetch", fetchMock);
    const parsed = await getOperationalDistrictHistory(2025, "D 1", "m3");
    expect(String((fetchMock as unknown as { mock: { calls: unknown[][] } }).mock.calls[0][0])).toContain("/operational/2025/districts/D%201/history?model=m3");
    expect(parsed.points[0].observed_mean_mm).toBe(12);
  });
});

describe("case list parsing", () => {
  it("builds query params and preserves nullable case-level metrics", async () => {
    const response = {
      year: 2025, total: 375, page: 1, page_size: 50,
      cases: [{
        case_id: "20250601_day1_24h", year: 2025, initialization_utc: "2025-06-01T00:00:00Z", lead_hours: 24,
        product: "day1_24h", year_role: "FINAL_TEST_COMPLETED", source_complete: true,
        deterministic_source_eligible: true, probability_source_eligible: true, regime_source_eligible: true,
        ensemble_source_eligible: false, c00_rainfall_qc_pass: true, full_5_member_rainfall_qc_pass: false,
        m1_rmse_mm: 3.396, raw_rmse_mm: 3.33, m1_minus_raw_rmse_mm: 0.066,
        initialization_date: "2025-06-01", month: 6, lead_label: "Day 1", valid_date: "2025-06-02",
        event_heavy: false, event_very_heavy: false, pseudo_regime_class: "BREAK_WEAK_MONSOON",
        selected_model_improved_vs_raw: false,
      }],
    };
    vi.stubGlobal("fetch", okJson(response));
    const result = await getOperationalCases(2025, { page: 2, pageSize: 10, leadHours: 24 });
    expect(result.total).toBe(375);
    expect(fetch).toHaveBeenCalledWith("/api/science/operational/2025/cases?page=2&page_size=10&lead_hours=24", { cache: "default", signal: expect.any(AbortSignal) });
  });

  it("accepts null case-level metrics for years without a per-case metrics file", async () => {
    const response = {
      year: 2023, total: 1, page: 1, page_size: 50,
      cases: [{
        case_id: "20230601_day1_24h", year: 2023, initialization_utc: "2023-06-01T00:00:00Z", lead_hours: 24,
        product: "day1_24h", year_role: "TRAIN_CROSSFIT", source_complete: true,
        deterministic_source_eligible: true, probability_source_eligible: true, regime_source_eligible: true,
        ensemble_source_eligible: false, c00_rainfall_qc_pass: true, full_5_member_rainfall_qc_pass: false,
        m1_rmse_mm: null, raw_rmse_mm: null, m1_minus_raw_rmse_mm: null,
        initialization_date: "2023-06-01", month: 6, lead_label: "Day 1", valid_date: "2023-06-02",
        event_heavy: null, event_very_heavy: null, pseudo_regime_class: "ACTIVE_MONSOON",
        selected_model_improved_vs_raw: null,
      }],
    };
    vi.stubGlobal("fetch", okJson(response));
    const result = await getOperationalCases(2023);
    expect(result.cases[0].m1_rmse_mm).toBeNull();
  });
});

describe("grid, atmosphere, probability, regime, ensemble parsing", () => {
  const gridPayload = {
    case_id: "20250601_day1_24h", year: 2025, field: "m1", units: "mm/24h", shape: [49, 49] as [number, number],
    latitude_centers: Array.from({ length: 49 }, (_, i) => 10 + i * 0.25),
    longitude_centers: Array.from({ length: 49 }, (_, i) => 68 + i * 0.25),
    values: Array.from({ length: 49 }, () => Array.from({ length: 49 }, () => null)),
    valid_mask: null, source: "phase4j_operational_final_test_v1",
    scientific_role: "Ridge MOS (pre-registered primary 2025 final-test model)", prediction_role: "FROZEN_ARCHIVAL_PREDICTION",
  };

  it("parses a well-formed rainfall grid", async () => {
    vi.stubGlobal("fetch", okJson(gridPayload));
    const result = await getOperationalRainfall(2025, "20250601_day1_24h", "m1");
    expect(result.shape).toEqual([49, 49]);
    expect(result.values).toHaveLength(49);
  });

  it("rejects a grid whose values row count disagrees with its declared shape", () => {
    const malformed = { ...gridPayload, values: gridPayload.values.slice(0, 10) };
    expect(operationalGridFieldSchema.safeParse(malformed).success).toBe(false);
  });

  it("rejects a grid whose latitude_centers length disagrees with shape", () => {
    const malformed = { ...gridPayload, latitude_centers: [1, 2, 3] };
    expect(operationalGridFieldSchema.safeParse(malformed).success).toBe(false);
  });

  it("parses an atmospheric field without collapsing u/v into a magnitude", async () => {
    const payload = {
      case_id: "20250601_day1_24h", year: 2025, field: "u850", pressure_level_hpa: 850, forecast_hour: 24,
      units: "m/s", shape: [51, 81] as [number, number], values: Array.from({ length: 51 }, () => Array(81).fill(1.2)),
      latitude_centers: Array.from({ length: 51 }, (_, i) => 5 + 0.5 * i), longitude_centers: Array.from({ length: 81 }, (_, j) => 55 + 0.5 * j), grid_spacing_degrees: 0.5,
      coordinate_note: "Frozen context-grid definition", source: "phase4f_payload_acquisition_v1/atmospheric_qc",
    };
    vi.stubGlobal("fetch", okJson(payload));
    const result = await getOperationalAtmosphere(2025, "20250601_day1_24h", "u850");
    expect(result.field).toBe("u850");
    expect(result.pressure_level_hpa).toBe(850);
    expect(result.latitude_centers[0]).toBe(5);
    expect(result.longitude_centers[80]).toBe(95);
  });

  it("rejects an atmospheric field whose coordinates or values do not match its shape", () => {
    const base = {
      case_id: "c", year: 2025, field: "u850", pressure_level_hpa: 850, forecast_hour: 24, units: "m/s", shape: [2, 3] as [number, number],
      values: [[1, 2, 3], [4, 5, 6]], latitude_centers: [5, 5.5], longitude_centers: [55, 55.5, 56], grid_spacing_degrees: 0.5, coordinate_note: "n", source: "s",
    };
    expect(operationalAtmosphericFieldSchema.safeParse(base).success).toBe(true);
    expect(operationalAtmosphericFieldSchema.safeParse({ ...base, latitude_centers: [5] }).success).toBe(false);
    expect(operationalAtmosphericFieldSchema.safeParse({ ...base, longitude_centers: [55, 55.5] }).success).toBe(false);
    expect(operationalAtmosphericFieldSchema.safeParse({ ...base, values: [[1, 2, 3]] }).success).toBe(false);
    expect(operationalAtmosphericFieldSchema.safeParse({ ...base, grid_spacing_degrees: 0 }).success).toBe(false);
  });

  it("parses a probability field", async () => {
    const payload = {
      case_id: "20250601_day1_24h", year: 2025, target: "heavy", threshold_probability: 0.1,
      calibration_type: "frozen isotonic/logistic calibrator selected in Phase 4I",
      values: Array.from({ length: 49 }, () => Array(49).fill(0.02)), prediction_role: "FROZEN_ARCHIVAL_PREDICTION",
    };
    vi.stubGlobal("fetch", okJson(payload));
    const result = await getOperationalProbability(2025, "20250601_day1_24h", "heavy");
    expect(result.target).toBe("heavy");
  });

  it("parses a regime response and preserves the pseudo-regime semantic note", async () => {
    const payload = {
      case_id: "20250601_day1_24h", year: 2025, year_role: "FINAL_TEST_COMPLETED", prediction_role: "FINAL_TEST_PREDICTION",
      classes: ["ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED"],
      probabilities: { ACTIVE_MONSOON: 0.7, BREAK_WEAK_MONSOON: 0.2, LOW_DEPRESSION_INFLUENCED: 0.1 },
      predicted_class: "ACTIVE_MONSOON", semantic_note: "forecast-only pseudo-regime; not independently observed meteorological truth",
    };
    vi.stubGlobal("fetch", okJson(payload));
    const result = await getOperationalRegime(2025, "20250601_day1_24h");
    expect(result.semantic_note).toContain("not independently observed meteorological truth");
  });

  it("parses an ensemble response and preserves per-member QC status without omission", async () => {
    const payload = {
      case_id: "20250601_day1_24h", year: 2025, label: "AVAILABLE FIVE-MEMBER SUBSET",
      members: [
        { member: "c00", qc_eligible: true, values: Array.from({ length: 49 }, () => Array(49).fill(1)) },
        { member: "p01", qc_eligible: false, values: null },
        { member: "p02", qc_eligible: false, values: null },
        { member: "p03", qc_eligible: false, values: null },
        { member: "p04", qc_eligible: true, values: Array.from({ length: 49 }, () => Array(49).fill(2)) },
      ],
    };
    vi.stubGlobal("fetch", okJson(payload));
    const result = await getOperationalEnsemble(2025, "20250601_day1_24h");
    expect(result.members).toHaveLength(5);
    expect(result.members.find((m) => m.member === "p01")?.values).toBeNull();
  });
});

describe("quality, fss, provenance parsing", () => {
  it("preserves the exact known QC counts without rounding", async () => {
    const payload = {
      scheduled_date_lead_cases: 1125, atmosphere_complete: 1125, c00_eligible_total: 615, five_member_eligible_total: 218,
      c00_eligible_by_year: { "2023": 200, "2024": 183, "2025": 232 },
      five_member_eligible_by_year: { "2023": 76, "2024": 67, "2025": 75 },
      atmosphere_complete_by_year: { "2023": 375, "2024": 375, "2025": 375 },
      deterministic_eligible_by_year: { "2023": 200, "2024": 183, "2025": 232 },
      scheduled_by_year: { "2023": 375, "2024": 375, "2025": 375 },
      note: "All selected source messages were acquired",
    };
    vi.stubGlobal("fetch", okJson(payload));
    const result = await getOperationalQuality();
    expect(result.c00_eligible_by_year).toEqual({ "2023": 200, "2024": 183, "2025": 232 });
    expect(result.five_member_eligible_by_year).toEqual({ "2023": 76, "2024": 67, "2025": 75 });
    expect(result.scheduled_by_year).toEqual({ "2023": 375, "2024": 375, "2025": 375 });
  });

  it("passes through frozen FSS payloads verbatim (no interpolation)", async () => {
    const payload = { year: 2025, fss: { heavy: { "1": { raw: { fss: 0.0912 } } } }, neighborhoods: [1, 3, 5, 9] };
    vi.stubGlobal("fetch", okJson(payload));
    const result = await getOperationalFSS(2025);
    expect(result.neighborhoods).toEqual([1, 3, 5, 9]);
  });

  it("parses provenance without leaking a filesystem path", async () => {
    const payload = {
      experiment_version: "operational-era-2023-2025-v1", forecast_source: "NOAA operational GEFS (historical archive)",
      observation_source: "IMD 0.25 degree gridded rainfall", model_versions: { M1: "Ridge MOS" },
      scientific_freeze_status: "FINAL_TEST_COMPLETED (2025 holdout consumed)",
      artifact_verification_status: "phase4j (2025 final test) hash-verified",
    };
    vi.stubGlobal("fetch", okJson(payload));
    const result = await getOperationalProvenance();
    expect(JSON.stringify(result)).not.toMatch(/[A-Za-z]:\\/); // no Windows drive path
  });
});

describe("typed unavailable/integrity error handling", () => {
  it("classifies SCIENCE_INTEGRITY_FAILURE as INTEGRITY_FAILURE", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false, status: 503,
      json: async () => ({ code: "SCIENCE_INTEGRITY_FAILURE", detail: "Frozen artifact integrity failure" }),
    })));
    await expect(getOperationalStatus()).rejects.toMatchObject({ kind: "INTEGRITY_FAILURE", code: "SCIENCE_INTEGRITY_FAILURE" });
  });

  it("classifies the backend's own SCIENCE_CASE_NOT_ELIGIBLE code as NOT_ELIGIBLE_FOR_CASE", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false, status: 404,
      json: async () => ({ code: "SCIENCE_CASE_NOT_ELIGIBLE", detail: "Member p02 failed canonical QC for this case; not exposed as valid" }),
    })));
    try {
      await getOperationalRainfall(2025, "20250601_day1_24h", "p02");
      throw new Error("expected rejection");
    } catch (error) {
      expect(error).toBeInstanceOf(OperationalApiError);
      expect((error as OperationalApiError).kind).toBe("NOT_ELIGIBLE_FOR_CASE");
      expect((error as OperationalApiError).code).toBe("SCIENCE_CASE_NOT_ELIGIBLE");
    }
  });

  it("classifies the backend's own SCIENCE_PRODUCT_UNAVAILABLE code as NOT_AVAILABLE, distinct from QC ineligibility", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false, status: 404,
      json: async () => ({ code: "SCIENCE_PRODUCT_UNAVAILABLE", detail: "Field 'm1' is not available for 2023: models other than M2 are fit on 2023, not scored against it" }),
    })));
    try {
      await getOperationalRainfall(2023, "20230601_day1_24h", "m1");
      throw new Error("expected rejection");
    } catch (error) {
      expect(error).toBeInstanceOf(OperationalApiError);
      expect((error as OperationalApiError).kind).toBe("NOT_AVAILABLE");
      expect((error as OperationalApiError).code).toBe("SCIENCE_PRODUCT_UNAVAILABLE");
    }
  });

  it("classifies a thrown network error (no response at all) as NETWORK_FAILURE", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    await expect(getOperationalStatus()).rejects.toMatchObject({ kind: "NETWORK_FAILURE" });
  });
});
