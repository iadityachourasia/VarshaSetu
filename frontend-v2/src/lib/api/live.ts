// Typed, Zod-validated client for the read-only, hash-verified experimental cycle bundles at /api/science/live/* (docs/139).
// Never invents a value: a lead the worker withheld is not served, and an absent live cycle is stated, not simulated.
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const LIVE_FIELDS = ["M0", "M1", "M2", "M3", "M4", "heavy_probability", "very_heavy_probability"] as const;
export type LiveFieldName = (typeof LIVE_FIELDS)[number];

const summary = z.object({
  kind: z.enum(["live", "replay"]), cycle: z.string().regex(/^\d{8}$/), initialization: z.string(), label: z.string(), created_at_utc: z.string(), age_days: z.number(), stale: z.boolean(),
  products: z.array(z.string()), withheld_products: z.record(z.string(), z.string()),
  season_scope: z.enum(["JJAS_RESEARCH_SCOPE", "OUTSIDE_JJAS_RESEARCH_SCOPE"]),
});
export type LiveSummary = z.infer<typeof summary>;

export const liveStatusSchema = z.object({ has_live_cycle: z.boolean(), latest_live: summary.nullable(), cycles: z.array(summary), message: z.string(), caveats: z.array(z.string()) });
export type LiveStatus = z.infer<typeof liveStatusSchema>;

const stat = z.object({ min: z.number(), max: z.number(), mean: z.number() });
export const liveCycleSchema = z.object({
  summary, manifest_sha256: z.string().length(64), messages: z.number(), transferred_bytes: z.number(), frozen_models: z.record(z.string(), z.string()),
  applicability: z.object({ status: z.string(), largest_share: z.object({ share: z.number(), product: z.string(), feature: z.string() }).optional() }).passthrough().nullable(),
  replay_comparison: z.object({ date: z.string(), products: z.record(z.string(), z.record(z.string(), z.number())) }).passthrough().nullable(),
  regime_probabilities: z.record(z.string(), z.record(z.string(), z.number())),
  domain_statistics: z.record(z.string(), z.record(z.string(), stat)),
  fields: z.record(z.string(), z.string()), observation_read: z.literal(false), caveats: z.array(z.string()),
});
export type LiveCycle = z.infer<typeof liveCycleSchema>;

export const liveFieldSchema = z.object({
  schema_version: z.literal("live_field_v2"),
  kind: z.enum(["live", "replay"]), cycle: z.string(), product: z.string(), field: z.string(), label: z.string(), evidence_label: z.string(), units: z.string(),
  latitude: z.array(z.number()).length(49), longitude: z.array(z.number()).length(49), values: z.array(z.array(z.number()).length(49)).length(49), array_sha256: z.string().length(64),
  source_track: z.literal("B_OPERATIONAL_GEFS"), model_id: z.enum(LIVE_FIELDS), initialization_utc: z.string(),
  accumulation_window_hours: z.tuple([z.number(), z.number()]), lead_hours: z.union([z.literal(24), z.literal(48), z.literal(72)]), valid_mask: z.array(z.array(z.boolean()).length(49)).length(49),
  valid_cells: z.number().int().min(0).max(49 * 49), mask_policy: z.string(), evidence_manifest_sha256: z.string().length(64),
  probability_status: z.literal("RESEARCH_ONLY_RELIABILITY_UNVERIFIED").nullable(),
}).superRefine((value, ctx) => {
  if ((value.units === "probability") !== (value.probability_status !== null)) {
    ctx.addIssue({ code: "custom", message: "Probability status must match field units" });
  }
});
export type LiveField = z.infer<typeof liveFieldSchema>;

const districtRow = z.object({
  district_id: z.string(), district_name: z.string(), valid_grid_cells: z.number().int().positive(), weighted_grid_coverage_fraction: z.number().min(0.95).max(1),
  raw_mean_mm: z.number().nonnegative(), corrected_mean_mm: z.number().nonnegative(), corrected_max_mm: z.number().nonnegative(),
  heavy_probability: z.number().min(0).max(1), very_heavy_probability: z.number().min(0).max(1),
  heavy_area_fraction: z.number().min(0).max(1), very_heavy_area_fraction: z.number().min(0).max(1),
});
export const liveDistrictsSchema = z.object({
  schema_version: z.literal("live_district_v2"),
  kind: z.enum(["live", "replay"]), cycle: z.string().regex(/^\d{8}$/), product: z.string(), model_id: z.enum(["M1", "M2", "M3", "M4"]),
  source_track: z.literal("B_OPERATIONAL_GEFS"), label: z.string(), accumulation_window_hours: z.tuple([z.number(), z.number()]),
  lead_hours: z.union([z.literal(24), z.literal(48), z.literal(72)]), initialization_utc: z.string(),
  valid_mask: z.array(z.array(z.boolean()).length(49)).length(49), valid_cells: z.number().int().min(0).max(49 * 49),
  units: z.literal("mm per 24 h"), district_count: z.number().int().nonnegative(), withheld_district_count: z.number().int().nonnegative(), coverage_threshold_fraction: z.literal(0.95), district_coverage: z.literal("REGIONAL_ONLY_10_TO_22_N_68_TO_80_E"),
  season_scope: z.enum(["JJAS_RESEARCH_SCOPE", "OUTSIDE_JJAS_RESEARCH_SCOPE"]),
  geometry_sha256: z.string().length(64), weights_sha256: z.string().length(64), evidence_manifest_sha256: z.string().length(64),
  probability_status: z.literal("RESEARCH_ONLY_RELIABILITY_UNVERIFIED"),
  districts: z.array(districtRow), caveats: z.array(z.string()),
}).refine((value) => value.district_count === value.districts.length, { message: "District count does not match rows" });
export type LiveDistricts = z.infer<typeof liveDistrictsSchema>;

async function getLive<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/live/${path}`, { cache: "no-store", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Live cycle request failed (${response.status})`;
    try {
      const body = (await response.json()) as { code?: unknown; detail?: unknown };
      if (typeof body?.code === "string") code = body.code;
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // no JSON body; keep the generic message
    }
    throw new EvidenceApiError(detail, response.status, code);
  }
  return schema.parse(await response.json());
}

export const getLiveStatus = (server = false) => getLive("status", liveStatusSchema, server);
export const getLiveCycle = (kind: string, date: string, server = false) => getLive(`cycle?kind=${kind}&date=${date}`, liveCycleSchema, server);
export const getLiveField = (kind: string, date: string, product: string, field: string, server = false) =>
  getLive(`field?kind=${kind}&date=${date}&product=${product}&field=${field}`, liveFieldSchema, server);
export const getLiveDistricts = (kind: string, date: string, product: string, model: "M1" | "M2" | "M3" | "M4", server = false) =>
  getLive(`districts?kind=${kind}&date=${date}&product=${product}&model=${model}`, liveDistrictsSchema, server);
