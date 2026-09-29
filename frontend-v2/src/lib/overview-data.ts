import type { z } from "zod";
import { pairedCaseSeries, type BenchmarkPoint } from "../components/overview/benchmark-chart";
import type { casesSchema, modelComparisonSchema, statusSchema } from "./api/science";
import type { operationalCasesResponseSchema } from "./api/operational";
import operational2025 from "./benchmarks/operational-2025.json";
import reforecast2019 from "./benchmarks/reforecast-2019-overview.json";

type Status = z.infer<typeof statusSchema>;
type Comparison = z.infer<typeof modelComparisonSchema>;
type ReforecastCases = z.infer<typeof casesSchema>;
type OperationalCases = z.infer<typeof operationalCasesResponseSchema>;

export type OverviewBenchmark = {
  year: 2019 | 2025;
  caseCount: number;
  raw: number;
  corrected: number;
  reductionPercent: string;
  series: BenchmarkPoint[] | null;
};

export type Overview2019Source = "verified_api" | "verified_snapshot" | "unavailable";

const REFORECAST_MANIFEST_SHA256 = "31be2aa797c95364a3d5c04cd26b3a8294b33081d2baa3b0b17085ad63812d89";
const REFORECAST_PHASE2B_SHA256 = "df2ed9f24d1edf23b202e4afca08fbf989a7d0c91f6d6a9ff74a34511eee893c";
const REFORECAST_PHASE2C_SHA256 = "7ffee9e90d7c84d5c0a6810a7a2ccb7afce034803033322f3456c640bcf16aa4";

function validRmse(value: number) {
  return Number.isFinite(value) && value >= 0;
}

function benchmark(year: 2019 | 2025, caseCount: number, raw: number, corrected: number, series: BenchmarkPoint[] | null): OverviewBenchmark | null {
  if (!Number.isInteger(caseCount) || caseCount < 2 || !validRmse(raw) || !validRmse(corrected) || raw === 0) return null;
  return { year, caseCount, raw, corrected, reductionPercent: ((raw - corrected) / raw * 100).toFixed(2), series };
}

function reconcilesWithFrozenRmse(points: BenchmarkPoint[], raw: number, corrected: number) {
  // The frozen 2025 population has the same 1,301 paired cells in every case.
  const aggregate = (key: "raw" | "corrected") => Math.sqrt(points.reduce((sum, point) => sum + point[key] ** 2, 0) / points.length);
  return Math.abs(aggregate("raw") - raw) < 1e-6 && Math.abs(aggregate("corrected") - corrected) < 1e-6;
}

export function overview2019(status: Status | null, comparison: Comparison | null, cases: ReforecastCases | null): OverviewBenchmark | null {
  const rawResult = comparison?.results.M0_RAW_GEFS;
  const correctedResult = comparison?.results.M2_GLOBAL_XGBOOST;
  if (!status || !comparison || !rawResult || !correctedResult) return null;
  const count = status.case_count;
  if (comparison.test_year !== 2019 || rawResult.same_case_count !== count || correctedResult.same_case_count !== count) return null;
  if (status.provenance.artifact_manifest_sha256 !== comparison.provenance.artifact_manifest_sha256) return null;
  const series = cases && cases.provenance.artifact_manifest_sha256 === status.provenance.artifact_manifest_sha256
    ? pairedCaseSeries(cases.cases, count, 2019)
    : null;
  return benchmark(2019, count, rawResult.overall.continuous.rmse_mm, correctedResult.overall.continuous.rmse_mm, series);
}

export function overview2019Snapshot(): OverviewBenchmark | null {
  if (reforecast2019.artifact_manifest_sha256 !== REFORECAST_MANIFEST_SHA256
    || reforecast2019.phase2b_results_sha256 !== REFORECAST_PHASE2B_SHA256
    || reforecast2019.phase2c_results_sha256 !== REFORECAST_PHASE2C_SHA256) return null;
  const count = reforecast2019.case_count;
  const series = pairedCaseSeries(reforecast2019.cases, count, 2019);
  if (!series) return null;
  return benchmark(2019, count, reforecast2019.raw_rmse_mm, reforecast2019.corrected_rmse_mm, series);
}

function transportFailure(reason: unknown): boolean {
  return reason instanceof TypeError
    || reason instanceof DOMException && (reason.name === "TimeoutError" || reason.name === "AbortError");
}

/** A frozen snapshot is used only when an essential request cannot reach the API. */
export function resolve2019Overview(
  status: PromiseSettledResult<Status>,
  comparison: PromiseSettledResult<Comparison>,
  cases: PromiseSettledResult<ReforecastCases>,
): { benchmark: OverviewBenchmark | null; source: Overview2019Source; status: Status | null } {
  const liveStatus = status.status === "fulfilled" ? status.value : null;
  const liveComparison = comparison.status === "fulfilled" ? comparison.value : null;
  const liveCases = cases.status === "fulfilled" ? cases.value : null;
  if (liveStatus && liveComparison) {
    const benchmark = overview2019(liveStatus, liveComparison, liveCases);
    return { benchmark, source: benchmark ? "verified_api" : "unavailable", status: liveStatus };
  }
  const failures = [status, comparison, cases].filter((result) => result.status === "rejected");
  if (!failures.length || failures.some((result) => result.status === "rejected" && !transportFailure(result.reason))) {
    return { benchmark: null, source: "unavailable", status: liveStatus };
  }
  const expected = reforecast2019.artifact_manifest_sha256;
  if (liveStatus && liveStatus.provenance.artifact_manifest_sha256 !== expected
    || liveComparison && liveComparison.provenance.artifact_manifest_sha256 !== expected
    || liveCases && liveCases.provenance.artifact_manifest_sha256 !== expected) {
    return { benchmark: null, source: "unavailable", status: liveStatus };
  }
  const benchmark = overview2019Snapshot();
  return { benchmark, source: benchmark ? "verified_snapshot" : "unavailable", status: liveStatus };
}

export function overview2025(cases: OperationalCases | null): OverviewBenchmark | null {
  const { case_count: count, raw_rmse_mm: raw, selected_rmse_mm: corrected } = operational2025;
  if (operational2025.evaluation_year !== 2025 || operational2025.status !== "FINAL_TEST_COMPLETED") return null;
  const completeIndex = cases && cases.year === 2025 && cases.page === 1 && cases.total >= count
    && cases.cases.length === cases.total && cases.page_size >= cases.total;
  const eligibleCases = completeIndex ? cases.cases.filter((item) => item.deterministic_source_eligible) : [];
  const paired = eligibleCases.length === count && eligibleCases.every((item) => item.year_role === "FINAL_TEST_COMPLETED" && item.source_complete)
    ? pairedCaseSeries(eligibleCases.map((item) => ({
      case_id: item.case_id,
      initialization_utc: item.initialization_utc,
      raw_rmse_mm: item.raw_rmse_mm,
      corrected_rmse_mm: item.m1_rmse_mm,
      eligible: item.year === 2025,
    })), count, 2025)
    : null;
  const series = paired && reconcilesWithFrozenRmse(paired, raw, corrected) ? paired : null;
  return benchmark(2025, count, raw, corrected, series);
}
