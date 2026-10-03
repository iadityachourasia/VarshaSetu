// Typed, Zod-validated client for the read-only, hash-verified geography-aware (M5a) experiment evidence at
// /api/science/evidence/geoaware/* (docs/124, docs/126). Same conventions as ./zones.ts: same-origin proxy, structured
// {code, detail} errors, and never inventing a value (an unsupported stratum carries a status, not a number).
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

const nullableNumber = z.number().nullable();
const heavyBlock = z.object({
  status: z.string().optional(), CSI: nullableNumber.optional(), POD: nullableNumber.optional(), FAR: nullableNumber.optional(),
  frequency_bias: nullableNumber.optional(),
}).passthrough();
const modelBlock = z.object({
  cell_count: z.number(), status: z.string().optional(),
  rmse_mm: nullableNumber.optional(), bias_mm: nullableNumber.optional(),
  categorical: z.object({ heavy: heavyBlock.optional() }).passthrough().optional(),
}).passthrough();
const differenceStat = z.object({
  status: z.string(), point: nullableNumber.optional(), interval95: z.tuple([z.number(), z.number()]).optional(), excludes_zero: z.boolean().optional(),
}).passthrough();

const yearDecision = z.object({
  csi_beats_M2: z.boolean(), rmse_within_tolerance: z.boolean(), guardrails_pass: z.boolean(),
  guardrails_G1_G2_G3: z.object({ G1: z.boolean(), G2: z.boolean(), G3: z.boolean() }),
  heavy_csi_zone_A3_minus_M2: differenceStat, overall_rmse_A3_minus_M2: differenceStat,
}).passthrough();

const arm = z.object({ selected: z.object({ grid_index: z.number(), features: z.number(), guardrails: z.record(z.string(), z.boolean()) }).passthrough().nullable(), reason: z.string().optional() }).passthrough();

export const geoawareOverviewSchema = z.object({
  protocol_sha256: z.string().length(64), selection_freeze_sha256: z.string().length(64), manifest_sha256: z.string().length(64),
  status: z.string(),
  approval: z.object({ option_D1: z.string() }).passthrough(),
  decision: z.object({
    adds_value: z.boolean(), candidate: z.string(), wording: z.string(), protocol_gap: z.string().nullable(),
    sign_agrees_2024_2025: z.boolean(), coverage_status_consequence: z.string(),
    geography_attribution: z.null(),
    per_year: z.record(z.string(), yearDecision),
  }).passthrough(),
  selection: z.record(z.string(), arm),
  training: z.object({ cases: z.number(), rows: z.number() }).passthrough(),
  configurations: z.array(z.object({ arm: z.string(), passes_guardrails: z.boolean() }).passthrough()),
  arms: z.record(z.string(), z.array(z.string())),
  available: z.array(z.object({ year: z.number(), evidence_role: z.string(), evidence_label: z.string(), cases: z.number() })),
  caveats: z.array(z.string()),
});
export type GeoawareOverview = z.infer<typeof geoawareOverviewSchema>;

export const geoawareEvaluationSchema = z.object({
  year: z.number(), evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64),
  payload: z.object({
    case_count: z.number(), models: z.array(z.string()), limits: z.array(z.string()),
    support: z.record(z.string(), z.object({ continuous_supported: z.boolean(), heavy: z.object({ observed_event_pairs: z.number(), supported: z.boolean() }) }).passthrough()),
    pooled: z.record(z.string(), z.record(z.string(), modelBlock)),
    comparisons: z.record(z.string(), z.record(z.string(), z.record(z.string(), differenceStat))),
    reproduction: z.object({ status: z.string() }).passthrough(),
    bootstrap: z.object({ repeats: z.number(), seed: z.number() }).passthrough(),
    guardrails_on_evaluation_population: z.record(z.string(), z.record(z.string(), z.boolean())),
  }).passthrough(),
  caveats: z.array(z.string()),
});
export type GeoawareEvaluation = z.infer<typeof geoawareEvaluationSchema>;

async function getGeoaware<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/geoaware/${path}`, { cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Geography-aware evidence request failed (${response.status})`;
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

export const getGeoawareOverview = (server = false) => getGeoaware("overview", geoawareOverviewSchema, server);
export const getGeoawareEvaluation = (year: number, server = false) => getGeoaware(`evaluation?year=${year}`, geoawareEvaluationSchema, server);

