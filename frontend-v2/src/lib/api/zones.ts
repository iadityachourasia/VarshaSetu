// Typed, Zod-validated client for the read-only, hash-verified coastal/orographic zone evidence at
// /api/science/evidence/zones/* (docs/115-118). Same conventions as ./evidence.ts: same-origin proxy,
// structured {code, detail} errors, and never inventing a value (an unsupported stratum carries a status, not a number).
import { z } from "zod";
import { EvidenceApiError } from "./evidence";

export const ZONE_NAMES = ["COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER"] as const;
export type ZoneName = (typeof ZONE_NAMES)[number];
export const ZONE_LABEL: Record<ZoneName, string> = {
  COASTAL: "Coastal", OROGRAPHIC: "Orographic", COASTAL_AND_OROGRAPHIC: "Coastal and orographic (Ghats coast)", OTHER: "Other (interior)",
};
export const STRATA = ["weak", "middle", "strong"] as const;
export const FORCING_KEYS = ["COASTAL|onshore", "OROGRAPHIC|cross_barrier", "COASTAL_AND_OROGRAPHIC|onshore", "COASTAL_AND_OROGRAPHIC|cross_barrier"] as const;
export type ZoneTrackYear = { track: "A" | "B"; year: number };

const nullableNumber = z.number().nullable();
const heavyBlock = z.object({
  status: z.string().optional(), observed_event_pairs: z.number().optional(),
  hits: z.number().optional(), misses: z.number().optional(), false_alarms: z.number().optional(), observed_event_count: z.number().optional(),
  forecast_event_count: z.number().optional(), frequency_bias: nullableNumber.optional(),
  POD: nullableNumber.optional(), FAR: nullableNumber.optional(), CSI: nullableNumber.optional(), ETS: nullableNumber.optional(),
}).passthrough();
const modelBlock = z.object({
  cell_count: z.number(), status: z.string().optional(),
  rmse_mm: nullableNumber.optional(), mae_mm: nullableNumber.optional(), bias_mm: nullableNumber.optional(),
  categorical: z.object({ heavy: heavyBlock.optional(), very_heavy: heavyBlock.optional() }).passthrough().optional(),
}).passthrough();
const differenceStat = z.object({
  status: z.string(), point: nullableNumber.optional(), interval95: z.tuple([z.number(), z.number()]).optional(), excludes_zero: z.boolean().optional(),
  in_decision_rule: z.boolean().optional(),
}).passthrough();
const differenceTable = z.record(z.string(), z.record(z.string(), z.record(z.string(), differenceStat)));

const zoneMeta = z.object({
  track: z.enum(["A", "B"]), year: z.number(), evidence_role: z.string(), evidence_label: z.string(), evidence_sha256: z.string().length(64), caveats: z.array(z.string()),
});

export const zoneVerificationSchema = zoneMeta.extend({
  stage: z.literal("stage1"),
  payload: z.object({
    case_count: z.number(), models: z.array(z.string()),
    zones: z.record(z.string(), z.object({ cells: z.number(), in_decision_rule: z.boolean() })),
    support: z.record(z.string(), z.object({
      cells: z.number(), cases: z.number(), continuous_supported: z.boolean(),
      heavy: z.object({ observed_event_pairs: z.number(), supported: z.boolean() }),
      very_heavy: z.object({ observed_event_pairs: z.number(), supported: z.boolean() }),
    })),
    pooled: z.record(z.string(), z.record(z.string(), modelBlock)),
    differences: z.object({ q1: differenceTable, q2: differenceTable }),
    reproduction: z.object({ status: z.string(), max_abs_diff: z.number() }).passthrough(),
    bootstrap: z.object({ repeats: z.number(), seed: z.number(), note: z.string() }).passthrough(),
    fss: z.object({ status: z.string(), reason: z.string() }),
  }).passthrough(),
});
export type ZoneVerification = z.infer<typeof zoneVerificationSchema>;

