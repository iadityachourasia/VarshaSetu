import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EVIDENCE_MODELS, EVIDENCE_YEARS, EvidenceApiError, getRegimeEvidence, regimeEvidenceSchema } from "./evidence";

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

const EVIDENCE_DIR = resolve(__dirname, "../../../../backend/app/evidence_data/phase6");

/** Build the API payload from a REAL tracked evidence file, exactly as backend/app/api/evidence.py does. */
function payloadFor(track: "A" | "B", year: number) {
  const data = JSON.parse(readFileSync(resolve(EVIDENCE_DIR, `regime_verification_${track}_${year}.json`), "utf8"));
  const defined: Record<string, Record<string, Record<string, number>>> = {};
  const undefinedCases: Record<string, Record<string, Record<string, number>>> = {};
  for (const threshold of ["heavy", "very_heavy"]) {
    defined[threshold] = {}; undefinedCases[threshold] = {};
    for (const scale of ["1", "3", "5", "9"]) {
      defined[threshold][scale] = {}; undefinedCases[threshold][scale] = {};
      for (const model of EVIDENCE_MODELS) {
        const n = data.overall.fss[threshold][scale].all_cases[model].case_count;
        defined[threshold][scale][model] = n; undefinedCases[threshold][scale][model] = data.case_count - n;
      }
    }
  }
  return {
    track, year, evidence_role: data.evidence_role, evidence_label: "label", evidence_sha256: "a".repeat(64),
    regime_assignment: data.regime_assignment, reproduction: { status: data.reproduction.status, check_count: data.reproduction.check_count, max_abs_diff: data.reproduction.max_abs_diff },
    lineage_sha256: data.lineage_sha256,
    summary: {
      case_count: data.case_count, cell_count: data.overall.cell_count,
      observed_event_cells: { heavy: data.overall.categorical.heavy.M0.observed_event_count, very_heavy: data.overall.categorical.very_heavy.M0.observed_event_count },
      cases_by_regime: Object.fromEntries(Object.entries(data.by_predicted_regime).map(([k, v]) => [k, (v as { case_count: number }).case_count])),
      cases_by_lead_day: Object.fromEntries(Object.entries(data.by_lead_day).map(([k, v]) => [k, (v as { case_count: number }).case_count])),
      defined_fss_cases: defined, undefined_fss_cases: undefinedCases,
    },
    overall: data.overall, by_predicted_regime: data.by_predicted_regime, by_lead_day: data.by_lead_day, bootstrap: data.bootstrap, caveats: ["c"],
  };
}

const ok = (body: unknown) => vi.fn(async (...args: [string]) => { void args; return { ok: true, status: 200, json: async () => body }; });

describe("regime evidence schema against the real tracked evidence", () => {
  for (const [track, years] of Object.entries(EVIDENCE_YEARS) as ["A" | "B", readonly number[]][]) {
    for (const year of years) {
      it(`parses Track ${track} ${year} with undefined FSS and null metrics preserved`, () => {
        const parsed = regimeEvidenceSchema.parse(payloadFor(track, year));
        expect(parsed.summary.case_count).toBeGreaterThan(100);
        expect(Object.keys(parsed.by_predicted_regime)).toHaveLength(3);
        expect(Object.keys(parsed.by_lead_day)).toEqual(["day1", "day2", "day3"]);
        // very-heavy FAR is genuinely undefined where a model forecasts no event: must stay null, never coerced to 0
        const veryHeavy = parsed.overall.categorical.very_heavy;
        for (const model of EVIDENCE_MODELS) {
          if (veryHeavy[model].forecast_event_count === 0) expect(veryHeavy[model].FAR).toBeNull();
        }
      });
    }
  }

  it("rejects a payload with an invalid hash length, a missing model or a missing regime block", () => {
    const base = payloadFor("A", 2019);
    expect(() => regimeEvidenceSchema.parse({ ...base, evidence_sha256: "abc" })).toThrow();
    const broken = structuredClone(base) as typeof base & { overall: { continuous: Record<string, unknown> } };
    delete broken.overall.continuous.M4;
    expect(() => regimeEvidenceSchema.parse(broken)).toThrow();
  });
});

