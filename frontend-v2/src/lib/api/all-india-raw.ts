// Typed, Zod-validated client for the read-only, hash-verified Raw GEFS verification over the whole IMD grid at /api/science/evidence/all-india-raw/* (docs/140).
// Same conventions as ./coastal-regime.ts: same-origin proxy, structured {code, detail} errors, and never inventing a value (an unsupported region carries a status, not a number).
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const ALL_INDIA_YEARS = [2023, 2024, 2025] as const;
export const ALL_INDIA_REGIONS = ["ALL_INDIA", "INSIDE_MODEL_DOMAIN", "NORTH_OF_DOMAIN", "EAST_AND_NORTH_EAST", "EAST_COAST_PENINSULA", "SOUTH_OF_DOMAIN"] as const;
export type AllIndiaRegion = (typeof ALL_INDIA_REGIONS)[number];
const nullableNumber = z.number().nullable();
const interval = z.object({ status: z.string(), point: nullableNumber.optional(), interval95: z.tuple([z.number(), z.number()]).optional(), excludes_zero: z.boolean().optional() }).passthrough();
const categorical = z.union([
  z.object({ hits: z.number(), misses: z.number(), false_alarms: z.number(), observed_event_count: z.number(), forecast_event_count: z.number(), CSI: nullableNumber, POD: nullableNumber, FAR: nullableNumber, frequency_bias: nullableNumber }).passthrough(),
  z.object({ status: z.literal("insufficient_support"), observed_event_pairs: z.number() }),
]);
const regionBlock = z.object({ cell_count: z.number(), cases: z.number(), continuous_supported: z.boolean(), rmse_mm: z.number().optional(), mae_mm: z.number().optional(), bias_mm: z.number().optional(),
  categorical: z.object({ heavy: categorical, very_heavy: categorical }) });
const regionRecord = <T extends z.ZodTypeAny>(schema: T) => z.object({ ALL_INDIA: schema, INSIDE_MODEL_DOMAIN: schema, NORTH_OF_DOMAIN: schema, EAST_AND_NORTH_EAST: schema, EAST_COAST_PENINSULA: schema, SOUTH_OF_DOMAIN: schema });

export const allIndiaOverviewSchema = z.object({
  protocol_sha256: z.string().length(64), manifest_sha256: z.string().length(64), ledger_sha256: z.string().length(64), status: z.string(), purpose: z.string(),
  definition: z.object({ forecast: z.string(), observation: z.string(), grid: z.string(), regions: z.object({ cell_counts: z.record(z.string(), z.number()), note: z.string() }).passthrough() }).passthrough(),
  evaluation: z.object({ uncertainty_note: z.string() }).passthrough(), decision_rule: z.string(), not_established: z.array(z.string()),
  available: z.array(z.object({ year: z.number(), evidence_role: z.string(), evidence_label: z.string(), cases_scored: z.number(), development: z.boolean() })), caveats: z.array(z.string()),
}).passthrough();
export type AllIndiaOverview = z.infer<typeof allIndiaOverviewSchema>;

export const allIndiaResultSchema = z.object({
  year: z.number(), evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64), protocol_sha256: z.string().length(64),
  payload: z.object({
    cases_scored: z.number(), initialization_dates: z.number(), excluded_cases: z.record(z.string(), z.number()), region_cells_with_observation: z.record(z.string(), z.number()),
    metrics: regionRecord(regionBlock), bootstrap: z.object({ intervals: regionRecord(z.record(z.string(), interval)) }).passthrough(), by_lead: z.record(z.string(), z.record(z.string(), z.object({ rmse_mm: nullableNumber, bias_mm: nullableNumber, cell_count: z.number() }))),
    reproduction: z.object({ status: z.string() }).passthrough(), forecast_nature: z.string(),
  }).passthrough(),
  caveats: z.array(z.string()),
});
export type AllIndiaResult = z.infer<typeof allIndiaResultSchema>;

async function getAllIndia<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/all-india-raw/${path}`, { cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `All-India Raw verification request failed (${response.status})`;
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

export const getAllIndiaOverview = (server = false) => getAllIndia("overview", allIndiaOverviewSchema, server);
export const getAllIndiaResult = (year: number, server = false) => getAllIndia(`result?year=${year}`, allIndiaResultSchema, server);
