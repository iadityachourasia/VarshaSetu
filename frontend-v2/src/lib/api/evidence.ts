// Typed, Zod-validated client for the read-only, hash-verified regime/lead-stratified verification
// evidence at /api/science/evidence/* (docs/108). Mirrors the conventions of ./science.ts and
// ./operational.ts: same-origin proxy, structured {code, detail} errors, and never inventing a value.
import { z } from "zod";

export const EVIDENCE_MODELS = ["M0", "M1", "M2", "M3", "M4"] as const;
export type EvidenceModel = (typeof EVIDENCE_MODELS)[number];
export const EVIDENCE_THRESHOLDS = ["heavy", "very_heavy"] as const;
export type EvidenceThreshold = (typeof EVIDENCE_THRESHOLDS)[number];
export const EVIDENCE_SCALES = ["1", "3", "5", "9"] as const;
export type EvidenceScale = (typeof EVIDENCE_SCALES)[number];
export const EVIDENCE_REGIMES = ["ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED"] as const;

const perModel = <T extends z.ZodTypeAny>(value: T) => z.object({
  M0: value, M1: value, M2: value, M3: value, M4: value,
});
const nullableNumber = z.number().nullable();

const continuousSchema = z.object({
  sample_count: z.number(), rmse_mm: nullableNumber, mae_mm: nullableNumber, bias_mm: nullableNumber,
});
export const categoricalSchema = z.object({
  hits: z.number(), misses: z.number(), false_alarms: z.number(), sample_count: z.number(),
  observed_event_count: z.number(), forecast_event_count: z.number(),
  POD: nullableNumber, FAR: nullableNumber, CSI: nullableNumber, ETS: nullableNumber,
});
const fssScoreSchema = z.object({ fss: nullableNumber, case_count: z.number(), reason: z.string().nullable() });
const fssScaleSchema = z.object({
  all_cases: perModel(fssScoreSchema),
  matched_all_models: z.object({ case_count: z.number() }).and(perModel(nullableNumber)),
});
const thresholdRecord = <T extends z.ZodTypeAny>(value: T) => z.object({ heavy: value, very_heavy: value });

export const evidenceBlockSchema = z.object({
  case_count: z.number(),
  cell_count: z.number(),
  continuous: perModel(continuousSchema),
  categorical: thresholdRecord(perModel(categoricalSchema)),
  fss: thresholdRecord(z.object({ "1": fssScaleSchema, "3": fssScaleSchema, "5": fssScaleSchema, "9": fssScaleSchema })),
});
export type EvidenceBlock = z.infer<typeof evidenceBlockSchema>;

const bootstrapStatSchema = z.object({
  status: z.string(),
  point: z.number().optional(),
  interval95: z.tuple([z.number(), z.number()]).optional(),
  fraction_positive: z.number().optional(),
  repeats: z.number().optional(),
}).passthrough();
const bootstrapPairSchema = z.object({
  CSI: bootstrapStatSchema, FSS_3x3: bootstrapStatSchema, FSS_9x9: bootstrapStatSchema,
}).passthrough();
export const BOOTSTRAP_PAIRS = ["M3_minus_M0", "M3_minus_M2", "M4_minus_M0", "M4_minus_M2", "M2_minus_M0", "M3_minus_M4"] as const;
const bootstrapBlockSchema = thresholdRecord(z.record(z.string(), bootstrapPairSchema));
export type BootstrapStat = z.infer<typeof bootstrapStatSchema>;

const lookup = <T extends z.ZodTypeAny>(value: T) => z.record(z.string(), value);

export const regimeEvidenceSchema = z.object({
  track: z.enum(["A", "B"]),
  year: z.number(),
  evidence_role: z.string(),
  evidence_label: z.string(),
  evidence_sha256: z.string().length(64),
  regime_assignment: z.string(),
  reproduction: z.object({ status: z.string(), check_count: z.number(), max_abs_diff: z.number() }).passthrough(),
  lineage_sha256: z.record(z.string(), z.unknown()),
  summary: z.object({
    case_count: z.number(),
    cell_count: z.number(),
    observed_event_cells: thresholdRecord(z.number()),
    cases_by_regime: lookup(z.number()),
    cases_by_lead_day: lookup(z.number()),
    defined_fss_cases: thresholdRecord(lookup(lookup(z.number()))),
    undefined_fss_cases: thresholdRecord(lookup(lookup(z.number()))),
  }),
  overall: evidenceBlockSchema,
  by_predicted_regime: lookup(evidenceBlockSchema),
  by_lead_day: lookup(evidenceBlockSchema),
  bootstrap: z.object({
    overall: bootstrapBlockSchema,
    by_predicted_regime: lookup(bootstrapBlockSchema.nullable()),
  }),
  caveats: z.array(z.string()),
});
export type RegimeEvidence = z.infer<typeof regimeEvidenceSchema>;