const byYear = z.record(z.string(), z.object({
  rmse_mm: z.number(), bias_mm: z.number(), heavy_csi: nullableNumber, zone_heavy_csi: nullableNumber, zone_heavy_frequency_bias: nullableNumber,
  very_heavy_frequency_bias: nullableNumber,
}));
const selectedModel = z.object({
  grid_index: z.number(), config: z.object({ objective: z.string(), weights: z.string(), max_depth: z.number(), n_estimators: z.number() }),
  pooled_rmse_mm: z.number(), features: z.number(), g3_passes_in_every_year: z.boolean(), by_year: byYear,
});
const intervalStat = z.object({
  status: z.string(), point: nullableNumber.optional(), interval: z.tuple([z.number(), z.number()]).optional(), level: z.number().optional(), excludes_zero: z.boolean().optional(),
}).passthrough();
const testDecision = z.object({
  candidate: z.string(), comparator: z.string(), status: z.string(), adds_value: z.boolean().nullable(),
  P1_zone_heavy_csi_beats_comparator_975: z.boolean().nullable().optional(), P2_overall_rmse_within_tolerance: z.boolean().nullable().optional(),
  P3_gating_guardrails_G1_G2_G4: z.boolean().nullable().optional(), guardrails: z.record(z.string(), z.boolean()).optional(), g3_reported_only: z.boolean().optional(),
  zone_heavy_csi_difference: intervalStat.optional(), overall_rmse_difference: intervalStat.optional(), level: z.number().optional(),
});
const pooledSummary = z.object({
  rmse_mm: z.number(), bias_mm: z.number(), heavy_csi: nullableNumber, very_heavy_frequency_bias: nullableNumber,
  zone_heavy_csi: nullableNumber, zone_heavy_frequency_bias: nullableNumber, zone_bias_mm: z.number(),
});

export const geoawareFollowupSchema = z.object({
  protocol_v1_sha256: z.string().length(64), protocol_v2_sha256: z.string().length(64), protocol_v3_sha256: z.string().length(64),
  freeze_v1_sha256: z.string().length(64), freeze_v2_sha256: z.string().length(64), freeze_v3_sha256: z.string().length(64),
  summary_sha256: z.string().length(64), unseal_record_sha256: z.string().length(64), test_result_sha256: z.string().length(64),
  sealed_test: z.object({ year: z.number(), opened: z.boolean(), status: z.string(), sealed_at_selection_freezes: z.boolean() }).passthrough(),
  unseal_record: z.object({
    written_at_utc: z.string(), owner_message: z.object({ verbatim: z.string(), interpretation: z.string() }).passthrough(),
    what_is_not_authorised: z.array(z.string()), disclosed_before_opening: z.array(z.string()), hashes_listed: z.number(),
  }).passthrough(),
  approval: z.object({ interpretation: z.string(), unseal: z.string() }).passthrough(),
  contamination_disclosure: z.string(),
  changes: z.array(z.object({ id: z.string(), what: z.string(), why: z.string() }).passthrough()),
  post_hoc_disclosure: z.object({ decided_after: z.string(), consequence: z.string(), no_threshold_was_tuned: z.string() }).passthrough(),
  decision_rule: z.object({ adds_value_requires_all: z.array(z.string()) }).passthrough(),
  development_years: z.array(z.number()),
  v1_outcome: z.object({ all_arms_without_candidate: z.boolean() }).passthrough(),
  v2_selection: z.record(z.string(), selectedModel.nullable()),
  v3_selection: z.record(z.string(), selectedModel.nullable()),
  eligible_v2_by_arm: z.record(z.string(), z.number()),
  raw_heavy_csi_by_year: z.record(z.string(), z.number()),
  matched_configuration_comparison: z.object({ configurations: z.number(), zone_heavy_csi_higher_in_every_held_out_year: z.number(), pooled_rmse_lower: z.number() }),
  test_2022: z.object({
    label: z.string(), claim: z.string(), claim_wording: z.string(), cases: z.number(), run_at_utc: z.string(), multiplicity: z.string(),
    support_zone: z.object({ cells: z.number(), cases: z.number(), heavy: z.object({ observed_event_pairs: z.number(), supported: z.boolean() }) }).passthrough(),
    candidate_sets: z.record(z.string(), z.object({ candidate: z.string(), comparator: z.string() })),
    models: z.record(z.string(), z.object({ arm: z.string(), grid_index: z.number(), config: z.object({ objective: z.string(), weights: z.string(), max_depth: z.number(), n_estimators: z.number() }) }).passthrough()),
    pooled_summary: z.record(z.string(), pooledSummary),
    decisions: z.record(z.string(), testDecision),
    sensitivity: z.array(z.object({ a: z.string(), b: z.string(), zone_heavy_csi_difference: intervalStat.nullable() })),
    by_lead: z.record(z.string(), z.object({ cases: z.number(), models: z.record(z.string(), z.object({ rmse_mm: z.number(), zone_heavy_csi: nullableNumber })) })),
    limits: z.array(z.string()),
  }),
  caveats: z.array(z.string()),
});
export type GeoawareFollowup = z.infer<typeof geoawareFollowupSchema>;
export const getGeoawareFollowup = (server = false) => getGeoaware("followup", geoawareFollowupSchema, server);
