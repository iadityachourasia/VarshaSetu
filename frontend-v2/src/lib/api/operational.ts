// Typed, Zod-validated client for the read-only Phase 5A.1/5A.1B operational-era
// (2023-2025) presentation API at /api/science/operational/*. Mirrors the exact
// conventions of ./science.ts (same getScience fetcher, same same-origin proxy
// behavior, same "never invent a missing value" contract) rather than
// introducing a second data-access architecture. See
// docs/93_OPERATIONAL_ATTRIBUTION_AND_FRONTEND_CLIENT.md for the full contract.
import { z } from "zod";

// ---------------------------------------------------------------------------
// Shared primitives
// ---------------------------------------------------------------------------

export const operationalYearSchema = z.union([z.literal(2023), z.literal(2024), z.literal(2025)]);
export type OperationalYear = z.infer<typeof operationalYearSchema>;

const matrix = z.array(z.array(z.number().nullable()));

const capabilityGrid = z.enum(["unavailable", "case_grid", "aggregate_metric_only", "out_of_fold_case_grid"]);
const capabilityRegime = z.enum(["unavailable", "per_case", "aggregate_distribution_only"]);
const capabilityEnsemble = z.enum(["unavailable", "eligible_subset_only"]);

// ---------------------------------------------------------------------------
// Status / years / availability
// ---------------------------------------------------------------------------

export const operationalStatusSchema = z.object({
  experiment: z.string(),
  label: z.string(),
  forecast_source: z.string(),
  observation_source: z.string(),
  years: z.record(z.string(), z.string()),
  api_version: z.string(),
  integrity_model: z.string(),
});

export const operationalAvailabilitySchema = z.object({
  year: z.number(),
  role: z.string(),
  role_label: z.string(),
  raw_rainfall: z.boolean(),
  imd_observation: z.boolean(),
  m1: capabilityGrid,
  m2: capabilityGrid,
  m3: capabilityGrid,
  m4: capabilityGrid,
  heavy_probability: capabilityGrid,
  very_heavy_probability: capabilityGrid,
  regime_probability: capabilityRegime,
  atmosphere_fields: z.boolean(),
  ensemble_members: capabilityEnsemble,
  case_level_metrics: z.boolean(),
  per_cell_metrics: z.boolean(),
  fss: z.boolean(),
  reliability_bins: z.boolean(),
  pr_roc_curve_arrays: z.literal("unavailable"),
  district_aggregates: z.literal(false),
  notes: z.array(z.string()),
});
export const operationalYearsSchema = z.array(operationalAvailabilitySchema);

// ---------------------------------------------------------------------------
// Case index / detail
// ---------------------------------------------------------------------------

export const operationalCaseSummarySchema = z.object({
  case_id: z.string(),
  year: z.number(),
  initialization_utc: z.string(),
  lead_hours: z.number(),
  product: z.string(),
  year_role: z.string(),
  source_complete: z.boolean(),
  deterministic_source_eligible: z.boolean(),
  probability_source_eligible: z.boolean(),
  regime_source_eligible: z.boolean(),
  ensemble_source_eligible: z.boolean(),
  c00_rainfall_qc_pass: z.boolean(),
  full_5_member_rainfall_qc_pass: z.boolean(),
  m1_rmse_mm: z.number().nullable(),
  raw_rmse_mm: z.number().nullable(),
  m1_minus_raw_rmse_mm: z.number().nullable(),
  initialization_date: z.string(),
  month: z.number(),
  lead_label: z.string(),
  valid_date: z.string().nullable(),
  event_heavy: z.boolean().nullable(),
  event_very_heavy: z.boolean().nullable(),
  pseudo_regime_class: z.enum(["ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED"]).nullable(),
  selected_model_improved_vs_raw: z.boolean().nullable(),
});
export const operationalCasesResponseSchema = z.object({
  year: z.number(),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  cases: z.array(operationalCaseSummarySchema),
});
export const operationalCaseDetailSchema = operationalCaseSummarySchema.extend({
  member_qc: z.record(z.string(), z.boolean()),
  available_products: z.array(z.string()),
});

// ---------------------------------------------------------------------------
// Grid-bearing products (rainfall / atmosphere / probability)
// ---------------------------------------------------------------------------