export class EvidenceApiError extends Error {
  readonly status: number | null;
  readonly code: string | null;
  constructor(message: string, status: number | null, code: string | null) {
    super(message);
    this.name = "EvidenceApiError";
    this.status = status;
    this.code = code;
  }
}

export async function getRegimeEvidence(track: "A" | "B", year: number, server = false): Promise<RegimeEvidence> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/regime-verification?track=${track}&year=${year}`, {
      cache: server ? "no-store" : "default",
      signal: AbortSignal.timeout(server ? 25_000 : 20_000),
    });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Evidence request failed (${response.status})`;
    try {
      const body = (await response.json()) as { code?: unknown; detail?: unknown };
      if (typeof body?.code === "string") code = body.code;
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // no JSON body; keep the generic message
    }
    throw new EvidenceApiError(detail, response.status, code);
  }
  return regimeEvidenceSchema.parse(await response.json());
}

/** Which populations have published regime-verification evidence (mirrors the backend manifest). */
export const EVIDENCE_YEARS: Record<"A" | "B", readonly number[]> = { A: [2018, 2019], B: [2024, 2025] };


// ---------------------------------------------------------------------------
// District-level verification (protocol v1, docs/112)
// ---------------------------------------------------------------------------

export const DISTRICT_DEFINITIONS = ["E1", "E2", "E3"] as const;
export type DistrictDefinition = (typeof DISTRICT_DEFINITIONS)[number];
export const DISTRICT_MODELS = ["M1", "M2", "M3", "M4"] as const;
export type DistrictModel = (typeof DISTRICT_MODELS)[number];
export const DISTRICT_BREAKDOWNS = ["pooled", "by_lead", "by_regime", "by_region"] as const;
export type DistrictBreakdown = (typeof DISTRICT_BREAKDOWNS)[number];
export const DISTRICT_CONTRAST_KEYS = ["M1_minus_M0", "M2_minus_M0", "M3_minus_M0", "M4_minus_M0", "M3_minus_M2", "M4_minus_M2", "M3_minus_M4"] as const;
export const DISTRICT_VERIFICATION_YEARS = [2018, 2019, 2024, 2025] as const;
export const DISTRICT_TRACK_OF_YEAR: Record<(typeof DISTRICT_VERIFICATION_YEARS)[number], "A" | "B"> = { 2018: "A", 2019: "A", 2024: "B", 2025: "B" };

const districtContinuousSchema = z.object({ pairs: z.number(), rmse_mm: nullableNumber, mae_mm: nullableNumber, bias_mm: nullableNumber });
const improvementSchema = z.object({
  mean_improvement_mm: nullableNumber,
  interval95: z.tuple([nullableNumber, nullableNumber]),
  status: z.enum(["improved", "worsened", "indeterminate", "undefined"]),
});
const districtEntrySchema = z.object({
  district_id: z.string(),
  district_name: z.string(),
  region: z.string(),
  included_cases: z.number(),
  median_valid_cells: z.number(),
  continuous: z.union([z.literal("insufficient_support"), perModel(districtContinuousSchema)]),
  improvement: z.union([z.literal("insufficient_support"), z.object({ M1: improvementSchema, M2: improvementSchema, M3: improvementSchema, M4: improvementSchema })]),
  categorical: z.record(z.string(), thresholdRecord(z.object({
    observed_events: z.number(),
    status: z.enum(["supported", "insufficient_support"]),
    models: perModel(categoricalSchema).nullable(),
  }))),
});
export type DistrictEntry = z.infer<typeof districtEntrySchema>;

const groupedCategorical = z.record(z.string(), perModel(categoricalSchema));

