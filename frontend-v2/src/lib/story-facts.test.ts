import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { buildStoryFacts, count, mm, reduction, rmseChange, signedScore } from "./story-facts";
import final2025 from "../../public/science/operational-v1/final_result_2025.json";
import quality from "../../public/science/operational-v1/quality.json";

const REPO = path.resolve(__dirname, "../../..");
// Same frozen Track A results the live /api/science/model-comparison endpoint serves.
const frozen2019 = JSON.parse(readFileSync(path.join(REPO, "data/manifests/phase2b/2019_final_results.json"), "utf8")) as { test_results: Record<string, { overall: { continuous: { rmse_mm: number } }; same_case_count?: number }>; case_count?: number };
const comparison = {
  results: Object.fromEntries(Object.entries(frozen2019.test_results).map(([model, block]) => [model, { overall: block.overall, same_case_count: block.same_case_count ?? (frozen2019.case_count as number) }])),
};

describe("Story Mode facts are derived from frozen evidence, never typed", () => {
  const facts = buildStoryFacts({ comparison, final2025: final2025 as never, quality });

  it("derives the 2019 benchmark from the frozen results", () => {
    const raw = frozen2019.test_results.M0_RAW_GEFS.overall.continuous.rmse_mm;
    const m2 = frozen2019.test_results.M2_GLOBAL_XGBOOST.overall.continuous.rmse_mm;
    expect(facts.benchmark2019?.rawRmse).toBe(raw);
    expect(facts.benchmark2019?.correctedRmse).toBe(m2);
    expect(facts.benchmark2019?.reductionPercent).toBeCloseTo(((raw - m2) / raw) * 100, 10);
    expect(facts.benchmark2019?.cases).toBeGreaterThan(0);
  });

  it("derives the 2025 final test, probability skill and data-quality funnel from the frozen presentation bundle", () => {
    expect(facts.final2025?.rawRmse).toBe(final2025.deterministic.M0.continuous.rmse_mm);
    expect(facts.final2025?.correctedRmse).toBe(final2025.deterministic.M1.continuous.rmse_mm);
    expect(facts.final2025?.cases).toBe(final2025.case_count);
    expect(facts.probability2025?.heavyBss).toBe(final2025.probability.heavy.metrics.bss);
    expect(facts.probability2025?.veryHeavyBss).toBe(final2025.probability.very_heavy.metrics.bss);
    const years = Object.values(quality.years);
    expect(facts.quality).toEqual({
      scheduled: years.reduce((a, y) => a + y.scheduled_cases, 0), c00Eligible: years.reduce((a, y) => a + y.c00_source_qc_cases, 0),
      fiveMemberEligible: years.reduce((a, y) => a + y.full_five_member_cases, 0),
    });
  });

  it("renders exactly the figures the previous hand-typed scenes showed (they were right; now they are derived)", () => {
    const b19 = facts.benchmark2019!;
    const b25 = facts.final2025!;
    expect([mm(b19.rawRmse), mm(b19.correctedRmse), rmseChange(b19.reductionPercent)]).toEqual(["19.77 mm", "17.85 mm", "−9.73%"]);
    expect([mm(b25.rawRmse), mm(b25.correctedRmse), rmseChange(b25.reductionPercent)]).toEqual(["16.17 mm", "15.57 mm", "−3.66%"]);
    expect([signedScore(facts.probability2025!.heavyBss), signedScore(facts.probability2025!.veryHeavyBss)]).toEqual(["+0.0948", "+0.0265"]);
    expect([count(facts.quality!.scheduled), count(facts.quality!.c00Eligible), count(facts.quality!.fiveMemberEligible)]).toEqual(["1,125", "615", "218"]);
  });

  it("returns null, not a guess, when the live 2019 source is unavailable or malformed", () => {
    expect(buildStoryFacts({ comparison: null, final2025: final2025 as never, quality }).benchmark2019).toBeNull();
    expect(buildStoryFacts({ comparison: { results: {} }, final2025: final2025 as never, quality }).benchmark2019).toBeNull();
    const broken = { results: { M0_RAW_GEFS: { overall: { continuous: { rmse_mm: Number.NaN } }, same_case_count: 10 }, M2_GLOBAL_XGBOOST: { overall: { continuous: { rmse_mm: 1 } }, same_case_count: 10 } } };
    expect(buildStoryFacts({ comparison: broken, final2025: final2025 as never, quality }).benchmark2019).toBeNull();
    expect(buildStoryFacts({ comparison, final2025: { ...final2025, probability: {} } as never, quality }).probability2025).toBeNull();
  });

  it("signs an RMSE increase as an increase, never as a reduction", () => {
    expect(reduction(10, 12)).toBeLessThan(0);
    expect(rmseChange(reduction(10, 12))).toBe("+20.00%");
    expect(rmseChange(reduction(10, 8))).toBe("−20.00%");
  });
});

