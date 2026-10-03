// Typed, Zod-validated client for the read-only, hash-verified independent check of the regime classifier at /api/science/evidence/regime-validation/* (docs/136).
// Same conventions as ./zones.ts and ./geoaware.ts: same-origin proxy, structured {code, detail} errors, and never inventing a value (an unsupported task carries a status, not a number).
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const VALIDATION_YEARS = [2018, 2019, 2024, 2025] as const;
export const OBSERVED_STATES = ["ACTIVE", "BREAK", "NEUTRAL"] as const;
const nullableNumber = z.number().nullable();
const countsByState = z.object({ ACTIVE: z.number(), BREAK: z.number(), NEUTRAL: z.number() });

export const regimeValidationOverviewSchema = z.object({
  protocol_sha256: z.string().length(64), manifest_sha256: z.string().length(64), status: z.string(), purpose: z.string(),
  criteria: z.object({
    not_the_published_classification: z.boolean(), deviations_from_the_published_work: z.array(z.string()), threshold_sd: z.number(), min_spell_days: z.number(),
    label_window_months: z.array(z.number()), core_zone_box: z.object({ lat: z.array(z.number()), lon: z.array(z.number()) }),
    climatology: z.object({ years: z.array(z.number()), files: z.number(), sigma_mm_per_day: z.number() }).passthrough(),
  }).passthrough(),
  tasks: z.record(z.string(), z.string()),
  support_gate: z.object({ min_cases_per_side: z.number() }).passthrough(),
  observation_only_counts: z.record(z.string(), z.object({
    labelled_days: countsByState, cases_by_observed_state: countsByState, cases_with_labelled_valid_day: z.number(), supported: z.object({ ACTIVE: z.boolean(), BREAK: z.boolean() }),
  }).passthrough()),
  approval: z.object({ note: z.string() }).passthrough(),
  available: z.array(z.object({ track: z.enum(["A", "B"]), year: z.number(), evidence_role: z.string(), evidence_label: z.string(), cases_labelled: z.number() })),
  caveats: z.array(z.string()),
});
export type RegimeValidationOverview = z.infer<typeof regimeValidationOverviewSchema>;

const scoredTask = z.object({
  status: z.literal("scored"), hits: z.number(), misses: z.number(), false_alarms: z.number(), correct_negatives: z.number(),
  recall: nullableNumber, specificity: nullableNumber, precision: nullableNumber, balanced_accuracy: nullableNumber, f1: nullableNumber, base_rate: nullableNumber,
  balanced_accuracy_bootstrap: z.object({ interval95: z.tuple([z.number(), z.number()]) }).passthrough().nullable(),
}).passthrough();
const unsupportedTask = z.object({ status: z.literal("insufficient_support"), observed_cases: z.number(), note: z.string() });
const task = z.discriminatedUnion("status", [scoredTask, unsupportedTask]);

export const regimeValidationResultSchema = z.object({
  track: z.enum(["A", "B"]), year: z.number(), evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64), protocol_sha256: z.string().length(64),
  payload: z.object({
    cases_listed: z.number(), cases_labelled: z.number(), observed_state_counts: countsByState,
    confusion_predicted_class_by_observed_state: z.record(z.string(), countsByState),
    tasks: z.object({ active_vs_not_active: task, break_vs_not_break: task }),
    depression: z.string(), pseudo_label_agreement_is_separate: z.boolean(),
    reproduction: z.object({ status: z.string() }).passthrough(),
  }).passthrough(),
  caveats: z.array(z.string()),
});
export type RegimeValidationResult = z.infer<typeof regimeValidationResultSchema>;

async function getValidation<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/regime-validation/${path}`, { cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Regime validation request failed (${response.status})`;
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

export const getRegimeValidationOverview = (server = false) => getValidation("overview", regimeValidationOverviewSchema, server);
export const getRegimeValidationResult = (year: number, server = false) => getValidation(`result?year=${year}`, regimeValidationResultSchema, server);
