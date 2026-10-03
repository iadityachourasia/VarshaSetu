// Typed, Zod-validated client for the read-only, hash-verified forecast-time coastal/orographic forcing regime at /api/science/evidence/coastal-regime/* (docs/137).
// Same conventions as ./zones.ts: same-origin proxy, structured {code, detail} errors, and never inventing a value (an unsupported population carries a status, not a number).
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const COASTAL_YEARS = [2018, 2019, 2024, 2025] as const;
export const COASTAL_CLASSES = ["WEAK", "MODERATE", "STRONG"] as const;
export type CoastalClass = (typeof COASTAL_CLASSES)[number];
const nullableNumber = z.number().nullable();
const interval = z.object({ status: z.string(), point: nullableNumber.optional(), interval95: z.tuple([z.number(), z.number()]).optional(), excludes_zero: z.boolean().optional() }).passthrough();

const group = z.object({
  cases: z.number(), heavy_event_pairs: z.number(), share_of_all_heavy_event_pairs: nullableNumber, mean_heavy_fraction: nullableNumber, share_of_cases_with_a_heavy_cell: nullableNumber,
});

export const coastalOverviewSchema = z.object({
  protocol_sha256: z.string().length(64), manifest_sha256: z.string().length(64), cases_file_sha256: z.string().length(64), status: z.string(), purpose: z.string(),
  definition: z.object({ index: z.string(), classes: z.string(), cut_points: z.record(z.string(), z.object({ q33: z.number(), q67: z.number(), training_year: z.number(), training_cases: z.number() })) }).passthrough(),
  decision: z.object({ discriminates: z.boolean(), rule: z.string(), wording: z.string() }),
  available: z.array(z.object({ track: z.enum(["A", "B"]), year: z.number(), evidence_role: z.string(), evidence_label: z.string(), cases: z.number(), development: z.boolean() })),
  caveats: z.array(z.string()),
}).passthrough();
export type CoastalOverview = z.infer<typeof coastalOverviewSchema>;

export const coastalResultSchema = z.object({
  track: z.enum(["A", "B"]), year: z.number(), evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64), protocol_sha256: z.string().length(64),
  payload: z.object({
    cases: z.number(), observed_heavy_event_pairs: z.number(), supported: z.boolean(), groups: z.object({ WEAK: group, MODERATE: group, STRONG: group }),
    discrimination: z.union([z.object({ strong_minus_weak_heavy_fraction: interval, spearman: interval }).passthrough(), z.object({ status: z.literal("insufficient_support") })]),
    regime_nature: z.string(), reproduction: z.object({ status: z.string() }).passthrough(),
  }).passthrough(),
  caveats: z.array(z.string()),
});
export type CoastalResult = z.infer<typeof coastalResultSchema>;

export const coastalCasesSchema = z.object({
  track: z.enum(["A", "B"]), year: z.number(), evidence_label: z.string(), cases_file_sha256: z.string().length(64),
  cut_points: z.object({ q33: z.number(), q67: z.number(), training_year: z.number() }).passthrough(),
  cases: z.array(z.object({ case_id: z.string(), index: nullableNumber, class: z.enum(["WEAK", "MODERATE", "STRONG"]).nullable(), percentile_vs_training: nullableNumber, lead_day: z.number() })),
  caveats: z.array(z.string()),
});
export type CoastalCases = z.infer<typeof coastalCasesSchema>;

async function getCoastal<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/coastal-regime/${path}`, { cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Coastal regime request failed (${response.status})`;
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

export const getCoastalOverview = (server = false) => getCoastal("overview", coastalOverviewSchema, server);
export const getCoastalResult = (year: number, server = false) => getCoastal(`result?year=${year}`, coastalResultSchema, server);
export const getCoastalCases = (year: number, server = false) => getCoastal(`cases?year=${year}`, coastalCasesSchema, server);