describe("getRegimeEvidence", () => {
  it("requests the track/year route and returns a validated payload", async () => {
    const fetchMock = ok(payloadFor("B", 2025));
    vi.stubGlobal("fetch", fetchMock);
    const parsed = await getRegimeEvidence("B", 2025);
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/science/evidence/regime-verification?track=B&year=2025");
    expect(parsed.year).toBe(2025);
  });

  it("surfaces structured {code, detail} errors, including an integrity failure", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 503, json: async () => ({ code: "SCIENCE_INTEGRITY_FAILURE", detail: "hash mismatch" }) })));
    await expect(getRegimeEvidence("A", 2019)).rejects.toMatchObject({ name: "EvidenceApiError", code: "SCIENCE_INTEGRITY_FAILURE", status: 503, message: "hash mismatch" });
  });

  it("classifies a network failure without a status and never falls back to invented data", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));
    const error = await getRegimeEvidence("A", 2019).catch((e) => e);
    expect(error).toBeInstanceOf(EvidenceApiError);
    expect(error.status).toBeNull();
  });
});

// ---- district-level verification (protocol v1) ---------------------------------------------------

import { DISTRICT_VERIFICATION_YEARS, districtVerificationSchema, getDistrictVerification } from "./evidence";

function districtPayload(year: number) {
  const data = JSON.parse(readFileSync(resolve(EVIDENCE_DIR, `district_verification_B_${year}.json`), "utf8"));
  return {
    track: "B", year, evidence_role: data.evidence_role, evidence_label: "label", evidence_sha256: "a".repeat(64), protocol_sha256: data.protocol_sha256,
    protocol_status: "APPROVED_FOR_EXECUTION", protocol_decisions: {}, regime_assignment: data.regime_assignment,
    reproduction: { status: data.reproduction.status, check_count: data.reproduction.check_count }, inclusion: data.inclusion, continuous: data.continuous,
    categorical: data.categorical, contrasts: data.contrasts, improved_worsened: data.improved_worsened, supported_district_counts: data.supported_district_counts,
    observed_events_pooled: data.observed_events_pooled, districts: data.districts, caveats: ["c"],
  };
}

describe("district verification schema against the real tracked evidence", () => {
  for (const year of DISTRICT_VERIFICATION_YEARS) {
    it(`parses Track B ${year} and keeps undefined values null`, () => {
      const parsed = districtVerificationSchema.parse(districtPayload(year));
      expect(parsed.inclusion.districts_included).toBe(169);
      expect(parsed.districts).toHaveLength(169);
      expect(Object.keys(parsed.categorical)).toEqual(["E1", "E2", "E3"]);
      const supported = parsed.districts.filter((d) => d.categorical.E1.heavy.status === "supported");
      expect(supported.length).toBeGreaterThan(20);
      for (const d of parsed.districts) {
        const cell = d.categorical.E1.heavy;
        expect(cell.status === "supported").toBe(cell.models !== null);
      }
      // a model that forecasts no event has an undefined FAR, which must stay null rather than 0
      const veryHeavy = parsed.categorical.E2.very_heavy.pooled.all;
      for (const model of EVIDENCE_MODELS) {
        if (veryHeavy[model].forecast_event_count === 0) expect(veryHeavy[model].FAR).toBeNull();
      }
    });
  }

  it("rejects a payload with a bad protocol hash, a missing pooled block or an unknown status", () => {
    const base = districtPayload(2025);
    expect(() => districtVerificationSchema.parse({ ...base, protocol_sha256: "abc" })).toThrow();
    const noPooled = structuredClone(base) as unknown as { categorical: { E1: { heavy: { pooled: Record<string, unknown> } } } };
    delete noPooled.categorical.E1.heavy.pooled.all;
    expect(() => districtVerificationSchema.parse(noPooled)).toThrow();
    const badStatus = structuredClone(base) as unknown as { districts: { categorical: { E1: { heavy: { status: string } } } }[] };
    badStatus.districts[0].categorical.E1.heavy.status = "maybe";
    expect(() => districtVerificationSchema.parse(badStatus)).toThrow();
  });

  it("requests the district route and surfaces structured errors", async () => {
    const fetchMock = ok(districtPayload(2024));
    vi.stubGlobal("fetch", fetchMock);
    await getDistrictVerification(2024);
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/science/evidence/district-verification?year=2024");
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 404, json: async () => ({ code: "SCIENCE_PRODUCT_UNAVAILABLE", detail: "No district verification for Track B 2023" }) })));
    await expect(getDistrictVerification(2023)).rejects.toMatchObject({ code: "SCIENCE_PRODUCT_UNAVAILABLE", status: 404 });
  });
});