export const districtVerificationSchema = z.object({
  track: z.enum(["A", "B"]),
  year: z.number(),
  evidence_role: z.string(),
  evidence_label: z.string(),
  evidence_sha256: z.string().length(64),
  protocol_sha256: z.string().length(64),
  protocol_status: z.string(),
  protocol_decisions: z.record(z.string(), z.unknown()),
  regime_assignment: z.string(),
  reproduction: z.object({ status: z.string(), check_count: z.number() }).passthrough(),
  inclusion: z.object({
    cases: z.number(), districts_total: z.number(), districts_included: z.number(), district_case_pairs: z.number(), min_valid_cells: z.number(),
    districts_excluded: z.array(z.object({ district_id: z.string(), district_name: z.string(), median_valid_cells: z.number() })),
  }),
  continuous: z.record(z.string(), z.record(z.string(), perModel(districtContinuousSchema))),
  categorical: z.record(z.string(), thresholdRecord(z.object({
    pooled: groupedCategorical.refine((value) => "all" in value), by_lead: groupedCategorical, by_regime: groupedCategorical, by_region: groupedCategorical,
  }))),
  contrasts: z.object({
    categorical: z.record(z.string(), thresholdRecord(z.record(z.string(), z.object({ CSI: bootstrapStatSchema })))),
    continuous: z.record(z.string(), bootstrapStatSchema),
  }),
  improved_worsened: z.record(z.string(), z.object({
    tested_districts: z.number(), improved: z.number(), worsened: z.number(), indeterminate: z.number(), undefined: z.number(),
    expected_by_chance_total: z.number(), expected_by_chance_per_direction: z.number(),
  })),
  supported_district_counts: z.record(z.string(), thresholdRecord(z.number())),
  observed_events_pooled: z.record(z.string(), thresholdRecord(z.number())),
  districts: z.array(districtEntrySchema),
  caveats: z.array(z.string()),
});
export type DistrictVerification = z.infer<typeof districtVerificationSchema>;

export async function getDistrictVerification(year: number, server = false): Promise<DistrictVerification> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/district-verification?year=${year}`, {
      cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000),
    });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `District verification request failed (${response.status})`;
    try {
      const body = (await response.json()) as { code?: unknown; detail?: unknown };
      if (typeof body?.code === "string") code = body.code;
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // no JSON body; keep the generic message
    }
    throw new EvidenceApiError(detail, response.status, code);
  }
  return districtVerificationSchema.parse(await response.json());
}


// ---------------------------------------------------------------------------
// SIH26080 requirement coverage (P0-6): figures are resolved server-side from hash-verified evidence
// ---------------------------------------------------------------------------

export const COVERAGE_STATUSES = ["IMPLEMENTED", "PARTIAL", "PLANNED"] as const;
export type CoverageStatus = (typeof COVERAGE_STATUSES)[number];

export const psCoverageSchema = z.object({
  schema_id: z.string(),
  title: z.string(),
  rules: z.array(z.string()),
  status_vocabulary: z.array(z.enum(COVERAGE_STATUSES)),
  counts: z.record(z.string(), z.number()),
  mandatory_counts: z.record(z.string(), z.number()),
  coverage_sha256: z.string().length(64),
  rows: z.array(z.object({
    id: z.string(),
    group: z.string(),
    requirement: z.string(),
    ps_ids: z.array(z.string()),
    ps_mandatory: z.boolean(),
    status: z.enum(COVERAGE_STATUSES),
    summary: z.string(),
    limitation: z.string(),
    pages: z.array(z.object({ label: z.string(), href: z.string().startsWith("/") })),
    docs: z.array(z.string()),
    facts: z.array(z.object({
      label: z.string(), value: z.number(), format: z.enum(["mm2", "score3", "int"]), source: z.string(),
      source_sha256: z.string().length(64), evidence_label: z.string(),
    })),
  })),
});
export type PsCoverage = z.infer<typeof psCoverageSchema>;
export type PsCoverageRow = PsCoverage["rows"][number];

export async function getPsCoverage(server = false): Promise<PsCoverage> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/ps-coverage`, { cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Coverage request failed (${response.status})`;
    try {
      const body = (await response.json()) as { code?: unknown; detail?: unknown };
      if (typeof body?.code === "string") code = body.code;
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // no JSON body; keep the generic message
    }
    throw new EvidenceApiError(detail, response.status, code);
  }
  return psCoverageSchema.parse(await response.json());
}
