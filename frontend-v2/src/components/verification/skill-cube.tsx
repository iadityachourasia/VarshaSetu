"use client";

import { useState } from "react";
import { ErrorState, MetricTerm } from "@/components/science/common";
import { DETERMINISTIC_MODEL_ORDER, OperationalFssChart, type DeterministicModelMetrics, type FssEventResult } from "@/components/science/operational-charts";
import { extractProbabilityEventMetrics } from "@/lib/operational-probability-metrics";
import { modelNames } from "@/science/frozen/results";

type EventKey = "heavy" | "very_heavy";
type Year2 = 2024 | 2025;
type Family = "continuous" | "extreme" | "probability" | "spatial";
type ContinuousMetric = "rmse_mm" | "mae_mm" | "bias_mm";
type ExtremeMetric = "POD" | "FAR" | "CSI" | "ETS";
type ProbabilityMetric = "brier" | "bss" | "pr_auc" | "roc_auc";

const YEAR_ROLE: Record<2023 | 2024 | 2025, string> = { 2023: "Cross-fit", 2024: "Validation", 2025: "Final test" };
const CONTINUOUS_LABEL: Record<ContinuousMetric, string> = { rmse_mm: "RMSE", mae_mm: "MAE", bias_mm: "Bias" };

/** Relative-to-this-table color scale, one metric family/metric at a time --
 * never one shared scale across incompatible metrics (spec section 19: "do
 * not mix incompatible metrics into one color normalization"). Lower-is-
 * better metrics (error metrics, FAR) invert the intensity mapping so the
 * best cell is always the most filled, not the least. */
function cellStyle(value: number | null, allValues: number[], lowerIsBetter: boolean): React.CSSProperties {
  if (value == null || allValues.length === 0) return {};
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const span = max - min;
  const raw = span === 0 ? 0.5 : (value - min) / span;
  const intensity = lowerIsBetter ? 1 - raw : raw;
  return { background: `color-mix(in srgb, var(--teal) ${Math.round(15 + 65 * intensity)}%, var(--surface-raised))` };
}

export function SkillCube({
  det, prob, fss,
}: {
  det: Partial<Record<Year2, Record<string, DeterministicModelMetrics> | undefined>>;
  prob: Partial<Record<Year2, Record<string, unknown> | undefined>>;
  fss: Partial<Record<Year2, Record<EventKey, FssEventResult> | undefined>>;
}) {
  const [family, setFamily] = useState<Family>("continuous");
  const [continuousMetric, setContinuousMetric] = useState<ContinuousMetric>("rmse_mm");
  const [extremeMetric, setExtremeMetric] = useState<ExtremeMetric>("CSI");
  const [event, setEvent] = useState<EventKey>("heavy");
  const [yearScope, setYearScope] = useState<"compare" | 2023>("compare");
  const years: Year2[] = [2024, 2025];

  if (yearScope === 2023) {
    return <div className="phase5-analysis-block"><h2>Skill Cube · 2023</h2><ErrorState message="2023 is train / cross-fit only. No frozen final-test or validation metric exists to place in this matrix -- comparing it against 2024/2025 here would strip away its role context." /><YearScopeControl yearScope={yearScope} setYearScope={setYearScope} /></div>;
  }

  return <div className="phase5-skill-cube">
    <div className="phase5-controls">
      <YearScopeControl yearScope={yearScope} setYearScope={setYearScope} />
      <label>Metric family<select value={family} onChange={(e) => setFamily(e.target.value as Family)}>
        <option value="continuous">Continuous</option><option value="extreme">Extreme</option><option value="probability">Probability</option><option value="spatial">Spatial</option>
      </select></label>
      {family === "continuous" ? <label>Metric<select value={continuousMetric} onChange={(e) => setContinuousMetric(e.target.value as ContinuousMetric)}>
        <option value="rmse_mm">RMSE</option><option value="mae_mm">MAE</option><option value="bias_mm">Bias</option>
      </select></label> : null}
      {family === "extreme" ? <label>Metric<select value={extremeMetric} onChange={(e) => setExtremeMetric(e.target.value as ExtremeMetric)}>
        <option value="POD">POD</option><option value="FAR">FAR</option><option value="CSI">CSI</option><option value="ETS">ETS</option>
      </select></label> : null}
      {family !== "continuous" ? <label>Event<select value={event} onChange={(e) => setEvent(e.target.value as EventKey)}>
        <option value="heavy">Heavy ≥64.5</option><option value="very_heavy">Very Heavy ≥115.6</option>
      </select></label> : null}
    </div>
    <p className="phase5-caveat"><strong>{years.map((y) => `${y} (${YEAR_ROLE[y]})`).join(" vs. ")}</strong> -- 2024 is a validation/model-selection population, 2025 is the completed one-time final test. Never read as one pooled six-year line.</p>

    {family === "continuous" ? <ContinuousMatrix det={det} metric={continuousMetric} years={years} /> : null}
    {family === "extreme" ? <ExtremeMatrix det={det} metric={extremeMetric} event={event} years={years} /> : null}
    {family === "probability" ? <ProbabilityMatrix prob={prob} event={event} years={years} /> : null}
    {family === "spatial" ? <SpatialMatrix fss={fss} event={event} years={years} /> : null}
  </div>;
}

