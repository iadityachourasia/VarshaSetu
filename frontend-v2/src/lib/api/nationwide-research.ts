import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const NATIONAL_FIELDS = ["M0", "M1", "M2", "M3", "M4", "heavy_p", "very_heavy_p"] as const;
export type NationalField = (typeof NATIONAL_FIELDS)[number];
const hash = z.string().length(64);
const probabilityStatus = z.literal("RESEARCH_METHOD_AUDIT_FAILED_RELIABILITY_UNVALIDATED");
const metric = z.object({ rmse_mm: z.number(), heavy_csi: z.number().nullable(), very_heavy_csi: z.number().nullable() });
const support = z.object({ cases: z.number(), paired_cells: z.number(), heavy_observed: z.number(), very_heavy_observed: z.number() });

export const nationwideOverviewSchema = z.object({
  status: z.literal("CONSUMED_2024_DEVELOPMENT_RESEARCH_ONLY"), source_track: z.literal("B_OPERATIONAL_GEFS"),
  year: z.literal(2024), cases: z.number(), paired_cells: z.number(), model_default: z.literal("regional_M2"),
  m2_selection_passed: z.boolean(), nationwide_promotion_eligible: z.literal(false), geometry_status: z.string(), probability_status: probabilityStatus,
  protocol_sha256: hash, score_sha256: hash, uncertainty_sha256: hash,
  models: z.object({ M0: metric, M1: metric, M2: metric, M3: metric, M4: metric }),
  regional_gate: z.record(z.string(), z.object({ M0_heavy_csi: z.number().nullable(), M2_heavy_csi: z.number().nullable(),
    M2_minus_raw_ci95: z.tuple([z.number(), z.number()]).nullable(), event_support: support })),
  caveat: z.string(),
});
export type NationwideOverview = z.infer<typeof nationwideOverviewSchema>;

const eventScores = z.object({ CSI: z.number().nullable(), ETS: z.number().nullable(), FAR: z.number().nullable(), POD: z.number().nullable() });
const eventVerification = z.object({ hits: z.number().int(), false_alarms: z.number().int(), misses: z.number().int(),
  observed_event_count: z.number().int(), forecast_event_count: z.number().int(), sample_count: z.number().int(),
  threshold_mm_24h: z.number(), metrics: eventScores, undefined_metric_reasons: z.record(z.string(), z.string()), undefined_reason: z.string().nullable() });
const continuousVerification = z.object({ bias_mm: z.number(), mae_mm: z.number(), rmse_mm: z.number(), sample_count: z.number().int() });
const fssVerification = z.object({ case_count: z.number().int(), fss: z.number().nullable(), reason: z.string().nullable() });
const modelVerification = z.object({ cases: z.number().int(), cells: z.number().int(), metrics: z.object({
  continuous: continuousVerification, heavy: eventVerification, very_heavy: eventVerification }),
  fss: z.object({ heavy: z.record(z.string(), fssVerification), very_heavy: z.record(z.string(), fssVerification) }) });
const dateBlockUncertainty = z.object({ defined_bootstrap_repeats: z.record(z.string(), z.number().int()), event_support_gate: z.boolean(),
  heavy_csi: z.number().nullable(), heavy_csi_delta_ci95: z.array(z.number()).length(2).nullable(), heavy_csi_minus_raw: z.number().nullable(),
  rmse_delta_ci95: z.array(z.number()).length(2).nullable(), rmse_minus_raw: z.number().nullable(), rmse_mm: z.number(),
  support: z.object({ cases: z.number().int(), paired_cells: z.number().int(), heavy_observed: z.number().int(), very_heavy_observed: z.number().int() }) });
export const nationwideVerificationSchema = z.object({
  status: z.literal("CONSUMED_2024_DEVELOPMENT_RESEARCH_ONLY"), source_track: z.literal("B_OPERATIONAL_GEFS"),
  reference: z.literal("IMD_RF25_03_TO_03_UTC"), region: z.string(), lead_hours: z.union([z.literal(0), z.literal(24), z.literal(48), z.literal(72)]),
  paired_cases: z.number().int(), paired_cells: z.number().int(),
  models: z.object({ M0: modelVerification, M1: modelVerification, M2: modelVerification, M3: modelVerification, M4: modelVerification }),
  uncertainty: z.object({ M0: dateBlockUncertainty, M1: dateBlockUncertainty, M2: dateBlockUncertainty, M3: dateBlockUncertainty, M4: dateBlockUncertainty }),
  protocol_sha256: hash, score_sha256: hash, uncertainty_sha256: hash, independent_skill_claim: z.literal(false), caveat: z.string(),
});
export type NationwideVerification = z.infer<typeof nationwideVerificationSchema>;