export const operationalGridFieldSchema = z.object({
  case_id: z.string(),
  year: z.number(),
  field: z.string(),
  units: z.string(),
  shape: z.tuple([z.number().int().positive(), z.number().int().positive()]),
  latitude_centers: z.array(z.number()).nullable(),
  longitude_centers: z.array(z.number()).nullable(),
  values: matrix,
  valid_mask: z.array(z.array(z.unknown())).nullable(),
  source: z.string(),
  scientific_role: z.string(),
  prediction_role: z.string(),
}).superRefine((payload, ctx) => {
  // Grid validation (Phase 5A.1B section 20): never let a malformed grid
  // payload silently render -- shape must agree with the actual value/
  // coordinate array sizes.
  const [rows, cols] = payload.shape;
  if (payload.values.length !== rows) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: `values has ${payload.values.length} rows, shape declares ${rows}` });
  }
  if (payload.values[0] && payload.values[0].length !== cols) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: `values row length ${payload.values[0].length} != declared ${cols}` });
  }
  if (payload.latitude_centers && payload.latitude_centers.length !== rows) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: "latitude_centers length does not match shape" });
  }
  if (payload.longitude_centers && payload.longitude_centers.length !== cols) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: "longitude_centers length does not match shape" });
  }
});
export type OperationalGridField = z.infer<typeof operationalGridFieldSchema>;

export const operationalAtmosphericFieldSchema = z.object({
  case_id: z.string(),
  year: z.number(),
  field: z.string(),
  pressure_level_hpa: z.number().nullable(),
  forecast_hour: z.number(),
  units: z.string(),
  shape: z.tuple([z.number().int().positive(), z.number().int().positive()]),
  values: matrix,
  coordinate_note: z.string(),
  source: z.string(),
});
export type OperationalAtmosphericField = z.infer<typeof operationalAtmosphericFieldSchema>;

export const operationalProbabilityFieldSchema = z.object({
  case_id: z.string(),
  year: z.number(),
  target: z.enum(["heavy", "very_heavy"]),
  threshold_probability: z.number(),
  calibration_type: z.string(),
  values: matrix,
  prediction_role: z.string(),
});
export type OperationalProbabilityField = z.infer<typeof operationalProbabilityFieldSchema>;

// ---------------------------------------------------------------------------
// Regime (per-case)
// ---------------------------------------------------------------------------

export const operationalRegimeSchema = z.object({
  case_id: z.string(),
  year: z.number(),
  year_role: z.string(),
  prediction_role: z.enum(["OUT_OF_FOLD", "PROSPECTIVE_VALIDATION", "FINAL_TEST_PREDICTION"]),
  classes: z.array(z.string()),
  probabilities: z.record(z.string(), z.number()),
  predicted_class: z.string(),
  semantic_note: z.string(),
});
export type OperationalRegime = z.infer<typeof operationalRegimeSchema>;

export const operationalRegimeSummarySchema = z.object({
  year: z.number(),
  prediction_role: z.string(),
  semantic_note: z.string(),
  distribution: z.record(z.string(), z.unknown()),
});

// ---------------------------------------------------------------------------
// Ensemble
// ---------------------------------------------------------------------------

export const operationalEnsembleMemberSchema = z.object({
  member: z.enum(["c00", "p01", "p02", "p03", "p04"]),
  qc_eligible: z.boolean(),
  values: matrix.nullable(),
});
export const operationalEnsembleSchema = z.object({
  case_id: z.string(),
  year: z.number(),
  label: z.literal("AVAILABLE FIVE-MEMBER SUBSET"),
  members: z.array(operationalEnsembleMemberSchema),
});
export type OperationalEnsemble = z.infer<typeof operationalEnsembleSchema>;

// ---------------------------------------------------------------------------
// Metrics (verbatim frozen payloads -- validated loosely by design; this
// client must not reshape, round, or otherwise transform stored numbers)
// ---------------------------------------------------------------------------

