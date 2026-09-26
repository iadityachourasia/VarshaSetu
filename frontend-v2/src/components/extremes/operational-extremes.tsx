"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { geometrySchema, getScience } from "@/lib/api/science";
import { ProbabilityLegend } from "@/components/maps/map-legend";
import { getOperationalIndex, operationalGrid, operationalMask } from "@/science/frozen/operational";
import { modelNames, thresholds } from "@/science/frozen/results";
import {
  getOperationalAvailability, getOperationalDeterministicMetrics, getOperationalFSS,
  getOperationalProbability, getOperationalProbabilityMetrics, operationalYearSchema, type OperationalYear,
} from "@/lib/api/operational";
import { loadOperationalCaseList } from "@/lib/operational-case-list";
import { withStaticFallback, type DataSourceMode } from "@/lib/data-source";
import { extractProbabilityEventMetrics } from "@/lib/operational-probability-metrics";
import { DeterministicCategoricalTable, OperationalFssChart, OperationalReliabilityChart, PopulationBadge, ProbabilityQualityCards, type DeterministicModelMetrics, type FssEventResult } from "@/components/science/operational-charts";
import type { CellSelection } from "@/lib/maps/grid";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });
type EventKey = "heavy" | "very_heavy";
type Mode = "probability" | "detection" | "spatial" | "reliability";
const YEARS = [2023, 2024, 2025] as const;