export const nationwideCasesSchema = z.object({ year: z.literal(2024), status: z.literal("CONSUMED_DEVELOPMENT_ONLY"), seal_sha256: hash,
  cases: z.array(z.object({ case_id: z.string(), lead_hours: z.union([z.literal(24), z.literal(48), z.literal(72)]), available_locally: z.boolean() })) });
export type NationwideCases = z.infer<typeof nationwideCasesSchema>;

const nationalGrid = z.object({ crs: z.literal("EPSG:4326"), shape: z.tuple([z.literal(129), z.literal(135)]),
  latitude_centers: z.array(z.number()).length(129), longitude_centers: z.array(z.number()).length(135),
  cell_size_degrees: z.literal(0.25), bounds_west_south_east_north: z.tuple([z.number(), z.number(), z.number(), z.number()]),
  row_order: z.literal("south_to_north"), column_order: z.literal("west_to_east"), mask_policy: z.string() });
export const nationwideGridSchema = z.object({
  case_id: z.string(), year: z.literal(2024), source_track: z.literal("B_OPERATIONAL_GEFS"),
  status: z.literal("CONSUMED_2024_DEVELOPMENT_RESEARCH_ONLY"), field: z.enum(NATIONAL_FIELDS),
  units: z.enum(["mm per 24 h", "probability"]), probability_status: probabilityStatus.nullable(), accumulation_window_hours: z.tuple([z.number(), z.number()]),
  grid: nationalGrid, values: z.array(z.array(z.number().nullable()).length(135)).length(129),
  valid_mask: z.array(z.array(z.boolean()).length(135)).length(129), valid_cells: z.number(),
  prediction_sha256: hash, fit_seal_sha256: hash, caveat: z.string(),
});
export type NationwideGrid = z.infer<typeof nationwideGridSchema>;

export const nationwideDistrictsSchema = z.object({ case_id: z.string(), status: z.literal("LOCAL_RESEARCH_GEOMETRY_ONLY_NOT_OFFICIAL"),
  districts: z.array(z.object({ district_id: z.string(), district_name: z.string(), weighted_grid_coverage_fraction: z.number(), supported: z.boolean(),
    M0: z.number().nullable(), M1: z.number().nullable(), M2: z.number().nullable(), M3: z.number().nullable(), M4: z.number().nullable(),
    heavy_p: z.number().nullable(), very_heavy_p: z.number().nullable() })),
  table_sha256: hash, coverage_rule: z.string(), caveat: z.string() });
export type NationwideDistricts = z.infer<typeof nationwideDistrictsSchema>;

async function request<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  let response: Response;
  try { response = await fetch(`/api/science/research/nationwide/${path}`, { signal: AbortSignal.timeout(25_000) }); }
  catch (error) { throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null); }
  if (!response.ok) {
    let detail = `Nationwide research request failed (${response.status})`;
    let code: string | null = null;
    try { const body = await response.json() as { detail?: unknown; code?: unknown }; if (typeof body.detail === "string") detail = body.detail; if (typeof body.code === "string") code = body.code; } catch { /* Keep HTTP status. */ }
    throw new EvidenceApiError(detail, response.status, code);
  }
  return schema.parse(await response.json());
}

export const getNationwideOverview = () => request("overview", nationwideOverviewSchema);
export const getNationwideVerification = (region: string, leadHours: 0 | 24 | 48 | 72) => request(`verification?region=${encodeURIComponent(region)}&lead_hours=${leadHours}`, nationwideVerificationSchema);
export const getNationwideCases = () => request("cases", nationwideCasesSchema);
export const getNationwideGrid = (caseId: string, field: NationalField) => request(`grid?case_id=${encodeURIComponent(caseId)}&field=${field}`, nationwideGridSchema);
export const getNationwideDistricts = (caseId: string) => request(`districts?case_id=${encodeURIComponent(caseId)}`, nationwideDistrictsSchema);