export const operationalDeterministicMetricsSchema = z.object({
  year: z.number(),
  metrics: z.record(z.string(), z.unknown()),
  primary_model: z.string().nullable(),
  notes: z.array(z.string()),
});
export const operationalProbabilityMetricsSchema = z.object({
  year: z.number(),
  metrics: z.record(z.string(), z.unknown()),
  curve_arrays: z.literal("unavailable"),
});
export const operationalFssSchema = z.object({
  year: z.number(),
  fss: z.record(z.string(), z.unknown()),
  neighborhoods: z.array(z.number()),
});
export const operationalEnsembleMetricsSchema = z.object({
  year: z.number(),
  metrics: z.record(z.string(), z.unknown()),
  label: z.literal("MATCHED 75-CASE SUBSET"),
  note: z.string(),
});

// ---------------------------------------------------------------------------
// Quality / provenance
// ---------------------------------------------------------------------------

export const operationalQualitySchema = z.object({
  scheduled_date_lead_cases: z.number(),
  atmosphere_complete: z.number(),
  c00_eligible_total: z.number(),
  five_member_eligible_total: z.number(),
  c00_eligible_by_year: z.record(z.string(), z.number()),
  five_member_eligible_by_year: z.record(z.string(), z.number()),
  atmosphere_complete_by_year: z.record(z.string(), z.number()),
  deterministic_eligible_by_year: z.record(z.string(), z.number()),
  scheduled_by_year: z.record(z.string(), z.number()),
  note: z.string(),
});
export const operationalProvenanceSchema = z.object({
  experiment_version: z.string(),
  forecast_source: z.string(),
  observation_source: z.string(),
  model_versions: z.record(z.string(), z.unknown()),
  scientific_freeze_status: z.string(),
  artifact_verification_status: z.string(),
});

// ---------------------------------------------------------------------------
// Typed unavailable-product error contract (section 17-18)
// ---------------------------------------------------------------------------

/**
 * As of Phase 5A.2, /api/science/operational/* returns a structured
 * `{code, detail}` body on every error (see backend/app/api/operational.py's
 * ScienceErrorCode + main.py's structured_science_error_handler) -- this is
 * additive and does not change any existing /api/science/* (Track A) response,
 * which still returns a plain string `detail` and is read by science.ts's
 * getScience unchanged. OperationalApiError.kind is derived directly from the
 * backend's own declared code, not pattern-matched over free text.
 */
export type OperationalErrorKind = "NOT_AVAILABLE" | "NOT_ELIGIBLE_FOR_CASE" | "INTEGRITY_FAILURE" | "NETWORK_FAILURE";

const CODE_TO_KIND: Record<string, OperationalErrorKind> = {
  SCIENCE_PRODUCT_UNAVAILABLE: "NOT_AVAILABLE",
  SCIENCE_CASE_NOT_FOUND: "NOT_AVAILABLE",
  SCIENCE_INVALID_FIELD: "NOT_AVAILABLE",
  SCIENCE_CASE_NOT_ELIGIBLE: "NOT_ELIGIBLE_FOR_CASE",
  SCIENCE_INTEGRITY_FAILURE: "INTEGRITY_FAILURE",
};

export class OperationalApiError extends Error {
  readonly kind: OperationalErrorKind;
  readonly code: string | null;
  readonly status: number | null;

  constructor(kind: OperationalErrorKind, message: string, status: number | null, code: string | null = null) {
    super(message);
    this.name = "OperationalApiError";
    this.kind = kind;
    this.code = code;
    this.status = status;
  }
}

function classifyOperationalError(status: number | null, code: string | null, detail: string): OperationalApiError {
  if (status === null) return new OperationalApiError("NETWORK_FAILURE", detail || "Network request failed", null, null);
  if (code && CODE_TO_KIND[code]) return new OperationalApiError(CODE_TO_KIND[code], detail || code, status, code);
  // Fallback only for a response that somehow lacks a recognized code (should
  // not happen against this backend; kept so a future/foreign error body
  // still degrades to a sane typed error instead of throwing an unhandled one).
  if (status === 503) return new OperationalApiError("INTEGRITY_FAILURE", detail || "Frozen artifact integrity failure", status, code);
  return new OperationalApiError("NOT_AVAILABLE", detail || "Requested product is not available", status, code);
}

/** Same same-origin/server-origin base-URL logic as getScience, routed under
 * /operational, but reading the structured {code, detail} error body so
 * callers can branch on `.kind`/`.code` instead of parsing a message string. */