export const zoneForcingSchema = zoneMeta.extend({
  stage: z.literal("stage2"),
  payload: z.object({
    case_count: z.number(), models: z.array(z.string()),
    forcing_cut_points: z.object({
      year: z.number(), cases_used: z.number(),
      cut_points: z.record(z.string(), z.object({ q33: z.number(), q67: z.number(), pairs: z.number(), degenerate: z.boolean() })),
    }),
    support: z.record(z.string(), z.object({
      cell_case_pairs: z.number(), cases: z.number(), heavy_observed_event_pairs: z.number(), continuous_supported: z.boolean(), heavy_supported: z.boolean(),
    })),
    pooled: z.record(z.string(), z.record(z.string(), modelBlock)),
    q3: differenceTable,
    reproduction: z.object({ status: z.string() }).passthrough(),
    forcing_inputs: z.object({ fields: z.array(z.string()), observations_read: z.boolean() }),
  }).passthrough(),
});
export type ZoneForcing = z.infer<typeof zoneForcingSchema>;

const trackSummary = z.object({
  development_year: z.number(), final_test_year: z.number(), tests: z.number(), development_significant: z.number(),
  expected_development_significant_by_chance: z.number(), expected_gaps_by_chance: z.number(), caveat: z.string(),
  geographic_gaps: z.number().optional(), forcing_gaps: z.number().optional(),
}).passthrough();

export const zoneOverviewSchema = z.object({
  protocol_sha256: z.string().length(64), spec_sha256: z.string().length(64), geography_sha256: z.string().length(64),
  stage1_manifest_sha256: z.string().length(64), stage2_manifest_sha256: z.string().length(64),
  status: z.string(), stage_3_authorised: z.boolean(), stage_3_recommended_by_pre_registered_rule: z.boolean(),
  available: z.array(z.object({ track: z.enum(["A", "B"]), year: z.number(), evidence_role: z.string(), evidence_label: z.string(), cases: z.number() })),
  decision_stage1: z.object({ rule: z.string(), tracks: z.record(z.string(), trackSummary) }).passthrough(),
  decision_stage2: z.object({ rule: z.string(), tracks: z.record(z.string(), trackSummary) }).passthrough(),
  caveats: z.array(z.string()),
});
export type ZoneOverview = z.infer<typeof zoneOverviewSchema>;

export const zoneGeographySchema = z.object({
  source: z.object({ file: z.string(), distribution: z.string(), attribution: z.string(), original: z.string() }).passthrough(),
  grid: z.object({ latitude_centers: z.array(z.number()), longitude_centers: z.array(z.number()) }).passthrough(),
  qa: z.object({ criteria_met: z.boolean(), footprint_cells: z.number() }).passthrough(),
  zone_cell_counts: z.record(z.string(), z.number()),
  zone_notes: z.record(z.string(), z.string()),
  sensitivity_only_counts: z.record(z.string(), z.unknown()),
  fields: z.object({
    zone: z.array(z.array(z.string().nullable())),
    mean_elevation_m: z.array(z.array(z.number().nullable())),
    local_relief_m: z.array(z.array(z.number().nullable())),
    distance_to_coast_km: z.array(z.array(z.number().nullable())),
  }).passthrough(),
  geography_sha256: z.string().length(64),
  caveats: z.array(z.string()),
});
export type ZoneGeography = z.infer<typeof zoneGeographySchema>;

async function getZones<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  let response: Response;
  try {
    response = await fetch(`${base}/api/science/evidence/zones/${path}`, { cache: server ? "no-store" : "default", signal: AbortSignal.timeout(server ? 25_000 : 20_000) });
  } catch (error) {
    throw new EvidenceApiError(error instanceof Error ? error.message : "Network request failed", null, null);
  }
  if (!response.ok) {
    let code: string | null = null;
    let detail = `Zone evidence request failed (${response.status})`;
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

export const getZoneOverview = (server = false) => getZones("overview", zoneOverviewSchema, server);
export const getZoneGeography = (server = false) => getZones("geography", zoneGeographySchema, server);
export const getZoneVerification = ({ track, year }: ZoneTrackYear, server = false) => getZones(`verification?track=${track}&year=${year}`, zoneVerificationSchema, server);
export const getZoneForcing = ({ track, year }: ZoneTrackYear, server = false) => getZones(`forcing?track=${track}&year=${year}`, zoneForcingSchema, server);
