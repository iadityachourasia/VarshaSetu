// Story Mode narrates frozen evidence; it must not carry typed scientific numbers (AGENTS.md 3.3). Every figure it shows is
// derived here from (a) the live, hash-verified /api/science/model-comparison for the 2019 benchmark and (b) the generated
// frozen presentation bundle (public/science/operational-v1) for the 2025 final test and the data-quality funnel.
// A value that cannot be derived is null, and the scene says so instead of showing a number.

import type { ConfirmationResult, R03Result, R05Result } from "@/lib/api/reforecast";
import type { PsCoverage } from "@/lib/api/evidence";

export type Benchmark = { rawRmse: number; correctedRmse: number; reductionPercent: number; cases: number };
export type StoryFacts = {
  benchmark2019: (Benchmark & { correctedLabel: string }) | null;
  final2025: (Benchmark & { correctedLabel: string }) | null;
  probability2025: { heavyBss: number; veryHeavyBss: number } | null;
  quality: { scheduled: number; c00Eligible: number; fiveMemberEligible: number } | null;
  coverage: CoverageFacts | null;
  regimeTasks: RegimeTaskFact[] | null;
  reforecast: ReforecastFacts | null;
};

export type CoverageFacts = { implemented: number; partial: number; planned: number; total: number; mandatoryImplemented: number; mandatoryTotal: number };
export type RegimeTaskFact = { key: string; label: string; cases: number; auc: number | null; verdict: string };
export type ReforecastRound = { rawRmse: number; correctedRmse: number; rawHeavyCsi: number | null; classifierHeavyCsi: number | null; classifierHeavyFrequencyBias: number | null; tier: string; cases: number; label: string; years: string | null };
export type ReforecastFacts = { round1: ReforecastRound; round2: ReforecastRound | null; regimeAddsValue: boolean | null };

type Comparison = { results: Record<string, { overall: { continuous: { rmse_mm: number } }; same_case_count: number }> };
type Final2025 = {
  case_count: number;
  deterministic: Record<string, { continuous: { rmse_mm: number } }>;
  probability: { heavy: { metrics: { bss: number } }; very_heavy: { metrics: { bss: number } } };
};
type Quality = { years: Record<string, { scheduled_cases: number; c00_source_qc_cases: number; full_five_member_cases: number }> };

const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

export function reduction(raw: number, corrected: number) {
  return ((raw - corrected) / raw) * 100;
}

function benchmark(raw: unknown, corrected: unknown, cases: unknown): Benchmark | null {
  if (!finite(raw) || !finite(corrected) || !finite(cases) || raw <= 0) return null;
  return { rawRmse: raw, correctedRmse: corrected, reductionPercent: reduction(raw, corrected), cases };
}

const REGIME_TASK_LABEL: Record<string, string> = { ACTIVE: "Active monsoon", BREAK: "Break monsoon", LOW_DEPRESSION: "Low / depression", WESTERN_DISTURBANCE: "Western disturbance", COASTAL_OROGRAPHIC: "Coastal / orographic" };
const REGIME_TASK_ORDER = ["ACTIVE", "BREAK", "LOW_DEPRESSION", "WESTERN_DISTURBANCE", "COASTAL_OROGRAPHIC"];

export function coverageFacts(coverage: PsCoverage | null | undefined): CoverageFacts | null {
  if (!coverage?.counts || !coverage.mandatory_counts) return null;
  const n = (record: Record<string, number>, key: string) => (finite(record[key]) ? record[key] : 0);
  const sum = (record: Record<string, number>) => Object.values(record).filter(finite).reduce((a, b) => a + b, 0);
  const total = sum(coverage.counts);
  if (total <= 0) return null;
  return { implemented: n(coverage.counts, "IMPLEMENTED"), partial: n(coverage.counts, "PARTIAL"), planned: n(coverage.counts, "PLANNED"), total, mandatoryImplemented: n(coverage.mandatory_counts, "IMPLEMENTED"), mandatoryTotal: sum(coverage.mandatory_counts) };
}

export function regimeTaskFacts(result: R03Result | null | undefined): RegimeTaskFact[] | null {
  const tasks = result?.payload?.tasks;
  if (!tasks) return null;
  const rows = REGIME_TASK_ORDER.filter((key) => tasks[key]).map((key) => {
    const task = tasks[key];
    const auc = task.auc && task.auc.status === "ok" && finite(task.auc.point) ? task.auc.point : null;
    const verdict = task.validated && task.useful ? "validated and useful" : task.validated ? "validated" : "not supported";
    return { key, label: REGIME_TASK_LABEL[key] ?? key, cases: task.cases, auc, verdict };
  });
  return rows.length ? rows : null;
}

/** The first and last year of a result, read from its by-year breakdown. */
function yearSpan(byYear: unknown): string | null {
  if (!byYear || typeof byYear !== "object") return null;
  const years = Object.keys(byYear).filter((key) => /^\d{4}$/.test(key)).sort();
  return years.length ? (years.length === 1 ? years[0] : `${years[0]}-${years[years.length - 1]}`) : null;
}