describe("the Story Mode component contains no scientific literals", () => {
  const source = readFileSync(path.resolve(__dirname, "../components/story/story-mode.tsx"), "utf8");
  // JSX text between tags and template strings, ignoring import lines, comments and class names.
  const code = source.split("\n").filter((line) => !/^\s*(import |\/\/)/.test(line)).join("\n").replace(/className="[^"]*"/g, "").replace(/aria-[a-z]+="[^"]*"/g, "");
  it("has no decimal numbers, mm values, percentages or large counts typed into scenes", () => {
    const offenders = code.match(/(?<![A-Za-z_.\-/])\d+\.\d+|\d[\d,]*\s?mm\b|\d+(\.\d+)?%|\b\d{3,}\b/g) ?? [];
    // Allowed: experiment years, the standard pressure levels named in the narrative (850, 700 and 500 hPa) and 100 (progress-bar layout). Anything else is a result.
    const descriptive = /^(20(1[7-9]|2[0-5])|500|700|850|100)$/;   // 100 is the progress-bar percentage arithmetic
    expect(offenders.filter((token) => !descriptive.test(token)), offenders.join(", ")).toEqual([]);
  });
  it("derives every scene figure from the facts object", () => {
    for (const fragment of ["facts.benchmark2019", "facts.final2025", "facts.probability2025", "facts.quality", "buildStoryFacts"]) expect(source).toContain(fragment);
  });
});

describe("Story Mode facts for coverage, regime detection and the reforecast study", () => {
  const PHASE15 = path.join(REPO, "backend/app/evidence_data/phase15");
  const load = (name: string) => JSON.parse(readFileSync(path.join(PHASE15, name), "utf8"));
  // The API serves the frozen file as the payload, with the label and role beside it.
  const r05 = { evidence_label: load("reforecast_r05_test.json").label, payload: load("reforecast_r05_test.json") };
  const confirmation = { evidence_label: load("reforecast_r05_confirmation.json").label, payload: load("reforecast_r05_confirmation.json") };
  const r03 = { payload: load("reforecast_r03_test.json") };

  it("derives both reforecast rounds, with their frozen tiers, from the evidence files", () => {
    const facts = buildStoryFacts({ comparison: null, final2025: final2025 as never, quality, r05: r05 as never, confirmation: confirmation as never }).reforecast!;
    expect(facts.round1.rawRmse).toBe(r05.payload.pooled.M0.rmse_mm);
    expect(facts.round1.correctedRmse).toBe(r05.payload.pooled.B1.rmse_mm);
    expect(facts.round1.tier).toBe(r05.payload.bundle_decisions.B1.decision.tier);
    expect(facts.round1.classifierHeavyCsi).toBe(r05.payload.exceedance["B1:heavy"].test.csi);
    expect(facts.round2?.correctedRmse).toBe(confirmation.payload.pooled.B1_shifted.rmse_mm);
    expect(facts.round2?.tier).toBe(confirmation.payload.bundle_decision.decision.tier);
    expect(facts.regimeAddsValue).toBe(false);
  });

  it("derives the five regime detection tasks with their AUC and verdict", () => {
    const tasks = buildStoryFacts({ comparison: null, final2025: final2025 as never, quality, r03: r03 as never }).regimeTasks!;
    expect(tasks.map((t) => t.key)).toEqual(["ACTIVE", "BREAK", "LOW_DEPRESSION", "WESTERN_DISTURBANCE", "COASTAL_OROGRAPHIC"]);
    expect(tasks[0].auc).toBe(r03.payload.tasks.ACTIVE.auc.point);
    expect(tasks.every((t) => t.verdict === "validated and useful" || t.verdict === "validated" || t.verdict === "not supported")).toBe(true);
  });

  it("derives requirement coverage from the counts, and says nothing when the source is missing", () => {
    const coverage = { counts: { IMPLEMENTED: 3, PARTIAL: 1, PLANNED: 0 }, mandatory_counts: { IMPLEMENTED: 2, PARTIAL: 0, PLANNED: 0 } };
    expect(buildStoryFacts({ comparison: null, final2025: final2025 as never, quality, coverage: coverage as never }).coverage).toEqual({ implemented: 3, partial: 1, planned: 0, total: 4, mandatoryImplemented: 2, mandatoryTotal: 2 });
    expect(buildStoryFacts({ comparison: null, final2025: final2025 as never, quality }).coverage).toBeNull();
    expect(buildStoryFacts({ comparison: null, final2025: final2025 as never, quality, coverage: { counts: {}, mandatory_counts: {} } as never }).coverage).toBeNull();
  });

  it("returns null rather than a partial or invented figure for malformed evidence", () => {
    expect(buildStoryFacts({ comparison: null, final2025: final2025 as never, quality, r05: { payload: { pooled: {} } } as never }).reforecast).toBeNull();
    expect(buildStoryFacts({ comparison: null, final2025: final2025 as never, quality, r03: { payload: { tasks: {} } } as never }).regimeTasks).toBeNull();
  });
});
