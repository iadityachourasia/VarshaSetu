"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DataSourceIndicator, ErrorState, LoadingState } from "@/components/science/common";
import { modelNames } from "@/science/frozen/results";
import { getOperationalDeterministicMetrics, getOperationalFSS, getOperationalProbabilityMetrics, type OperationalYear } from "@/lib/api/operational";
import { loadOperationalCaseList, type CaseListItem } from "@/lib/operational-case-list";
import { withStaticFallback, type DataSourceMode } from "@/lib/data-source";
import { extractProbabilityEventMetrics } from "@/lib/operational-probability-metrics";
import { median } from "@/lib/stats";
import {
  DETERMINISTIC_MODEL_ORDER, DeterministicCategoricalTable, OperationalFssChart, PopulationBadge, ProbabilityQualityCards,
  leadRmse, type DeterministicModelMetrics, type FssEventResult,
} from "@/components/science/operational-charts";

type Year = 2024 | 2025;
type EventKey = "heavy" | "very_heavy";
type Tab = "continuous" | "extremes" | "probability" | "spatial" | "lead_time" | "case_outcomes" | "generalization";
const TABS: { key: Tab; label: string }[] = [
  { key: "continuous", label: "Continuous" },
  { key: "extremes", label: "Extremes" },
  { key: "probability", label: "Probability" },
  { key: "spatial", label: "Spatial" },
  { key: "lead_time", label: "Lead Time" },
  { key: "case_outcomes", label: "Case Outcomes" },
  { key: "generalization", label: "Generalization" },
];

/** Each bar is one 2025 final-test case's M1-minus-Raw RMSE, sorted so the
 * diverging shape is legible; negative (improved) and positive (worsened)
 * are also separated by color per axe's "not color alone" rule via the
 * sign-labeled axis and caption, not color alone. */
function CaseOutcomeChart({ deltas }: { deltas: number[] }) {
  const data = [...deltas].sort((a, b) => a - b).map((delta, index) => ({ index, delta }));
  return <figure className="chart-figure"><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 10, right: 15, bottom: 4, left: 0 }}>
    <CartesianGrid stroke="var(--line)" strokeDasharray="2 6" />
    <XAxis dataKey="index" tick={false} label={{ value: "Cases, sorted by RMSE change", position: "insideBottom", offset: -2, fill: "var(--text-subtle)", fontSize: 9 }} />
    <YAxis tick={{ fill: "var(--text-subtle)", fontSize: 10 }} label={{ value: "M1 − Raw RMSE (mm)", angle: -90, position: "insideLeft", fill: "var(--text-subtle)", fontSize: 9 }} />
    <ReferenceLine y={0} stroke="var(--text-subtle)" />
    <Tooltip formatter={(value) => (typeof value === "number" ? `${value.toFixed(3)} mm` : value)} labelFormatter={() => "Case RMSE change"} />
    <Bar dataKey="delta">{data.map((entry) => <Cell key={entry.index} fill={entry.delta < 0 ? "var(--corrected)" : "#9c605c"} />)}</Bar>
  </BarChart></ResponsiveContainer></div><figcaption>Negative (teal) = M1 improved on Raw for that case; positive (red) = M1 worsened. Not every case improved.</figcaption></figure>;
}

/** A minimal two-point slope chart: one line per model across the 2024
 * validation and 2025 final-test populations. Deliberately not a bar chart
 * -- the point is the direction of change across years, not the absolute
 * value in either year alone. */