function round(rmse: { raw: unknown; corrected: unknown }, csi: { raw: unknown; classifier: unknown; bias: unknown }, tier: unknown, cases: unknown, label: unknown, years: unknown): ReforecastRound | null {
  if (!finite(rmse.raw) || !finite(rmse.corrected) || typeof tier !== "string" || !finite(cases) || typeof label !== "string") return null;
  return { rawRmse: rmse.raw, correctedRmse: rmse.corrected, rawHeavyCsi: finite(csi.raw) ? csi.raw : null, classifierHeavyCsi: finite(csi.classifier) ? csi.classifier : null, classifierHeavyFrequencyBias: finite(csi.bias) ? csi.bias : null, tier, cases, label, years: yearSpan(years) };
}

export function reforecastFacts(r05: R05Result | null | undefined, confirmation: ConfirmationResult | null | undefined): ReforecastFacts | null {
  const p = r05?.payload;
  if (!p) return null;
  const heavy = p.exceedance?.["B1:heavy"]?.test;
  const round1 = round({ raw: p.pooled?.M0?.rmse_mm, corrected: p.pooled?.B1?.rmse_mm }, { raw: p.raw_categorical?.heavy?.csi, classifier: heavy?.csi, bias: heavy?.frequency_bias }, p.bundle_decisions?.B1?.decision?.tier, p.cases, r05?.evidence_label, (p as { by_year?: unknown }).by_year);
  if (!round1) return null;
  const c = confirmation?.payload;
  const cHeavy = c?.exceedance?.["B1:heavy"]?.test;
  const round2 = c ? round({ raw: c.pooled?.M0?.rmse_mm, corrected: c.pooled?.B1_shifted?.rmse_mm }, { raw: c.raw_categorical?.heavy?.csi, classifier: cHeavy?.csi, bias: cHeavy?.frequency_bias }, c.bundle_decision?.decision?.tier, c.cases, confirmation?.evidence_label, (c as { by_year?: unknown }).by_year) : null;
  const arms = Object.values(p.regime_decisions ?? {}).map((arm) => arm?.adds_value?.adds_value);
  return { round1, round2, regimeAddsValue: arms.length && arms.every((v) => typeof v === "boolean") ? arms.some(Boolean) : null };
}

export function buildStoryFacts(inputs: { comparison: Comparison | null | undefined; final2025: Final2025; quality: Quality; coverage?: PsCoverage | null; r03?: R03Result | null; r05?: R05Result | null; confirmation?: ConfirmationResult | null }): StoryFacts {
  const { comparison, final2025, quality } = inputs;
  const raw2019 = comparison?.results?.M0_RAW_GEFS;
  const m2 = comparison?.results?.M2_GLOBAL_XGBOOST;
  const b2019 = benchmark(raw2019?.overall.continuous.rmse_mm, m2?.overall.continuous.rmse_mm, raw2019?.same_case_count);
  const b2025 = benchmark(final2025.deterministic.M0?.continuous.rmse_mm, final2025.deterministic.M1?.continuous.rmse_mm, final2025.case_count);
  const heavy = final2025.probability?.heavy?.metrics?.bss;
  const veryHeavy = final2025.probability?.very_heavy?.metrics?.bss;
  const years = Object.values(quality.years ?? {});
  return {
    benchmark2019: b2019 && { ...b2019, correctedLabel: "Global XGBoost" },
    final2025: b2025 && { ...b2025, correctedLabel: "Preselected M1" },
    probability2025: finite(heavy) && finite(veryHeavy) ? { heavyBss: heavy, veryHeavyBss: veryHeavy } : null,
    coverage: coverageFacts(inputs.coverage),
    regimeTasks: regimeTaskFacts(inputs.r03),
    reforecast: reforecastFacts(inputs.r05, inputs.confirmation),
    quality: years.length ? {
      scheduled: years.reduce((sum, y) => sum + y.scheduled_cases, 0),
      c00Eligible: years.reduce((sum, y) => sum + y.c00_source_qc_cases, 0),
      fiveMemberEligible: years.reduce((sum, y) => sum + y.full_five_member_cases, 0),
    } : null,
  };
}

export const mm = (value: number) => `${value.toFixed(2)} mm`;
/** RMSE change relative to Raw as a signed percentage: a reduction in error is negative, an increase positive. */
export const rmseChange = (reductionPercent: number) => { const change = -reductionPercent; return `${change >= 0 ? "+" : "−"}${Math.abs(change).toFixed(2)}%`; };
export const signedScore = (value: number) => `${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(4)}`;
export const count = (value: number) => value.toLocaleString("en-GB");
export const score3 = (value: number | null) => (value == null ? "n/a" : value.toFixed(3));
