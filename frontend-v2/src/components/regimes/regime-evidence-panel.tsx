"use client";

import { ForestPlot } from "@/components/science/forest-plot";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/science/common";
import {
  BOOTSTRAP_PAIRS, EVIDENCE_MODELS, EVIDENCE_REGIMES, EVIDENCE_SCALES, EVIDENCE_YEARS, EvidenceApiError, getRegimeEvidence,
  type BootstrapStat, type EvidenceBlock, type EvidenceModel, type EvidenceScale, type EvidenceThreshold, type RegimeEvidence,
} from "@/lib/api/evidence";
import { regimeName } from "@/lib/format";
import { HashChip } from "@/components/ui/hash-chip";
import { DownloadLink } from "@/components/ui/download-link";

type MetricKey = "rmse_mm" | "mae_mm" | "bias_mm" | "POD" | "FAR" | "CSI" | "ETS" | "FSS" | "freq";
const METRICS: { key: MetricKey; label: string; group: "continuous" | "event" }[] = [
  { key: "rmse_mm", label: "RMSE", group: "continuous" }, { key: "mae_mm", label: "MAE", group: "continuous" },
  { key: "bias_mm", label: "Bias", group: "continuous" }, { key: "POD", label: "POD", group: "event" },
  { key: "FAR", label: "FAR", group: "event" }, { key: "CSI", label: "CSI", group: "event" },
  { key: "ETS", label: "ETS", group: "event" }, { key: "FSS", label: "FSS", group: "event" },
  { key: "freq", label: "Forecast / observed events", group: "event" },
];
const MODEL_LABEL: Record<EvidenceModel, string> = {
  M0: "M0 Raw", M1: "M1 Ridge", M2: "M2 Global ML", M3: "M3 Hard regime", M4: "M4 Soft regime",
};
const PAIR_LABEL: Record<string, string> = {
  M3_minus_M0: "M3 − Raw", M3_minus_M2: "M3 − M2", M4_minus_M0: "M4 − Raw", M4_minus_M2: "M4 − M2",
  M2_minus_M0: "M2 − Raw", M3_minus_M4: "M3 − M4",
};
const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));

function cellValue(block: EvidenceBlock, model: EvidenceModel, metric: MetricKey, threshold: EvidenceThreshold, scale: EvidenceScale) {
  if (metric === "rmse_mm" || metric === "mae_mm" || metric === "bias_mm") {
    return { text: fixed(block.continuous[model][metric], 2), note: null as string | null };
  }
  if (metric === "FSS") {
    const score = block.fss[threshold][scale].all_cases[model];
    return { text: fixed(score.fss, 3), note: `n=${score.case_count}` };
  }
  const event = block.categorical[threshold][model];
  if (metric === "freq") {
    return { text: event.observed_event_count ? fixed(event.forecast_event_count / event.observed_event_count, 3) : "undefined", note: `obs ${event.observed_event_count}` };
  }
  return { text: fixed(event[metric], 3), note: null };
}

function DataTable({ caption, rows, metric, threshold, scale }: {
  caption: string; rows: { label: string; detail: string; block: EvidenceBlock | undefined }[];
  metric: MetricKey; threshold: EvidenceThreshold; scale: EvidenceScale;
}) {
  return <div className="district-table-wrap"><table className="phase5-table regime-evidence-table">
    <caption className="sr-only">{caption}</caption>
    <thead><tr><th scope="col">Group</th>{EVIDENCE_MODELS.map((model) => <th scope="col" key={model}>{MODEL_LABEL[model]}</th>)}</tr></thead>
    <tbody>{rows.map((row) => <tr key={row.label}>
      <th scope="row">{row.label}<span className="micro-note"> {row.detail}</span></th>
      {EVIDENCE_MODELS.map((model) => {
        const cell = row.block ? cellValue(row.block, model, metric, threshold, scale) : { text: "unavailable", note: null };
        return <td key={model}>{cell.text}{cell.note ? <span className="micro-note"> · {cell.note}</span> : null}</td>;
      })}
    </tr>)}</tbody>
  </table></div>;
}

function ciText(stat: BootstrapStat | undefined) {
  if (!stat || stat.status !== "ok" || stat.point === undefined || !stat.interval95) return stat ? `not reported (${stat.status})` : "not reported";
  const [low, high] = stat.interval95;
  const excludes = low > 0 || high < 0;
  // Four decimals so a bound very close to zero is not displayed as "0.000" next to "excludes 0".
  return `${stat.point >= 0 ? "+" : ""}${stat.point.toFixed(4)} [${low.toFixed(4)}, ${high.toFixed(4)}]${excludes ? " · interval excludes 0" : " · includes 0"}`;
}

