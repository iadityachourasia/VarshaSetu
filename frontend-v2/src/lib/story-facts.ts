// Story Mode narrates frozen evidence; it must not carry typed scientific numbers (AGENTS.md 3.3). Every figure it shows is
// derived here from (a) the live, hash-verified /api/science/model-comparison for the 2019 benchmark and (b) the generated
// frozen presentation bundle (public/science/operational-v1) for the 2025 final test and the data-quality funnel.
// A value that cannot be derived is null, and the scene says so instead of showing a number.

export type Benchmark = { rawRmse: number; correctedRmse: number; reductionPercent: number; cases: number };
export type StoryFacts = {
  benchmark2019: (Benchmark & { correctedLabel: string }) | null;
  final2025: (Benchmark & { correctedLabel: string }) | null;
  probability2025: { heavyBss: number; veryHeavyBss: number } | null;
  quality: { scheduled: number; c00Eligible: number; fiveMemberEligible: number } | null;
};

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

export function buildStoryFacts(inputs: { comparison: Comparison | null | undefined; final2025: Final2025; quality: Quality }): StoryFacts {
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
