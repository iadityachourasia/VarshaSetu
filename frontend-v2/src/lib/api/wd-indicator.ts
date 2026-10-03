// Typed, Zod-validated client for the read-only, hash-verified forecast-time western-disturbance indicator at /api/science/evidence/wd-indicator/* (docs/138).
// Same conventions as ./coastal-regime.ts: same-origin proxy, structured {code, detail} errors, and never inventing a value (an unsupported population carries a status, not a number).
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const WD_YEARS = [2021, 2022, 2024, 2025] as const;
const nullableNumber = z.number().nullable();
const interval = z.object({ status: z.string(), point: nullableNumber.optional(), interval95: z.tuple([z.number(), z.number()]).optional(), excludes_zero: z.boolean().optional() }).passthrough();
const group = z.object({ cases: z.number(), mean_rain_mm_per_day: nullableNumber, share_of_cases_with_rain_at_least_1mm: nullableNumber });

export const wdOverviewSchema = z.object({
  protocol_sha256: z.string().length(64), manifest_sha256: z.string().length(64), cases_file_sha256: z.string().length(64), status: z.string(), purpose: z.string(),
  definition: z.object({ indicator: z.string(), flag: z.string(), training_year: z.number(), threshold: z.object({ threshold: z.number(), training_cases: z.number() }).passthrough() }).passthrough(),
  evaluation: z.object({ observed_quantity: z.string() }).passthrough(),
  decision: z.object({ associated: z.boolean(), rule: z.string(), wording: z.string() }),
  not_established: z.array(z.string()),
  available: z.array(z.object({ year: z.number(), evidence_role: z.string(), evidence_label: z.string(), cases_scored: z.number(), development: z.boolean() })),
  caveats: z.array(z.string()),
}).passthrough();
export type WdOverview = z.infer<typeof wdOverviewSchema>;

export const wdResultSchema = z.object({
  year: z.number(), evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64), protocol_sha256: z.string().length(64),
  payload: z.object({
    cases_scored: z.number(), supported: z.boolean(), development: z.boolean(), groups: z.object({ flagged: group, not_flagged: group }),
    association: z.union([z.object({ flagged_minus_not_flagged_mean_rain: interval, spearman: interval }).passthrough(), z.object({ status: z.literal("insufficient_support") })]),
    indicator_nature: z.string(), reproduction: z.object({ status: z.string() }).passthrough(),
  }).passthrough(),
  caveats: z.array(z.string()),
});
export type WdResult = z.infer<typeof wdResultSchema>;

export const wdCasesSchema = z.object({
  year: z.number(), evidence_label: z.string(), cases_file_sha256: z.string().length(64),
  threshold: z.object({ threshold: z.number(), training_cases: z.number() }).passthrough(),
  cases: z.array(z.object({ case_id: z.string(), initialization: z.string(), lead_day: z.number(), index: nullableNumber, flag: z.boolean().nullable() })),
  caveats: z.array(z.string()),
});
export type WdCases = z.infer<typeof wdCasesSchema>;

async function getWd<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/wd-indicator/${path}`, { cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Western-disturbance indicator request failed (${response.status})`;
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

export const getWdOverview = (server = false) => getWd("overview", wdOverviewSchema, server);
export const getWdResult = (year: number, server = false) => getWd(`result?year=${year}`, wdResultSchema, server);
export const getWdCases = (year: number, server = false) => getWd(`cases?year=${year}`, wdCasesSchema, server);
