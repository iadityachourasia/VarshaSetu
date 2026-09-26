import { z } from "zod";
import type { Grid } from "@/lib/api/science";

const caseSummarySchema = z.object({
  case_id: z.string(), year: z.union([z.literal(2023), z.literal(2024), z.literal(2025)]),
  role: z.string(), initialization_utc: z.string(), lead_hours: z.number(),
  valid_observation_date: z.string(), heavy_cells: z.number(), very_heavy_cells: z.number(),
  max_observed_mm: z.number(), regime_probabilities: z.tuple([z.number(), z.number(), z.number()]),
  has_ensemble: z.boolean(), models: z.array(z.string()), has_probabilities: z.boolean(),
  frozen_case_metrics: z.object({ raw_rmse_mm: z.number(), M1_rmse_mm: z.number(), M1_minus_raw_rmse_mm: z.number() }).nullable(),
  artifact: z.string().regex(/^cases\/20(?:23|24|25)\/20\d{6}_day[123]_24h\.json$/),
});
const indexSchema = z.object({
  schema: z.literal("phase5a-operational-index-v1"), experiment: z.literal("historical_operational_gefs"),
  grid: z.object({
    crs: z.literal("EPSG:4326"), shape: z.tuple([z.literal(49), z.literal(49)]),
    latitude_centers: z.array(z.number()).length(49), longitude_centers: z.array(z.number()).length(49),
    cell_size_degrees: z.literal(0.25), bounds_west_south_east_north: z.tuple([z.number(), z.number(), z.number(), z.number()]),
    row_order: z.literal("south_to_north"), column_order: z.literal("west_to_east"), mask_policy: z.string(),
  }),
  pixel_indices: z.array(z.number().int().min(0).max(2400)).length(1301),
  cases: z.array(caseSummarySchema).length(615), source_hashes: z.record(z.string(), z.string()),
});
const values = z.array(z.number().finite()).length(1301);
const caseSchema = z.object({
  schema: z.literal("phase5a-operational-case-v1"), case_id: z.string(), year: z.number(),
  source: z.literal("historical_operational_gefs"), role: z.string(), initialization_utc: z.string(),
  lead_hours: z.number(), product: z.string(), valid_observation_date: z.string(), row_count: z.literal(1301),
  fields: z.record(z.string(), values), atmosphere: z.record(z.string(), values),
  regime_probabilities: z.tuple([z.number(), z.number(), z.number()]),
  probabilities: z.object({ heavy: values, very_heavy: values }).nullable(),
  frozen_case_metrics: caseSummarySchema.shape.frozen_case_metrics,
  ensemble_members: z.record(z.string(), values).nullable(),
});

export type OperationalIndex = z.infer<typeof indexSchema>;
export type OperationalCaseSummary = z.infer<typeof caseSummarySchema>;
export type OperationalCase = z.infer<typeof caseSchema>;
export type OperationalField = (number | null)[][];

const base = "/science/operational-v1";

async function getFrozen<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(`${base}/${path}`, { cache: "force-cache" });
  if (!response.ok) throw new Error("Frozen historical presentation artifact unavailable");
  return schema.parse(await response.json());
}

export function getOperationalIndex(): Promise<OperationalIndex> {
  return getFrozen("index.json", indexSchema);
}

export async function getOperationalCase(summary: OperationalCaseSummary): Promise<OperationalCase> {
  const result = await getFrozen(summary.artifact, caseSchema);
  if (result.case_id !== summary.case_id || result.year !== summary.year) throw new Error("Case lineage mismatch");
  return result;
}

export function expandedField(index: OperationalIndex, values: number[]): OperationalField {
  if (values.length !== index.pixel_indices.length) throw new Error("Frozen field length differs from paired mask");
  const matrix: OperationalField = Array.from({ length: 49 }, () => Array<number | null>(49).fill(null));
  for (let point = 0; point < values.length; point++) {
    const flat = index.pixel_indices[point];
    matrix[Math.floor(flat / 49)][flat % 49] = values[point];
  }
  return matrix;
}

export function operationalMask(index: OperationalIndex): boolean[][] {
  const matrix = Array.from({ length: 49 }, () => Array<boolean>(49).fill(false));
  for (const flat of index.pixel_indices) matrix[Math.floor(flat / 49)][flat % 49] = true;
  return matrix;
}

export function operationalGrid(index: OperationalIndex): Grid {
  return index.grid;
}

export const experimentSeasons = [
  { year: 2017, experiment: "reforecast", role: "TRAINING", maps: false },
  { year: 2018, experiment: "reforecast", role: "VALIDATION", maps: false },
  { year: 2019, experiment: "reforecast", role: "FINAL HISTORICAL TEST", maps: true },
  { year: 2023, experiment: "operational", role: "TRAINING / CROSS-FIT", maps: true },
  { year: 2024, experiment: "operational", role: "VALIDATION / MODEL SELECTION", maps: true },
  { year: 2025, experiment: "operational", role: "FINAL HISTORICAL TEST — COMPLETED", maps: true },
] as const;