function GeneralizationSlopeChart({ raw2024, m1_2024, raw2025, m1_2025 }: { raw2024: number | null; m1_2024: number | null; raw2025: number | null; m1_2025: number | null }) {
  const data = [
    { year: "2024 validation", raw: raw2024, m1: m1_2024 },
    { year: "2025 final test", raw: raw2025, m1: m1_2025 },
  ];
  return <figure className="chart-figure"><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 10, right: 15, bottom: 0, left: -18 }}>
    <CartesianGrid stroke="var(--line)" strokeDasharray="2 6" />
    <XAxis dataKey="year" tick={{ fill: "var(--text-subtle)", fontSize: 10 }} />
    <YAxis tick={{ fill: "var(--text-subtle)", fontSize: 10 }} />
    <Tooltip formatter={(value) => (typeof value === "number" ? `${value.toFixed(4)} mm` : value)} />
    <Legend />
    <Line type="linear" dataKey="raw" name="Raw GEFS" stroke="var(--raw)" strokeWidth={2.5} dot={{ r: 5 }} connectNulls={false} />
    <Line type="linear" dataKey="m1" name="M1 Ridge MOS" stroke="var(--corrected)" strokeWidth={2.5} strokeDasharray="5 3" dot={{ r: 5 }} connectNulls={false} />
  </LineChart></ResponsiveContainer></div><figcaption>M1 improved RMSE relative to Raw in both the model-selection year and the one-time final test -- not proof of universal operational performance.</figcaption></figure>;
}