// ---- SIH26080 coverage ----------------------------------------------------------------------------

import { getPsCoverage, psCoverageSchema } from "./evidence";

function coveragePayload() {
  const raw = JSON.parse(readFileSync(resolve(EVIDENCE_DIR, "ps_coverage.json"), "utf8"));
  const rows = raw.rows.map((row: { facts: { label: string; format: string; source: string }[] }) => ({
    ...row, facts: row.facts.map((f) => ({ label: f.label, value: 0.5, format: f.format, source: f.source, source_sha256: "a".repeat(64), evidence_label: "label" })),
  }));
  const counts = Object.fromEntries(raw.status_vocabulary.map((s: string) => [s, rows.filter((r: { status: string }) => r.status === s).length]));
  return { schema_id: raw.schema, title: raw.title, rules: raw.rules, status_vocabulary: raw.status_vocabulary, counts, mandatory_counts: counts, coverage_sha256: "b".repeat(64), rows };
}

describe("SIH26080 coverage schema against the real tracked manifest", () => {
  it("parses every row and keeps the honest statuses of the missing mandatory regimes", () => {
    const parsed = psCoverageSchema.parse(coveragePayload());
    expect(parsed.rows.length).toBeGreaterThanOrEqual(25);
    const byId = new Map(parsed.rows.map((r) => [r.id, r]));
    for (const id of ["REGIME-COASTAL-OROGRAPHIC", "REGIME-WESTERN-DISTURBANCE", "LIVE-INFERENCE"]) expect(byId.get(id)?.status).toBe("PLANNED");
    expect(byId.get("REGIME-CLASSIFIER")?.status).toBe("PARTIAL");
    const covered = new Set(parsed.rows.flatMap((r) => r.ps_ids));
    for (let n = 1; n <= 14; n++) expect(covered.has(`PS-R${String(n).padStart(2, "0")}`)).toBe(true);
    for (const row of parsed.rows) if (row.status === "IMPLEMENTED") expect(row.pages.length).toBeGreaterThan(0);
  });

  it("rejects an unknown status, a non-absolute page link and a non-numeric fact", () => {
    const base = coveragePayload();
    expect(() => psCoverageSchema.parse({ ...base, rows: [{ ...base.rows[0], status: "DONE" }] })).toThrow();
    expect(() => psCoverageSchema.parse({ ...base, rows: [{ ...base.rows[0], pages: [{ label: "x", href: "regimes" }] }] })).toThrow();
    const withFact = base.rows.find((r: { facts: unknown[] }) => r.facts.length);
    expect(() => psCoverageSchema.parse({ ...base, rows: [{ ...withFact, facts: [{ ...withFact.facts[0], value: null }] }] })).toThrow();
  });

  it("requests the coverage route and surfaces integrity failures", async () => {
    const fetchMock = ok(coveragePayload());
    vi.stubGlobal("fetch", fetchMock);
    await getPsCoverage();
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/science/evidence/ps-coverage");
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 503, json: async () => ({ code: "SCIENCE_INTEGRITY_FAILURE", detail: "pointer does not resolve" }) })));
    await expect(getPsCoverage()).rejects.toMatchObject({ code: "SCIENCE_INTEGRITY_FAILURE", status: 503 });
  });
});