// Phase 5A.2D: live-API-primary and year-adaptive (2023/2024/2025). Which of
// the four modes can render anything for the selected year is driven by the
// live availability endpoint (getOperationalAvailability), not a hardcoded
// year check -- 2023 genuinely has no frozen probability/FSS/reliability/
// deterministic-detection artifacts (models are fit on 2023, not scored
// against it), and the UI says so from the backend's own notes rather than
// rendering a fake disabled chart. Grid geometry (lat/lon centers, valid-
// cell mask) is presentation-only and continues to read the static bundle,
// exactly as Ensemble/Regime already do (docs/96 section 19).
export function OperationalExtremes({ initialCase, initialYear }: { initialCase?: string; initialYear?: OperationalYear }) {
  const [year, setYear] = useState<OperationalYear>(initialYear ?? 2025);
  const [event, setEvent] = useState<EventKey>("heavy");
  const [mode, setMode] = useState<Mode>("probability");
  const [caseId, setCaseId] = useState(initialCase ?? "");
  const [selected, setSelected] = useState<CellSelection | null>(null);

  const index = useQuery({ queryKey: ["operational-index"], queryFn: getOperationalIndex, staleTime: Infinity });
  const availabilityResult = useQuery({
    queryKey: ["operational-availability", year],
    queryFn: () => withStaticFallback(() => getOperationalAvailability(year), null),
  });
  const caseListResult = useQuery({
    queryKey: ["operational-case-list", year],
    queryFn: () => loadOperationalCaseList(year),
    staleTime: 60_000,
  });
  const cases = useMemo(
    () => (caseListResult.data?.data ?? []).filter((item) => item.probability_source_eligible),
    [caseListResult.data],
  );
  const selectedCase = cases.find((item) => item.case_id === caseId) ?? cases[0];

  const availability = availabilityResult.data?.data;
  const eventProbabilityAvailable = availability ? availability[event === "heavy" ? "heavy_probability" : "very_heavy_probability"] !== "unavailable" : false;
  const detectionAvailable = availability?.case_level_metrics ?? false;
  const fssAvailable = availability?.fss ?? false;
  const reliabilityAvailable = availability?.reliability_bins ?? false;

  const probabilityFieldResult = useQuery({
    queryKey: ["operational-probability-field", year, selectedCase?.case_id, event],
    queryFn: () => withStaticFallback(() => getOperationalProbability(year, selectedCase!.case_id, event), null),
    enabled: Boolean(selectedCase) && eventProbabilityAvailable,
  });
  const probabilityMetricsResult = useQuery({
    queryKey: ["operational-probability-metrics", year],
    queryFn: () => withStaticFallback(() => getOperationalProbabilityMetrics(year), null),
    enabled: eventProbabilityAvailable,
  });
  const fssResult = useQuery({
    queryKey: ["operational-fss", year],
    queryFn: () => withStaticFallback(() => getOperationalFSS(year), null),
    enabled: fssAvailable,
  });
  const deterministicResult = useQuery({
    queryKey: ["operational-deterministic", year],
    queryFn: () => withStaticFallback(() => getOperationalDeterministicMetrics(year), null),
    enabled: detectionAvailable,
  });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });

  const grid = index.data ? operationalGrid(index.data) : null;
  const mask = index.data ? operationalMask(index.data) : null;
  const metric = extractProbabilityEventMetrics(probabilityMetricsResult.data?.data?.metrics, event);
  const fssEvent = fssResult.data?.data?.fss?.[event] as FssEventResult | undefined;
  const deterministicMetrics = deterministicResult.data?.data?.metrics as Record<string, DeterministicModelMetrics> | undefined;
  const threshold = event === "heavy" ? thresholds.heavy : thresholds.veryHeavy;
  const values = probabilityFieldResult.data?.data?.values ?? null;
  const population = deterministicMetrics?.M0 ?? null;

  const indicatorMode: DataSourceMode | undefined = [availabilityResult.data?.mode, probabilityFieldResult.data?.mode, probabilityMetricsResult.data?.mode, fssResult.data?.mode, deterministicResult.data?.mode]
    .find((candidate) => candidate && candidate !== "VERIFIED_API") ?? availabilityResult.data?.mode;

  if (index.isPending || caseListResult.isPending || availabilityResult.isPending) return <div className="page-content"><LoadingState /></div>;
  if (index.isError) return <div className="page-content"><ErrorState message="Frozen operational-era grid geometry unavailable." /></div>;
  if (availabilityResult.isError || !availabilityResult.data || availabilityResult.data.mode === "UNAVAILABLE") {
    return <div className="page-content"><ErrorState message={availabilityResult.data?.message ?? "Year availability metadata unavailable."} /></div>;
  }
  if (availabilityResult.data.mode === "INTEGRITY_FAILURE") {
    return <div className="page-content"><ErrorState message={`Scientific artifact integrity check failed: ${availabilityResult.data.message}. This is a hard failure and is not masked by cached data.`} /></div>;
  }
  if (caseListResult.isError || !caseListResult.data || caseListResult.data.mode === "UNAVAILABLE") {
    return <div className="page-content"><ErrorState message={caseListResult.data?.message ?? "Frozen probability case catalogue unavailable."} /></div>;
  }
  if (caseListResult.data.mode === "INTEGRITY_FAILURE") {
    return <div className="page-content"><ErrorState message={`Scientific artifact integrity check failed: ${caseListResult.data.message}. This is a hard failure and is not masked by cached data.`} /></div>;
  }

  const unavailableNote = (label: string) => <div className="phase5-analysis-block"><h2>{label} unavailable for {year}</h2>{availability?.notes.length ? availability.notes.map((note) => <p key={note}>{note}</p>) : <p>This product does not exist in the frozen {year} corpus.</p>}</div>;

  return <div className="page-content phase5-extremes">
    <PageHeading title="Extreme Rain" subtitle={`${availability?.role_label ?? year} · calibrated probability and separate spatial verification`} action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}>{indicatorMode ? <DataSourceIndicator mode={indicatorMode} /> : null}<PrototypeNote /></span>} />
    <div className="phase5-context-strip"><strong>{year} · {availability?.role_label ?? ""}</strong>{population ? <PopulationBadge cases={population.case_count} cells={population.cell_count} /> : null}<span>Not live warning guidance</span></div>
    <div className="phase5-controls"><label>Year<select value={year} onChange={(change) => { setYear(operationalYearSchema.parse(Number(change.target.value))); setCaseId(""); }}>{YEARS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label></div>
    <div className="phase5-tab-row" role="group" aria-label="Rainfall threshold"><button type="button" aria-pressed={event === "heavy"} onClick={() => setEvent("heavy")}>Heavy ≥{thresholds.heavy} mm / 24 h</button><button type="button" aria-pressed={event === "very_heavy"} onClick={() => setEvent("very_heavy")}>Very Heavy ≥{thresholds.veryHeavy} mm / 24 h</button></div>
    <div className="phase5-tab-row" role="group" aria-label="Extreme analysis mode">{(["probability", "detection", "spatial", "reliability"] as const).map((item) => <button key={item} type="button" aria-pressed={mode === item} onClick={() => setMode(item)}>{item === "spatial" ? "Spatial skill / FSS" : item[0].toUpperCase() + item.slice(1)}</button>)}</div>

    {mode === "probability" ? (!eventProbabilityAvailable ? unavailableNote("Calibrated probability") : <>
      {probabilityMetricsResult.isPending ? <LoadingState /> : !metric ? <ErrorState message="Probability quality metrics are unavailable." /> : <>
        <ProbabilityQualityCards metric={metric} />
        {metric.categorical.metrics.FAR >= 0.5 ? <p className="phase5-caveat">Discrimination and calibration remain limited by rare events at this threshold; the false-alarm ratio is high (FAR {metric.categorical.metrics.FAR.toFixed(3)}).</p> : null}
      </>}
      <div className="phase5-controls"><label>Historical case<select value={selectedCase?.case_id ?? ""} onChange={(change) => { setCaseId(change.target.value); setSelected(null); }}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.initialization_utc.slice(0, 10)} · {item.lead_label}</option>)}</select></label>{metric ? <span className="phase5-control-note">Frozen decision threshold: {metric.categorical.decision_threshold_probability.toFixed(2)} · probability scale 0–100%</span> : null}</div>
      {probabilityFieldResult.isPending ? <LoadingState /> : probabilityFieldResult.isError || !values || !grid || !mask ? <ErrorState message="The calibrated probability grid is unavailable for this case." /> : <>
        <div className="phase5-prob-map"><GridMap id="operational-probability" title={`${event === "heavy" ? "Heavy" : "Very Heavy"} calibrated probability`} subtitle={`P(IMD ≥${threshold} mm / 24 h) · ${year} · ${selectedCase?.lead_label ?? ""} · ${availability?.role_label ?? ""}`} values={values} mask={mask} grid={grid} palette="probability" geometry={geometry.data?.geometry} selected={selected} onSelect={setSelected} /></div><ProbabilityLegend />
        {selected ? <p className="phase5-legend-note">Selected {grid.latitude_centers[selected.row].toFixed(2)}° N, {grid.longitude_centers[selected.column].toFixed(2)}° E: {(() => { const point = values[selected.row]?.[selected.column]; return point != null ? `${(100 * point).toFixed(1)}%` : "masked IMD cell"; })()}</p> : null}
        <p className="phase5-legend-note">Historical case inspection only -- not a live warning issuance.</p>
      </>}
    </>) : null}

    {mode === "detection" ? (!detectionAvailable ? unavailableNote("Deterministic event detection") : <div className="phase5-analysis-block">
      <h2>Thresholded event detection · Raw versus M1–M4</h2>
      <p>Each model&rsquo;s own deterministic rainfall forecast thresholded at IMD ≥{threshold} mm / 24 h -- distinct from the calibrated-probability model&rsquo;s own detection metrics shown in Probability mode.</p>
      {population ? <PopulationBadge cases={population.case_count} cells={population.cell_count} /> : null}
      {deterministicResult.isPending ? <LoadingState /> : <DeterministicCategoricalTable metrics={deterministicMetrics} event={event} modelNames={modelNames} />}
      <p className="phase5-caveat">Do not collapse POD/FAR/CSI/ETS into one &ldquo;accuracy&rdquo; score -- each answers a different verification question and none replaces spatial (FSS) or probabilistic verification.</p>
    </div>) : null}

    {mode === "spatial" ? (!fssAvailable ? unavailableNote("Fractions Skill Score") : <div className="phase5-analysis-block">
      <h2>Fractions Skill Score · Raw versus preselected M1</h2>
      <p>Matched paired 2-D cases, frozen ≥50% valid-neighborhood rule. Higher is better; sample denominators vary by threshold.</p>
      {fssResult.isPending ? <LoadingState /> : fssResult.isError || !fssEvent ? <ErrorState message="Spatial skill (FSS) results are unavailable." /> : <>
        <OperationalFssChart fss={fssEvent} selectedModelLabel="M1 Ridge MOS" />
        <table className="phase5-table"><thead><tr><th>Neighborhood</th><th>Raw FSS</th><th>M1 FSS</th><th>Cases</th></tr></thead><tbody>{(["1", "3", "5", "9"] as const).map((scale) => <tr key={scale}><th>{scale}×{scale}</th><td>{fssEvent[scale].matched_raw.fss?.toFixed(4) ?? "Undefined"}</td><td>{fssEvent[scale].matched_selected.fss?.toFixed(4) ?? "Undefined"}</td><td>{fssEvent[scale].matched_case_count}</td></tr>)}</tbody></table>
      </>}
      <p className="phase5-caveat">Raw GEFS retained stronger extreme-rain spatial FSS than the RMSE-selected M1 at every tested scale. Lower overall RMSE did not translate into better extreme-rain spatial skill.</p>
    </div>) : null}

    {mode === "reliability" ? (!reliabilityAvailable ? unavailableNote("Reliability bins") : <div className="phase5-analysis-block">
      <h2>Reliability bins</h2>
      <p>Mean predicted probability versus observed frequency. Sparse upper bins are not evidence of stable calibration.</p>
      {!metric ? <ErrorState message="Reliability bins are unavailable." /> : <>
        <OperationalReliabilityChart metric={metric} />
        <table className="phase5-table"><thead><tr><th>Forecast bin</th><th>Mean predicted</th><th>Observed frequency</th><th>Cells</th></tr></thead><tbody>{metric.reliability.map((bin) => <tr key={bin.bin_lower}><th>{Math.round(bin.bin_lower * 100)}–{Math.round(bin.bin_upper * 100)}%</th><td>{bin.mean_predicted_probability == null ? "Undefined" : `${(100 * bin.mean_predicted_probability).toFixed(1)}%`}</td><td>{bin.observed_event_frequency == null ? "Undefined" : `${(100 * bin.observed_event_frequency).toFixed(1)}%`}</td><td>{bin.sample_count.toLocaleString()}</td></tr>)}</tbody></table>
      </>}
    </div>) : null}

    <p className="phase5-caveat">POST-HOC EXPLORATORY VIEW OF THE COMPLETED FINAL TEST. Frozen overall metrics remain the evidence; individual maps are historical case inspection, not a new evaluation. No PR/ROC curve is rendered anywhere on this page -- only the scalar PR-AUC/ROC-AUC the frozen artifacts actually carry.</p>
  </div>;
}