async function getOperational<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/operational${path}`, {
      cache: server ? "no-store" : "default",
      signal: AbortSignal.timeout(server ? 25_000 : 20_000),
    });
  } catch (error) {
    throw classifyOperationalError(null, null, error instanceof Error ? error.message : "Network request failed");
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = "";
    try {
      const body = (await response.json()) as { code?: unknown; detail?: unknown };
      if (typeof body?.code === "string") code = body.code;
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // no JSON body to read; fall through with an empty detail/code
    }
    throw classifyOperationalError(response.status, code, detail);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch (error) {
    // A response can send its headers, then stall while streaming the body.
    // AbortSignal.timeout applies to that read too. Keep malformed JSON as a
    // contract failure, but classify an interrupted body as a network failure.
    if (error instanceof SyntaxError) throw error;
    throw classifyOperationalError(null, null, error instanceof Error ? error.message : "Network response body failed");
  }
  return schema.parse(body);
}

// ---------------------------------------------------------------------------
// Typed accessors
// ---------------------------------------------------------------------------

export function getOperationalStatus(server = false) {
  return getOperational("/status", operationalStatusSchema, server);
}
export function getOperationalYears(server = false) {
  return getOperational("/years", operationalYearsSchema, server);
}
export function getOperationalAvailability(year: OperationalYear, server = false) {
  return getOperational(`/${year}/availability`, operationalAvailabilitySchema, server);
}
export function getOperationalCases(
  year: OperationalYear,
  filters: { page?: number; pageSize?: number; leadHours?: number } = {},
  server = false,
) {
  const params = new URLSearchParams();
  if (filters.page) params.set("page", String(filters.page));
  if (filters.pageSize) params.set("page_size", String(filters.pageSize));
  if (filters.leadHours) params.set("lead_hours", String(filters.leadHours));
  const query = params.toString();
  return getOperational(`/${year}/cases${query ? `?${query}` : ""}`, operationalCasesResponseSchema, server);
}
export function getOperationalCase(year: OperationalYear, caseId: string, server = false) {
  return getOperational(`/${year}/cases/${caseId}`, operationalCaseDetailSchema, server);
}
export function getOperationalRainfall(year: OperationalYear, caseId: string, field: string, server = false) {
  return getOperational(`/${year}/cases/${caseId}/rainfall?field=${field}`, operationalGridFieldSchema, server);
}
export function getOperationalAtmosphere(year: OperationalYear, caseId: string, field: string, server = false) {
  return getOperational(`/${year}/cases/${caseId}/atmosphere/${field}`, operationalAtmosphericFieldSchema, server);
}
export function getOperationalProbability(year: OperationalYear, caseId: string, target: "heavy" | "very_heavy", server = false) {
  return getOperational(`/${year}/cases/${caseId}/probability/${target}`, operationalProbabilityFieldSchema, server);
}
export function getOperationalRegime(year: OperationalYear, caseId: string, server = false) {
  return getOperational(`/${year}/cases/${caseId}/regime`, operationalRegimeSchema, server);
}
export function getOperationalRegimeSummary(year: OperationalYear, server = false) {
  return getOperational(`/${year}/regimes`, operationalRegimeSummarySchema, server);
}
export function getOperationalEnsemble(year: OperationalYear, caseId: string, server = false) {
  return getOperational(`/${year}/cases/${caseId}/ensemble`, operationalEnsembleSchema, server);
}
export function getOperationalDeterministicMetrics(year: OperationalYear, server = false) {
  return getOperational(`/${year}/metrics/deterministic`, operationalDeterministicMetricsSchema, server);
}
export function getOperationalProbabilityMetrics(year: OperationalYear, server = false) {
  return getOperational(`/${year}/metrics/probability`, operationalProbabilityMetricsSchema, server);
}
export function getOperationalFSS(year: OperationalYear, server = false) {
  return getOperational(`/${year}/metrics/fss`, operationalFssSchema, server);
}
export function getOperationalEnsembleMetrics(year: OperationalYear, server = false) {
  return getOperational(`/${year}/metrics/ensemble`, operationalEnsembleMetricsSchema, server);
}
export function getOperationalQuality(server = false) {
  return getOperational("/quality", operationalQualitySchema, server);
}
export function getOperationalProvenance(server = false) {
  return getOperational("/provenance", operationalProvenanceSchema, server);
}
