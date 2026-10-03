// Typed, Zod-validated client for the read-only, hash-verified experimental cycle bundles at /api/science/live/* (docs/139).
// Never invents a value: a lead the worker withheld is not served, and an absent live cycle is stated, not simulated.
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const LIVE_FIELDS = ["M0", "M1", "M2", "M3", "M4", "heavy_probability", "very_heavy_probability"] as const;
export type LiveFieldName = (typeof LIVE_FIELDS)[number];

const summary = z.object({
  kind: z.enum(["live", "replay"]), cycle: z.string().regex(/^\d{8}$/), initialization: z.string(), label: z.string(), created_at_utc: z.string(), age_days: z.number(), stale: z.boolean(),
  products: z.array(z.string()), withheld_products: z.record(z.string(), z.string()),
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
  kind: z.enum(["live", "replay"]), cycle: z.string(), product: z.string(), field: z.string(), label: z.string(), evidence_label: z.string(), units: z.string(),
  latitude: z.array(z.number()).length(49), longitude: z.array(z.number()).length(49), values: z.array(z.array(z.number()).length(49)).length(49), array_sha256: z.string().length(64),
});
export type LiveField = z.infer<typeof liveFieldSchema>;

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