function YearScopeControl({ yearScope, setYearScope }: { yearScope: "compare" | 2023; setYearScope: (value: "compare" | 2023) => void }) {
  return <label>Year<select value={String(yearScope)} onChange={(e) => setYearScope(e.target.value === "2023" ? 2023 : "compare")}>
    <option value="compare">2024 vs 2025</option><option value="2023">2023 (cross-fit only)</option>
  </select></label>;
}

function ContinuousMatrix({ det, metric, years }: { det: Partial<Record<Year2, Record<string, DeterministicModelMetrics> | undefined>>; metric: ContinuousMetric; years: Year2[] }) {
  const cells = years.flatMap((year) => DETERMINISTIC_MODEL_ORDER.map((model) => det[year]?.[model]?.continuous[metric] ?? null));
  const allValues = cells.filter((value): value is number => value != null);
  return <><p className="phase5-control-note">{CONTINUOUS_LABEL[metric]} · mm{metric === "bias_mm" ? " · signed, not clamped to a single best direction" : ""}</p>
    <table className="phase5-table phase5-cube-table"><thead><tr><th>Model</th>{years.map((year) => <th key={year}>{year} <small>{YEAR_ROLE[year]}</small></th>)}</tr></thead><tbody>{DETERMINISTIC_MODEL_ORDER.map((model) => <tr key={model}><th>{model} · {modelNames[model]}</th>{years.map((year) => { const value = det[year]?.[model]?.continuous[metric] ?? null; return <td key={year} style={cellStyle(value, allValues, metric !== "bias_mm")}>{value == null ? "Unavailable" : value.toFixed(4)}</td>; })}</tr>)}</tbody></table></>;
}

function ExtremeMatrix({ det, metric, event, years }: { det: Partial<Record<Year2, Record<string, DeterministicModelMetrics> | undefined>>; metric: ExtremeMetric; event: EventKey; years: Year2[] }) {
  const cells = years.flatMap((year) => DETERMINISTIC_MODEL_ORDER.map((model) => det[year]?.[model]?.[event]?.metrics[metric] ?? null));
  const allValues = cells.filter((value): value is number => value != null);
  const lowerIsBetter = metric === "FAR";
  return <><table className="phase5-table phase5-cube-table"><thead><tr><th>Model</th>{years.map((year) => <th key={year}>{year} <small>{YEAR_ROLE[year]}</small></th>)}</tr></thead><tbody>{DETERMINISTIC_MODEL_ORDER.map((model) => <tr key={model}><th>{model} · {modelNames[model]}</th>{years.map((year) => { const value = det[year]?.[model]?.[event]?.metrics[metric] ?? null; return <td key={year} style={cellStyle(value, allValues, lowerIsBetter)}>{value == null ? "Unavailable" : value.toFixed(4)}</td>; })}</tr>)}</tbody></table><p className="phase5-caveat">Each of <MetricTerm term="POD" />/<MetricTerm term="FAR" />/<MetricTerm term="CSI" />/<MetricTerm term="ETS" /> answers a different verification question; do not collapse them into one score.</p></>;
}

function ProbabilityMatrix({ prob, event, years }: { prob: Partial<Record<Year2, Record<string, unknown> | undefined>>; event: EventKey; years: Year2[] }) {
  const metrics: { key: ProbabilityMetric; label: string }[] = [{ key: "brier", label: "Brier" }, { key: "bss", label: "BSS" }, { key: "pr_auc", label: "PR-AUC" }, { key: "roc_auc", label: "ROC-AUC" }];
  return <table className="phase5-table phase5-cube-table"><thead><tr><th>Metric</th>{years.map((year) => <th key={year}>{year} <small>{YEAR_ROLE[year]}</small></th>)}</tr></thead><tbody>{metrics.map(({ key, label }) => <tr key={key}><th><MetricTerm term={label} /></th>{years.map((year) => { const eventMetric = extractProbabilityEventMetrics(prob[year], event); const value = eventMetric ? eventMetric[key] : null; return <td key={year}>{value == null ? "Unavailable" : value.toFixed(key === "brier" ? 5 : 4)}</td>; })}</tr>)}</tbody></table>;
}

function SpatialMatrix({ fss, event, years }: { fss: Partial<Record<Year2, Record<EventKey, FssEventResult> | undefined>>; event: EventKey; years: Year2[] }) {
  return <div className="phase5-cube-spatial">{years.map((year) => { const eventFss = fss[year]?.[event]; return <div key={year}><h3>{year} <small>{YEAR_ROLE[year]}</small></h3>{eventFss ? <OperationalFssChart fss={eventFss} selectedModelLabel="M1 Ridge MOS" /> : <ErrorState message="FSS is unavailable for this year." />}</div>; })}</div>;
}
