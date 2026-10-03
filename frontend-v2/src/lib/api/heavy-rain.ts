// Typed, Zod-validated client for the read-only, hash-verified heavy-rain bundle layer (B1) at /api/science/heavy-rain/* (docs/143): the frozen B1 regression and the two frozen exceedance classifiers
// shown on the 2019 cases of the existing product. Same conventions as ./reforecast.ts: same-origin proxy, structured {code, detail} errors, and never an invented value.
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

const nullableNumber = z.number().nullable();
const matrix = z.array(z.array(nullableNumber));
const categoricalSchema = z.object({ tau: z.number(), hits: z.number(), misses: z.number(), false_alarms: z.number(), observed_events: z.number(), csi: nullableNumber, frequency_bias: nullableNumber, pod: nullableNumber.optional(), far: nullableNumber.optional() });
const categoricalSummary = z.object({ csi: nullableNumber, frequency_bias: nullableNumber }).passthrough();
const rainfallStats = z.object({ rmse_mm: z.number(), mae_mm: z.number(), bias_mm: z.number(), cells: z.number(), heavy: categoricalSummary.optional(), very_heavy: categoricalSummary.optional() }).passthrough();

export const heavyRainOverviewSchema = z.object({
  year: z.number(), cases: z.number(), evidence_label: z.string(), bundle_label: z.string(), shift_mm: z.number(), bias_guardrail_mm: z.number(), slice_bias_within_limit: z.boolean(),
  thresholds_mm: z.record(z.string(), z.number()), decision_thresholds: z.record(z.string(), z.number()),
  protocol_sha256: z.string().length(64), manifest_sha256: z.string().length(64), arrays_sha256: z.string().length(64),
  summary: z.object({ cases: z.number(), cells: z.number(), rainfall: z.object({ M0: rainfallStats, M2: rainfallStats, B1: rainfallStats }), classifier: z.object({ heavy: categoricalSchema, very_heavy: categoricalSchema }) }).passthrough(),
  confirmation: z.object({
    label: z.string(), years: z.array(z.number()), cases: z.number(), tier: z.string(), bias_within_limit: z.boolean(), delta_source: z.string(),
    pooled: z.object({ M0: rainfallStats, B1_shifted: rainfallStats }).passthrough(), exceedance: z.record(z.string(), categoricalSchema),
  }).passthrough(),
  caveats: z.array(z.string()),
});
export type HeavyRainOverview = z.infer<typeof heavyRainOverviewSchema>;

export const heavyRainCaseSchema = z.object({
  case_id: z.string(), year: z.number(), b1_rainfall_mm: matrix, heavy_score: matrix, very_heavy_score: matrix, heavy_decision: matrix, very_heavy_decision: matrix,
  decision_thresholds: z.record(z.string(), z.number()), b1_rmse_mm: z.number(), evidence_label: z.string(), caveats: z.array(z.string()),
});
export type HeavyRainCase = z.infer<typeof heavyRainCaseSchema>;

const districtRow = z.object({
  district_id: z.string(), district_name: z.string(), valid_grid_cells: z.number(),
  raw_mean_mm: z.number(), corrected_mean_mm: z.number(), corrected_max_mm: z.number(),
  heavy_probability: z.number(), very_heavy_probability: z.number(), heavy_flag_area_fraction: z.number(), very_heavy_flag_area_fraction: z.number(),
  heavy_area_fraction: z.number(), very_heavy_area_fraction: z.number(), dominant_regime: z.string().nullable().optional(),
}).passthrough();
export const heavyRainDistrictsSchema = z.object({ case_id: z.string(), year: z.number(), districts: z.array(districtRow), aggregation: z.string(), decision_thresholds: z.record(z.string(), z.number()), evidence_label: z.string(), caveats: z.array(z.string()) });
export type HeavyRainDistricts = z.infer<typeof heavyRainDistrictsSchema>;

async function getHeavyRain<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/science/heavy-rain/${path}`, { cache: "default", signal: AbortSignal.timeout(25_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Heavy-rain layer request failed (${response.status})`;
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

export const getHeavyRainOverview = () => getHeavyRain("overview", heavyRainOverviewSchema);
export const getHeavyRainCase = (caseId: string) => getHeavyRain(`cases/${encodeURIComponent(caseId)}`, heavyRainCaseSchema);
export const getHeavyRainDistricts = (caseId: string) => getHeavyRain(`cases/${encodeURIComponent(caseId)}/districts`, heavyRainDistrictsSchema);
