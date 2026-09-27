import { z } from "zod";

const provenanceSchema = z.object({
  corpus_version: z.string(),
  deterministic_model: z.string(),
  deterministic_model_sha256: z.string(),
  probability_freeze_sha256: z.string(),
  artifact_manifest_sha256: z.string(),
  prototype_only: z.boolean(),
});

const caseSchema = z.object({
  case_id: z.string(),
  initialization_utc: z.string(),
  valid_period_start_utc: z.string(),
  valid_period_end_utc: z.string(),
  lead_hours: z.number(),
  product: z.string(),
  dominant_regime: z.string(),
  regime_probabilities: z.record(z.string(), z.number()),
  raw_rmse_mm: z.number(),
  corrected_rmse_mm: z.number(),
  mean_heavy_probability: z.number(),
  mean_very_heavy_probability: z.number(),
  observed_heavy_cells: z.number(),
  observed_very_heavy_cells: z.number(),
});

const gridSchema = z.object({
  crs: z.literal("EPSG:4326"),
  shape: z.tuple([z.number().int().positive(), z.number().int().positive()]),
  latitude_centers: z.array(z.number()),
  longitude_centers: z.array(z.number()),
  cell_size_degrees: z.number().positive(),
  bounds_west_south_east_north: z.tuple([z.number(), z.number(), z.number(), z.number()]),
  row_order: z.literal("south_to_north"),
  column_order: z.literal("west_to_east"),
  mask_policy: z.string(),
});

const matrix = z.array(z.array(z.number().nullable()));
const maskMatrix = z.array(z.array(z.boolean()));
const payloadBase = z.object({
  case_id: z.string(),
  initialization_utc: z.string(),
  lead_hours: z.number(),
  product: z.string(),
  valid_period_start_utc: z.string(),
  valid_period_end_utc: z.string(),
  provenance: provenanceSchema,
});

export const statusSchema = z.object({
  readiness_state: z.string(),
  operational_ready: z.boolean(),
  case_count: z.number(),
  district_count: z.number(),
  provenance: provenanceSchema,
});
export const casesSchema = z.object({ cases: z.array(caseSchema), provenance: provenanceSchema });
export const demoCasesSchema = z.object({
  selection: z.string(),
  cases: z.array(caseSchema),
  catalogue_sha256: z.string(),
  provenance: provenanceSchema,
});
export const caseDetailSchema = payloadBase.extend({ data: caseSchema.passthrough() });
export const rainfallSchema = payloadBase.extend({
  data: z.object({
    raw: matrix, corrected: matrix, observed: matrix, valid_mask: maskMatrix,
    unit: z.literal("mm/24h"), grid: gridSchema,
  }),
});
export const probabilitiesSchema = payloadBase.extend({
  data: z.object({
    heavy_probability: matrix,
    very_heavy_probability: matrix,
    thresholds_mm_24h: z.object({ heavy: z.number(), very_heavy: z.number() }),
    grid: gridSchema,
  }),
});
export const regimeSchema = payloadBase.extend({
  data: z.object({
    probabilities: z.record(z.string(), z.number()),
    dominant_regime: z.string(),
    label_status: z.string(),
  }),
});
const fssScore = z.object({ fss: z.number().nullable(), case_count: z.number(), reason: z.string().nullable() });
const fssPair = z.object({ raw: fssScore, corrected: fssScore });
const caseFssScore = z.object({ fss: z.number().nullable(), valid_centers: z.number(), reason: z.string().nullable() });
export const fssSchema = payloadBase.extend({
  data: z.record(z.string(), z.record(z.string(), z.object({ raw: caseFssScore, corrected: caseFssScore }))),
});

export const districtSchema = z.object({
  district_id: z.string(), district_name: z.string(),
  raw_mean_mm: z.number(), corrected_mean_mm: z.number(), corrected_max_mm: z.number(),
  heavy_probability: z.number(), very_heavy_probability: z.number(),
  heavy_area_fraction: z.number(), very_heavy_area_fraction: z.number(),
  dominant_regime: z.string(), valid_grid_cells: z.number(),
});
export const districtsSchema = payloadBase.extend({
  data: z.object({ districts: z.array(districtSchema), aggregation: z.string(), geometry_source: z.string() }),
});
export const geometrySchema = z.object({
  geometry: z.object({
    type: z.literal("FeatureCollection"),
    features: z.array(z.object({
      type: z.literal("Feature"),
      properties: z.object({ district_id: z.string(), district_name: z.string() }),
      geometry: z.unknown(),
    })),
  }),
  geometry_sha256: z.string(), source: z.string(), license: z.string(),
  provenance: provenanceSchema,
});

const continuous = z.object({ rmse_mm: z.number(), mae_mm: z.number(), bias_mm: z.number(), sample_count: z.number() });
const eventMetrics = z.object({ POD: z.number().nullable(), FAR: z.number().nullable(), CSI: z.number().nullable(), ETS: z.number().nullable() });
const threshold = z.object({ metrics: eventMetrics, observed_event_count: z.number(), sample_count: z.number() }).passthrough();
export const modelComparisonSchema = z.object({
  results: z.record(z.string(), z.object({
    overall: z.object({ continuous, thresholds: z.object({ heavy_64_5: threshold, very_heavy_115_6: threshold }) }),
    same_case_count: z.number(), same_cell_count: z.number(),
  }).passthrough()),
  test_year: z.literal(2019), results_sha256: z.string(), provenance: provenanceSchema,
});

const reliabilityBin = z.object({
  bin_lower: z.number(), bin_upper: z.number(), sample_count: z.number(),
  mean_predicted_probability: z.number().nullable(), observed_event_frequency: z.number().nullable(),
});
const probabilityMetrics = z.object({
  brier: z.number().nullable(), bss: z.number().nullable(), pr_auc: z.number().nullable(),
  roc_auc: z.number().nullable(), observed_event_count: z.number(), sample_count: z.number(),
  reliability: z.array(reliabilityBin),
  categorical: z.object({ metrics: eventMetrics, observed_event_count: z.number(), sample_count: z.number(), decision_threshold_probability: z.number() }).passthrough(),
  undefined_reasons: z.record(z.string(), z.string()),
});
export const verificationSchema = z.object({
  metrics: z.object({
    case_count: z.number(), cell_count: z.number(), district_count: z.number(),
    fss: z.record(z.string(), z.record(z.string(), fssPair)),
    targets: z.object({ heavy: probabilityMetrics, very_heavy: probabilityMetrics }),
  }).passthrough(),
  provenance: provenanceSchema,
});

export type CaseSummary = z.infer<typeof caseSchema>;
export type Rainfall = z.infer<typeof rainfallSchema>;
export type Probabilities = z.infer<typeof probabilitiesSchema>;
export type District = z.infer<typeof districtSchema>;
export type Grid = z.infer<typeof gridSchema>;
export type Verification = z.infer<typeof verificationSchema>;
export type ModelComparison = z.infer<typeof modelComparisonSchema>;
export type Geometry = z.infer<typeof geometrySchema>;

export async function getScience<T>(path: string, schema: z.ZodType<T>, server = false): Promise<T> {
  const base = server ? (process.env.SCIENCE_API_URL ?? "http://127.0.0.1:8000") : "";
  const response = await fetch(`${base}/api/science${path}`, {
    cache: server ? "no-store" : "default",
    signal: AbortSignal.timeout(server ? 25_000 : 20_000),
  });
  if (!response.ok) throw new Error(response.status === 404 ? "Historical case not found" : "Scientific artifacts are unavailable");
  return schema.parse(await response.json());
}
