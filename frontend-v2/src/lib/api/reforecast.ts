// Typed, Zod-validated client for the read-only, hash-verified reforecast study at /api/science/evidence/reforecast/* (docs/142): the heavy-rain model comparison (R05) and the regime-detection tasks (R03)
// on the sealed years 2014-2016. Same conventions as ./coastal-regime.ts: same-origin proxy, structured {code, detail} errors, never inventing a value (an unsupported task carries a tier, not a number).
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const R05_MODELS = ["M0", "B0", "B1", "R_hard", "R_soft"] as const;
export const R03_TASKS = ["ACTIVE", "BREAK", "LOW_DEPRESSION", "WESTERN_DISTURBANCE", "COASTAL_OROGRAPHIC"] as const;
const nullableNumber = z.number().nullable();
const interval = z.object({ status: z.string(), point: nullableNumber.optional(), interval95: z.tuple([z.number(), z.number()]).optional(), excludes_zero: z.boolean().optional() }).passthrough().nullable();
const threshold = z.object({ hits: z.number(), misses: z.number(), false_alarms: z.number(), observed_events: z.number(), csi: nullableNumber, frequency_bias: nullableNumber });
const metrics = z.object({ rmse_mm: z.number(), mae_mm: z.number(), bias_mm: z.number(), cells: z.number(), heavy: threshold, very_heavy: threshold });
const decision = z.object({ IMPROVES_RMSE: z.boolean(), IMPROVES_HEAVY: z.boolean(), IMPROVES_VERY_HEAVY: z.boolean(), BIAS_OK: z.boolean(), improvements: z.array(z.string()), tier: z.string() });

export const reforecastOverviewSchema = z.object({
  protocol_sha256: z.string().length(64), manifest_sha256: z.string().length(64), purpose: z.string(), populations: z.object({ train_years: z.array(z.number()), validation_years: z.array(z.number()), sealed_test_years: z.array(z.number()) }).passthrough(),
  r05: z.object({ grid_size: z.number() }).passthrough(), r03: z.object({ tasks: z.record(z.string(), z.string()), label_nature: z.string() }).passthrough(),
  selection: z.object({ selection: z.record(z.string(), z.unknown()) }).passthrough(), regime_tasks_selection: z.object({ tasks: z.record(z.string(), z.record(z.string(), z.unknown())) }),
  unseal_record: z.object({ written_at_utc: z.string(), years: z.array(z.number()), what_is_not_authorised: z.array(z.string()) }).passthrough(), evidence_label: z.string(), caveats: z.array(z.string()),
}).passthrough();
export type ReforecastOverview = z.infer<typeof reforecastOverviewSchema>;

export const r05ResultSchema = z.object({
  evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64), protocol_sha256: z.string().length(64),
  payload: z.object({
    cases: z.number(), initialization_dates: z.number(), rows: z.number(), pooled: z.record(z.string(), metrics), support: z.object({ observed_event_pairs: z.record(z.string(), z.number()), supported: z.record(z.string(), z.boolean()) }),
    selected_configurations: z.record(z.string(), z.record(z.string(), z.unknown())),
    decisions: z.record(z.string(), z.object({ vs_raw: z.record(z.string(), interval), decision })),
    bundle_decisions: z.record(z.string(), z.object({ vs_raw: z.record(z.string(), interval), decision, components: z.string() })),
    exceedance: z.record(z.string(), z.object({ tau: z.number(), auc: nullableNumber, brier_score: z.number(), base_rate: z.number(), test: z.object({ hits: z.number(), misses: z.number(), false_alarms: z.number(), observed_events: z.number(), csi: nullableNumber, frequency_bias: nullableNumber }) }).passthrough()),
    raw_categorical: z.record(z.string(), z.object({ csi: nullableNumber, frequency_bias: nullableNumber })),
    regime_decisions: z.record(z.string(), z.object({ vs_b0: z.record(z.string(), interval), adds_value: z.object({ adds_value: z.boolean(), heavy_csi_improves: z.boolean(), rmse_not_worse_than_0_2_mm: z.boolean() }) }).passthrough()),
    by_lead: z.record(z.string(), z.record(z.string(), metrics)), reproduction: z.object({ status: z.string() }).passthrough(),
  }).passthrough(),
  caveats: z.array(z.string()),
});
export type R05Result = z.infer<typeof r05ResultSchema>;

export const confirmationResultSchema = z.object({
  evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64), protocol_sha256: z.string().length(64),
  payload: z.object({
    cases: z.number(), initialization_dates: z.number(), rows: z.number(), delta_mm: z.number(), delta_source: z.string(), pooled: z.record(z.string(), metrics),
    exceedance: z.record(z.string(), z.object({ tau: z.number(), test: z.object({ hits: z.number(), misses: z.number(), false_alarms: z.number(), observed_events: z.number(), csi: nullableNumber, frequency_bias: nullableNumber }) })),
    raw_categorical: z.record(z.string(), z.object({ csi: nullableNumber, frequency_bias: nullableNumber })), support: z.object({ observed_event_pairs: z.record(z.string(), z.number()), supported: z.record(z.string(), z.boolean()) }),
    bundle_decision: z.object({ vs_raw: z.record(z.string(), interval), decision, components: z.string() }), reproduction: z.object({ status: z.string() }).passthrough(),
  }).passthrough(),
  caveats: z.array(z.string()),
});
export type ConfirmationResult = z.infer<typeof confirmationResultSchema>;

const task = z.object({
  cases: z.number(), positives: z.number(), negatives: z.number(), tier: z.string(), validated: z.boolean(), useful: z.boolean(), reason: z.string().optional(),
  auc: interval.optional(), balanced_accuracy: interval.optional(), auc_over_baseline: interval.optional(), baseline_auc: nullableNumber.optional(),
}).passthrough();
export const r03ResultSchema = z.object({
  evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64), protocol_sha256: z.string().length(64),
  payload: z.object({ label_nature: z.string(), tasks: z.record(z.string(), task) }).passthrough(), caveats: z.array(z.string()),
});
export type R03Result = z.infer<typeof r03ResultSchema>;

async function getReforecast<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/reforecast/${path}`, { cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Reforecast study request failed (${response.status})`;
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

export const getReforecastOverview = (server = false) => getReforecast("overview", reforecastOverviewSchema, server);
export const getR05Result = (server = false) => getReforecast("r05", r05ResultSchema, server);
export const getR03Result = (server = false) => getReforecast("r03", r03ResultSchema, server);

export const getR05Confirmation = (server = false) => getReforecast("r05-confirmation", confirmationResultSchema, server);