function regimeRows(data: RegimeEvidence) {
  return [
    ...EVIDENCE_REGIMES.map((name) => ({ label: regimeName(name), detail: `${data.by_predicted_regime[name]?.case_count ?? 0} cases`, block: data.by_predicted_regime[name] })),
    { label: "All cases", detail: `${data.overall.case_count} cases`, block: data.overall },
  ];
}
function leadRows(data: RegimeEvidence) {
  return Object.entries(data.by_lead_day).map(([key, block]) => ({ label: key.replace("day", "Day "), detail: `${block.case_count} cases`, block }));
}

export function RegimeEvidencePanel({ track, year }: { track: "A" | "B"; year: number }) {
  const [metric, setMetric] = useState<MetricKey>("CSI");
  const [threshold, setThreshold] = useState<EvidenceThreshold>("heavy");
  const [scale, setScale] = useState<EvidenceScale>("3");
  const supported = EVIDENCE_YEARS[track].includes(year);
  const query = useQuery({ queryKey: ["regime-evidence", track, year], queryFn: () => getRegimeEvidence(track, year), enabled: supported, staleTime: 5 * 60_000 });

  if (!supported) {
    return <section className="phase5-analysis-block" aria-labelledby="regime-evidence-title"><h2 id="regime-evidence-title">Regime-aware verification</h2>
      <p>No regime-stratified verification is published for {track === "A" ? "Track A" : "Track B"} {year}: it is {year === 2017 || year === 2023 ? "a training / cross-fit year, so models were fitted on it and were not scored against it" : "outside the evidence set"}. Published populations: {EVIDENCE_YEARS[track].join(" and ")}.</p></section>;
  }
  if (query.isPending) return <LoadingState compact label="Loading regime-aware verification evidence" />;
  if (query.isError || !query.data) {
    const error = query.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <ErrorState message={integrity ? `Evidence integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "Regime-aware verification evidence is unavailable."} />;
  }
  const data = query.data;
  const isEvent = METRICS.find((item) => item.key === metric)?.group === "event";
  const raw = data.overall.continuous.M0.rmse_mm;
  const postHoc = /POST-HOC/.test(data.evidence_label);

  return <section className="phase5-analysis-block regime-evidence" aria-labelledby="regime-evidence-title">
    <h2 id="regime-evidence-title">Regime-aware correction · verification by forecast-only regime and lead</h2>
    <p className={postHoc ? "phase5-caveat" : undefined}><strong>{data.evidence_label}</strong>. Track {data.track} · {data.year} · {data.summary.case_count} cases · {data.summary.cell_count.toLocaleString("en-GB")} paired cells.
      Frozen models re-aggregated only; nothing was trained, tuned or selected for this view. Reproduction of the frozen numbers: {data.reproduction.status} ({data.reproduction.check_count} checks, max difference {data.reproduction.max_abs_diff.toExponential(1)}). Evidence SHA-256 <HashChip hash={data.evidence_sha256} /></p>

    <p className="regime-evidence-downloads"><strong>Verification report</strong> (generated from this hash-verified evidence; RMSE, MAE, bias, POD, FAR, CSI, ETS and FSS by regime and lead):{" "}
      {(["md", "csv", "json"] as const).map((format, index) => <span key={format}>{index ? " · " : ""}<DownloadLink href={`/api/science/evidence/report?track=${track}&year=${year}&format=${format}`}>{format === "md" ? "Markdown" : format.toUpperCase()}</DownloadLink></span>)}</p>
    <div className="phase5-metric-strip" aria-label="RMSE change relative to Raw NWP">
      {EVIDENCE_MODELS.filter((model) => model !== "M0").map((model) => {
        const value = data.overall.continuous[model].rmse_mm;
        const change = raw && value != null ? (value - raw) / raw * 100 : null;
        return <span key={model}><b>{MODEL_LABEL[model]}</b> RMSE {fixed(value, 2)} mm{change == null ? "" : ` (${change <= 0 ? "" : "+"}${change.toFixed(2)}% vs Raw ${fixed(raw, 2)} mm)`}</span>;
      })}
    </div>

    <div className="phase5-tab-row" role="group" aria-label="Verification metric">{METRICS.map((item) => <button key={item.key} type="button" aria-pressed={metric === item.key} onClick={() => setMetric(item.key)}>{item.label}</button>)}</div>
    <div className="phase5-controls">
      <div className="phase5-tab-row" role="group" aria-label="Rainfall threshold for event metrics, FSS and paired differences"><button type="button" aria-pressed={threshold === "heavy"} onClick={() => setThreshold("heavy")}>Heavy ≥ 64.5 mm / 24 h</button><button type="button" aria-pressed={threshold === "very_heavy"} onClick={() => setThreshold("very_heavy")}>Very Heavy ≥ 115.6 mm / 24 h</button></div>
      {metric === "FSS" ? <div className="phase5-tab-row" role="group" aria-label="FSS neighborhood">{EVIDENCE_SCALES.map((item) => <button key={item} type="button" aria-pressed={scale === item} onClick={() => setScale(item)}>{item}×{item}</button>)}</div> : null}
    </div>
    {isEvent ? null : <p className="micro-note">RMSE, MAE and bias are continuous and do not depend on the threshold; the threshold buttons still switch the paired-difference table below.</p>}

    <h3>By forecast-only pseudo-regime</h3>
    <DataTable caption={`${METRICS.find((item) => item.key === metric)?.label} by forecast-only pseudo-regime`} rows={regimeRows(data)} metric={metric} threshold={threshold} scale={scale} />
    <h3>By lead day</h3>
    <DataTable caption={`${METRICS.find((item) => item.key === metric)?.label} by lead day`} rows={leadRows(data)} metric={metric} threshold={threshold} scale={scale} />
    {metric === "FSS" ? <p className="micro-note">FSS: each model is scored on its own defined cases (n shown). A case is undefined when neither forecast nor observation has an event in an eligible neighborhood. Undefined cases at this scale, Raw / M2 / M3 / M4: {(["M0", "M2", "M3", "M4"] as const).map((model) => data.summary.undefined_fss_cases[threshold][scale][model]).join(" / ")}.</p> : null}
    {metric === "freq" ? <p className="micro-note">Values near 0 mean the model forecasts almost no events at this threshold (event suppression); 1 is an unbiased event frequency.</p> : null}

    <h3>Paired differences over all cases (case-cluster bootstrap)</h3>
    <div className="forest-grid" data-testid="regime-forest">
      {([["CSI", "Δ CSI"], ["FSS_3x3", "Δ FSS 3×3"], ["FSS_9x9", "Δ FSS 9×9"]] as const).map(([key, title], index) => <ForestPlot key={key} title={title} showLabels={index === 0} width={index === 0 ? 520 : 350}
        rows={BOOTSTRAP_PAIRS.map((pair) => { const stat = data.bootstrap.overall[threshold][pair]?.[key]; const ok = stat?.status === "ok" && stat.point !== undefined && stat.interval95; return { label: PAIR_LABEL[pair], point: ok ? stat.point ?? null : null, low: ok ? stat.interval95![0] : null, high: ok ? stat.interval95![1] : null }; })} />)}
    </div>
    <div className="district-table-wrap"><table className="phase5-table regime-evidence-table"><caption className="sr-only">Paired bootstrap differences in CSI and FSS for {threshold === "heavy" ? "heavy" : "very heavy"} rain</caption>
      <thead><tr><th scope="col">Contrast</th><th scope="col">Δ CSI [95 % interval]</th><th scope="col">Δ FSS 3×3 [95 % interval]</th><th scope="col">Δ FSS 9×9 [95 % interval]</th></tr></thead>
      <tbody>{BOOTSTRAP_PAIRS.map((pair) => { const row = data.bootstrap.overall[threshold][pair]; return <tr key={pair}><th scope="row">{PAIR_LABEL[pair]}</th><td>{ciText(row?.CSI)}</td><td>{ciText(row?.FSS_3x3)}</td><td>{ciText(row?.FSS_9x9)}</td></tr>; })}</tbody></table></div>
    <p className="micro-note">Positive Δ means the first model scores higher. Intervals resample whole cases and ignore serial correlation between days, so they are optimistic.</p>

    <h3>Method and limitations</h3>
    <ul className="phase5-caveats">{data.caveats.map((caveat) => <li className="phase5-caveat" key={caveat}>{caveat}</li>)}<li className="phase5-caveat">Regime assignment: {data.regime_assignment}.</li></ul>
  </section>;
}