// Phase 5A.2D: live-API-primary for the deterministic and probability metric
// families (getOperationalDeterministicMetrics / getOperationalProbabilityMetrics)
// and FSS (getOperationalFSS), reusing the exact same shared components
// (DeterministicCategoricalTable, OperationalFssChart, ProbabilityQualityCards)
// Extreme Rain uses against the same live data -- same withStaticFallback
// pattern as Casebook/Ensemble/Regime Intelligence. Restructured into named
// tabs (spec section 14): Continuous / Extremes / Probability / Spatial /
// Lead Time / Case Outcomes / Generalization. The "Case outcomes" tab has no
// dedicated metrics endpoint; it is computed directly from the already-live
// per-case index (loadOperationalCaseList) using the exact sign-of-delta
// rule the backend itself uses for `selected_model_improved_vs_raw`
// (backend/app/api/operational.py) -- a transparent aggregate over real
// per-case values, not a new or invented statistic. Track A's own
// verification (VerificationView) is untouched.
export function OperationalVerification() {
  const [tab, setTab] = useState<Tab>("continuous");
  const [year, setYear] = useState<Year>(2025);
  const [event, setEvent] = useState<EventKey>("heavy");

  const det2024 = useQuery({ queryKey: ["operational-deterministic", 2024], queryFn: () => withStaticFallback(() => getOperationalDeterministicMetrics(2024 as OperationalYear), null) });
  const det2025 = useQuery({ queryKey: ["operational-deterministic", 2025], queryFn: () => withStaticFallback(() => getOperationalDeterministicMetrics(2025 as OperationalYear), null) });
  const prob2024 = useQuery({ queryKey: ["operational-probability-metrics", 2024], queryFn: () => withStaticFallback(() => getOperationalProbabilityMetrics(2024 as OperationalYear), null) });
  const prob2025 = useQuery({ queryKey: ["operational-probability-metrics", 2025], queryFn: () => withStaticFallback(() => getOperationalProbabilityMetrics(2025 as OperationalYear), null) });
  const fss2024 = useQuery({ queryKey: ["operational-fss", 2024], queryFn: () => withStaticFallback(() => getOperationalFSS(2024 as OperationalYear), null), enabled: tab === "spatial" });
  const fss2025 = useQuery({ queryKey: ["operational-fss", 2025], queryFn: () => withStaticFallback(() => getOperationalFSS(2025 as OperationalYear), null), enabled: tab === "spatial" });
  const caseList2025 = useQuery({ queryKey: ["operational-case-list", 2025], queryFn: () => loadOperationalCaseList(2025 as OperationalYear), staleTime: 60_000 });

  const det = useMemo(() => ({
    2024: det2024.data?.data?.metrics as Record<string, DeterministicModelMetrics> | undefined,
    2025: det2025.data?.data?.metrics as Record<string, DeterministicModelMetrics> | undefined,
  }), [det2024.data, det2025.data]);
  const fss = useMemo(() => ({
    2024: fss2024.data?.data?.fss as Record<EventKey, FssEventResult> | undefined,
    2025: fss2025.data?.data?.fss as Record<EventKey, FssEventResult> | undefined,
  }), [fss2024.data, fss2025.data]);

  const outcomeCases = useMemo(
    () => (caseList2025.data?.data ?? []).filter((item): item is CaseListItem & { m1_minus_raw_rmse_mm: number } => item.m1_minus_raw_rmse_mm !== null),
    [caseList2025.data],
  );
  const improved = outcomeCases.filter((item) => item.m1_minus_raw_rmse_mm < 0).length;
  const worsened = outcomeCases.filter((item) => item.m1_minus_raw_rmse_mm > 0).length;
  const tied = outcomeCases.length - improved - worsened;
  const medianDelta = median(outcomeCases.map((item) => item.m1_minus_raw_rmse_mm));

  const heavy2024 = extractProbabilityEventMetrics(prob2024.data?.data?.metrics, "heavy");
  const veryHeavy2024 = extractProbabilityEventMetrics(prob2024.data?.data?.metrics, "very_heavy");
  const heavy2025 = extractProbabilityEventMetrics(prob2025.data?.data?.metrics, "heavy");
  const veryHeavy2025 = extractProbabilityEventMetrics(prob2025.data?.data?.metrics, "very_heavy");
  const currentProbabilityMetric = extractProbabilityEventMetrics((year === 2024 ? prob2024 : prob2025).data?.data?.metrics, event);
  const currentDeterministicPopulation = det[year]?.M0 ?? null;
  const currentFssEvent = fss[year]?.[event];

  const indicatorMode: DataSourceMode | undefined = [det2024.data?.mode, det2025.data?.mode, prob2024.data?.mode, prob2025.data?.mode]
    .find((candidate) => candidate && candidate !== "VERIFIED_API") ?? det2025.data?.mode;

  if (det2024.isPending || det2025.isPending || prob2024.isPending || prob2025.isPending || caseList2025.isPending) {
    return <div className="phase5-verification"><LoadingState /></div>;
  }
  if (caseList2025.isError || !caseList2025.data || caseList2025.data.mode === "UNAVAILABLE") {
    return <div className="phase5-verification"><ErrorState message={caseList2025.data?.message ?? "Frozen 2025 case catalogue unavailable."} /></div>;
  }
  if (caseList2025.data.mode === "INTEGRITY_FAILURE") {
    return <div className="phase5-verification"><ErrorState message={`Scientific artifact integrity check failed: ${caseList2025.data.message}. This is a hard failure and is not masked by cached data.`} /></div>;
  }

  return <div className="phase5-verification">
    <div className="phase5-analysis-block">
      <h2>Model selection story {indicatorMode ? <DataSourceIndicator mode={indicatorMode} /> : null}</h2>
      <ol className="phase5-pipeline">
        <li>2024 validation: M1 Ridge MOS selected as the primary model under the frozen validation-RMSE rule, before the 2025 holdout was opened.</li>
        <li>2025: M1 evaluated exactly once, as the one-time final test.</li>
      </ol>
      <p className="phase5-caveat">M2 achieved a lower secondary 2025 RMSE ({det[2025]?.M2?.continuous.rmse_mm.toFixed(4) ?? "unavailable"} mm vs. M1&rsquo;s {det[2025]?.M1?.continuous.rmse_mm.toFixed(4) ?? "unavailable"} mm), but was not eligible for post-test reselection: reselecting the &ldquo;winner&rdquo; after seeing final-test results would invalidate the test. M1 remains the reported primary result.</p>
    </div>

    <div className="phase5-tab-row" role="tablist" aria-label="Verification mode">{TABS.map((item) => <button key={item.key} type="button" role="tab" aria-selected={tab === item.key} onClick={() => setTab(item.key)}>{item.label}</button>)}</div>

    {tab !== "lead_time" && tab !== "case_outcomes" && tab !== "generalization" ? <div className="phase5-controls">
      <label>Year<select value={year} onChange={(change) => setYear(Number(change.target.value) as Year)}><option value={2024}>2024 validation</option><option value={2025}>2025 completed final test</option></select></label>
      {tab !== "continuous" ? <label>Event<select value={event} onChange={(change) => setEvent(change.target.value as EventKey)}><option value="heavy">Heavy ≥64.5</option><option value="very_heavy">Very Heavy ≥115.6</option></select></label> : null}
      {currentDeterministicPopulation ? <PopulationBadge cases={currentDeterministicPopulation.case_count} cells={currentDeterministicPopulation.cell_count} /> : null}
    </div> : null}

    {tab === "continuous" ? <section className="phase5-analysis-block" role="tabpanel">
      <h2>Continuous verification · {year === 2025 ? "2025 completed final test" : "2024 validation / model selection"}</h2>
      <p>{year === 2025 ? "SELECTED_MODEL_IMPROVED_RMSE: M1 reduced RMSE versus Raw on the completed final test." : "VALIDATION / MODEL SELECTION: M1 was selected here under the frozen primary-RMSE rule. These are not final-test results."}</p>
      <table className="phase5-table"><thead><tr><th>Model</th><th>RMSE · mm</th><th>MAE · mm</th><th>Bias · mm</th><th>Governance role</th></tr></thead><tbody>{DETERMINISTIC_MODEL_ORDER.map((model) => { const item = det[year]?.[model]; return <tr key={model}><th>{model} · {modelNames[model]}</th><td>{item ? item.continuous.rmse_mm.toFixed(4) : "Unavailable"}</td><td>{item ? item.continuous.mae_mm.toFixed(4) : "Unavailable"}</td><td>{item ? item.continuous.bias_mm.toFixed(4) : "Unavailable"}</td><td>{model === "M1" ? "Preselected primary" : model === "M0" ? "Raw reference" : model === "M2" ? "Secondary final-test result" : "Predeclared secondary"}</td></tr>; })}</tbody></table>
      {year === 2025 && det[2025]?.M0 && det[2025]?.M1 ? <p className="phase5-caveat">Difference: {(det[2025].M1.continuous.rmse_mm - det[2025].M0.continuous.rmse_mm).toFixed(4)} mm · relative change {(100 * (det[2025].M1.continuous.rmse_mm - det[2025].M0.continuous.rmse_mm) / det[2025].M0.continuous.rmse_mm).toFixed(4)}%. Do not visually assign &ldquo;winner&rdquo; based only on lowest 2025 RMSE -- M1 remains primary because it was selected before the test, not because it is the single lowest number.</p> : null}
    </section> : null}

    {tab === "extremes" ? <section className="phase5-analysis-block" role="tabpanel">
      <h2>Thresholded event detection · {year}</h2>
      <p>Each model&rsquo;s own deterministic rainfall forecast thresholded at the frozen Heavy/Very-Heavy boundary. Reused from Extreme Rain&rsquo;s Detection mode against the same live data.</p>
      {(year === 2025 ? det2025 : det2024).isPending ? <LoadingState /> : <DeterministicCategoricalTable metrics={det[year]} event={event} modelNames={modelNames} />}
    </section> : null}

    {tab === "probability" ? <section className="phase5-analysis-block" role="tabpanel">
      <h2>Probability quality · {year}</h2>
      {(year === 2025 ? prob2025 : prob2024).isPending ? <LoadingState /> : !currentProbabilityMetric ? <ErrorState message="Probability quality metrics are unavailable for this year." /> : <ProbabilityQualityCards metric={currentProbabilityMetric} />}
      <p className="phase5-caveat">Only scalar PR-AUC/ROC-AUC exist in the frozen corpus; no PR or ROC curve point arrays are rendered anywhere on this page.</p>
    </section> : null}

    {tab === "spatial" ? <section className="phase5-analysis-block" role="tabpanel">
      <h2>Spatial skill (FSS) · {year}</h2>
      {(year === 2025 ? fss2025 : fss2024).isPending ? <LoadingState /> : !currentFssEvent ? <ErrorState message="FSS results are unavailable for this year." /> : <OperationalFssChart fss={currentFssEvent} selectedModelLabel="M1 Ridge MOS" />}
    </section> : null}

    {tab === "lead_time" ? <section className="phase5-analysis-block" role="tabpanel"><h2>2025 lead-time RMSE · paired common cells</h2><table className="phase5-table"><thead><tr><th>Model</th><th>Day 1</th><th>Day 2</th><th>Day 3</th></tr></thead><tbody>{DETERMINISTIC_MODEL_ORDER.map((model) => <tr key={model}><th>{modelNames[model]}</th>{(["24", "48", "72"] as const).map((hour) => { const value = leadRmse(det[2025]?.[model]?.leads?.[hour]); return <td key={hour}>{value == null ? "Unavailable" : value.toFixed(3)}</td>; })}</tr>)}</tbody></table></section> : null}

    {tab === "case_outcomes" ? <section className="phase5-analysis-block" role="tabpanel">
      <h2>Case outcomes · selected M1 versus Raw</h2>
      <div className="phase5-outcome-bar"><span style={{ flex: improved }}>{improved} improved</span><span style={{ flex: worsened }}>{worsened} worsened</span></div>
      <p>{tied} tied · median per-case RMSE change {medianDelta == null ? "unavailable" : `${medianDelta.toFixed(4)} mm`}. All {outcomeCases.length} cases remain in the final result.</p>
      {outcomeCases.length > 0 ? <CaseOutcomeChart deltas={outcomeCases.map((item) => item.m1_minus_raw_rmse_mm)} /> : null}
      <p className="phase5-caveat">Not every case improved -- {worsened} of {outcomeCases.length} worsened under M1 relative to Raw. Negative delta = improvement; positive = deterioration.</p>
    </section> : null}

    {tab === "generalization" ? <>
      <section className="phase5-analysis-block" role="tabpanel">
        <h2>Validation → Final-Test Behavior</h2>
        <GeneralizationSlopeChart raw2024={det[2024]?.M0?.continuous.rmse_mm ?? null} m1_2024={det[2024]?.M1?.continuous.rmse_mm ?? null} raw2025={det[2025]?.M0?.continuous.rmse_mm ?? null} m1_2025={det[2025]?.M1?.continuous.rmse_mm ?? null} />
        <table className="phase5-table"><thead><tr><th>Population</th><th>Raw RMSE</th><th>Selected M1 RMSE</th></tr></thead><tbody><tr><th>2024 validation</th><td>{det[2024]?.M0?.continuous.rmse_mm.toFixed(4) ?? "Unavailable"}</td><td>{det[2024]?.M1?.continuous.rmse_mm.toFixed(4) ?? "Unavailable"}</td></tr><tr><th>2025 final</th><td>{det[2025]?.M0?.continuous.rmse_mm.toFixed(4) ?? "Unavailable"}</td><td>{det[2025]?.M1?.continuous.rmse_mm.toFixed(4) ?? "Unavailable"}</td></tr></tbody></table>
        <p className="phase5-caveat">M1 improved RMSE in both the model-selection year and the one-time final test. This is not proof of universal operational performance -- the populations differ, and this descriptive comparison does not reopen model selection.</p>
      </section>
      <section className="phase5-analysis-block" role="tabpanel">
        <h2>Probability generalization</h2>
        <table className="phase5-table"><thead><tr><th>Population</th><th>Heavy PR-AUC</th><th>Very Heavy PR-AUC</th></tr></thead><tbody><tr><th>2024 validation</th><td>{heavy2024 ? heavy2024.pr_auc.toFixed(5) : "Unavailable"}</td><td>{veryHeavy2024 ? veryHeavy2024.pr_auc.toFixed(5) : "Unavailable"}</td></tr><tr><th>2025 final</th><td>{heavy2025 ? heavy2025.pr_auc.toFixed(5) : "Unavailable"}</td><td>{veryHeavy2025 ? veryHeavy2025.pr_auc.toFixed(5) : "Unavailable"}</td></tr></tbody></table>
        <p className="phase5-caveat">Probability discrimination weakened from validation to final test. The populations differ; this descriptive comparison does not reopen model selection.</p>
      </section>
    </> : null}
  </div>;
}
