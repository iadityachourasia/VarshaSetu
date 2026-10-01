"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { EvidenceApiError } from "@/lib/api/evidence";
import {
  FORCING_KEYS, STRATA, ZONE_LABEL, ZONE_NAMES, getZoneForcing, getZoneGeography, getZoneOverview, getZoneVerification,
  type ZoneForcing, type ZoneGeography, type ZoneName, type ZoneTrackYear, type ZoneVerification,
} from "@/lib/api/zones";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";

type Metric = "rmse_mm" | "bias_mm" | "CSI" | "frequency_bias";
const METRICS: { key: Metric; label: string; q1?: string; digits: number }[] = [
  { key: "rmse_mm", label: "RMSE (mm per 24 h)", q1: "rmse", digits: 2 },
  { key: "bias_mm", label: "Bias, forecast minus IMD (mm)", q1: "bias", digits: 2 },
  { key: "CSI", label: "Heavy-rain CSI", q1: "heavy_csi", digits: 3 },
  { key: "frequency_bias", label: "Heavy-rain frequency bias (forecast / observed events)", digits: 2 },
];
const LAYERS = [
  { key: "zone", label: "Zones" }, { key: "local_relief_m", label: "Local relief (m)" },
  { key: "mean_elevation_m", label: "Mean elevation (m)" }, { key: "distance_to_coast_km", label: "Distance to coast (km)" },
] as const;
type Layer = (typeof LAYERS)[number]["key"];
const RUNS: { id: string; label: string; ty: ZoneTrackYear }[] = [
  { id: "B-2025", label: "Track B 2025 · completed final test (post-hoc)", ty: { track: "B", year: 2025 } },
  { id: "B-2024", label: "Track B 2024 · development year", ty: { track: "B", year: 2024 } },
  { id: "A-2019", label: "Track A 2019 · completed final test (post-hoc)", ty: { track: "A", year: 2019 } },
  { id: "A-2018", label: "Track A 2018 · development year", ty: { track: "A", year: 2018 } },
];
const MODEL_LABEL: Record<string, string> = { M0: "M0 Raw", M1: "M1 Ridge", M2: "M2 Global ML", M3: "M3 Hard regime", M4: "M4 Soft regime" };
const ZONE_FILL: Record<string, string> = { COASTAL: "var(--zone-coastal)", OROGRAPHIC: "var(--zone-orographic)", COASTAL_AND_OROGRAPHIC: "var(--zone-both)", OTHER: "var(--zone-other)" };
const COMPONENT_LABEL: Record<string, string> = { onshore: "onshore flow", cross_barrier: "cross-barrier flow" };
const STRATUM_LABEL: Record<string, string> = { weak: "Weak", middle: "Middle", strong: "Strong" };

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
const signed = (value: number, digits: number) => `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;

type Block = ZoneVerification["payload"]["pooled"][string][string];
function metricValue(block: Block | undefined, metric: Metric): number | null | "unsupported" {
  if (!block || block.status) return "unsupported";
  if (metric === "rmse_mm" || metric === "bias_mm") return block[metric] ?? null;
  const heavy = block.categorical?.heavy;
  if (!heavy || heavy.status) return "unsupported";
  return metric === "CSI" ? heavy.CSI ?? null : heavy.frequency_bias ?? null;
}
const cell = (value: number | null | "unsupported", digits: number) => (value === "unsupported" ? "insufficient support" : fixed(value, digits));

function rampColor(t: number) {
  const stops = [[68, 1, 84], [49, 104, 142], [33, 145, 140], [94, 201, 98], [253, 231, 37]];
  const x = Math.min(0.999, Math.max(0, t)) * (stops.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const c = stops[i].map((v, k) => Math.round(v + (stops[i + 1][k] - v) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

function ZoneMap({ geography, layer }: { geography: ZoneGeography; layer: Layer }) {
  const rows = geography.fields.zone;
  const lat = geography.grid.latitude_centers;
  const lon = geography.grid.longitude_centers;
  const values = layer === "zone" ? null : geography.fields[layer];
  const range = useMemo(() => {
    if (!values) return null;
    const flat = values.flat().filter((v): v is number => v != null && Number.isFinite(v));
    return { min: Math.min(...flat), max: Math.max(...flat) };
  }, [values]);
  const size = 12;
  const n = rows.length;
  return <figure className="zone-map-figure">
    <svg className="zone-map" viewBox={`0 0 ${n * size} ${n * size}`} role="img"
      aria-label={`Map of the ${n} by ${n} land grid, 10 to 22 degrees north and 68 to 80 degrees east, coloured by ${LAYERS.find((l) => l.key === layer)?.label}`}>
      {rows.map((row, i) => row.map((label, j) => {
        if (label == null) return null;
        const v = values?.[i][j];
        const fill = values && range ? (v == null ? "var(--line)" : rampColor((v - range.min) / Math.max(1e-9, range.max - range.min))) : ZONE_FILL[label];
        return <rect key={`${i}-${j}`} x={j * size} y={(n - 1 - i) * size} width={size} height={size} fill={fill}>
          <title>{`${lat[i].toFixed(2)}°N ${lon[j].toFixed(2)}°E · ${ZONE_LABEL[label as ZoneName] ?? label}${v != null ? ` · ${v.toFixed(1)}` : ""}`}</title>
        </rect>;
      }))}
    </svg>
    <figcaption className="micro-note">
      North is up. {range ? `${LAYERS.find((l) => l.key === layer)?.label}: dark to bright from ${range.min.toFixed(0)} to ${range.max.toFixed(0)}.` : "Colours show the four rule-based zones; counts are in the legend."}
    </figcaption>
  </figure>;
}

function SkillTable({ data, metric }: { data: ZoneVerification; metric: Metric }) {
  const { payload } = data;
  const def = METRICS.find((m) => m.key === metric)!;
  const allEvents = payload.support.ALL.heavy.observed_event_pairs;
  const zones = ["ALL", ...ZONE_NAMES];
  return <div className="district-table-wrap"><table className="phase5-table zone-table">
    <caption className="sr-only">{def.label} by zone and model</caption>
    <thead><tr><th scope="col">Zone</th><th scope="col">Cells</th><th scope="col">Heavy events (share)</th>
      {payload.models.map((m) => <th scope="col" key={m}>{MODEL_LABEL[m] ?? m}</th>)}</tr></thead>
    <tbody>{zones.map((zone) => {
      const events = payload.support[zone].heavy.observed_event_pairs;
      return <tr key={zone}><th scope="row">{zone === "ALL" ? "All land cells" : ZONE_LABEL[zone as ZoneName]}</th>
        <td>{payload.zones[zone].cells.toLocaleString("en-GB")}</td>
        <td>{events.toLocaleString("en-GB")} ({allEvents ? `${Math.round((100 * events) / allEvents)} %` : "undefined"})</td>
        {payload.models.map((m) => <td key={m}>{cell(metricValue(payload.pooled[zone]?.[m], metric), def.digits)}</td>)}</tr>;
    })}</tbody></table></div>;
}

function DifferenceTable({ data, metric }: { data: ZoneVerification; metric: Metric }) {
  const def = METRICS.find((m) => m.key === metric)!;
  const { payload } = data;
  if (!def.q1) return <p className="micro-note">Heavy-rain frequency bias is shown pooled above; the pre-registered zone-versus-all-cells comparison covers RMSE, bias and heavy CSI.</p>;
  const statText = (stat: { status: string; point?: number | null; interval95?: [number, number]; excludes_zero?: boolean } | undefined) => {
    if (!stat || stat.status !== "ok" || stat.point == null || !stat.interval95) return stat?.status === "insufficient_support" ? "insufficient support" : "not reported";
    return `${signed(stat.point, def.digits)} [${signed(stat.interval95[0], def.digits)}, ${signed(stat.interval95[1], def.digits)}] ${stat.excludes_zero ? "· excludes 0" : "· includes 0"}`;
  };
  return <div className="district-table-wrap"><table className="phase5-table zone-table">
    <caption className="sr-only">Zone value minus all-cell value with 95 percent paired whole-case bootstrap interval</caption>
    <thead><tr><th scope="col">Zone minus all cells</th>{payload.models.map((m) => <th scope="col" key={m}>{MODEL_LABEL[m] ?? m}</th>)}</tr></thead>
    <tbody>{ZONE_NAMES.map((zone) => <tr key={zone}><th scope="row">{ZONE_LABEL[zone]}</th>
      {payload.models.map((m) => <td key={m}>{statText(payload.differences.q1[zone]?.[m]?.[def.q1!])}</td>)}</tr>)}</tbody></table></div>;
}

function ForcingSection({ data }: { data: ZoneForcing }) {
  const { payload } = data;
  return <section className="phase5-analysis-block" aria-labelledby="zone-forcing-heading">
    <h2 id="zone-forcing-heading">Forecast-time forcing strength inside the zones</h2>
    <p>Forcing is the onshore or cross-barrier component of the forecast 850 hPa wind multiplied by precipitable water. Weak, middle and strong are terciles whose cut-points were fitted on the training year ({payload.forcing_cut_points.year}) only. No observation enters the forcing.</p>
    {FORCING_KEYS.map((key) => {
      const [zone, component] = key.split("|");
      const cut = payload.forcing_cut_points.cut_points[key];
      const events = STRATA.map((s) => payload.support[`${key}|${s}`].heavy_observed_event_pairs);
      const total = events.reduce((a, b) => a + b, 0);
      return <div key={key} className="zone-forcing-block">
        <h3>{ZONE_LABEL[zone as ZoneName]} · {COMPONENT_LABEL[component]}</h3>
        <p className="micro-note">Training-year cut-points: lower {fixed(cut.q33, 1)}, upper {fixed(cut.q67, 1)}{cut.q33 === 0 ? " (a lower cut of zero means the weak group includes every pair with no such flow)" : ""}.</p>
        <div className="district-table-wrap"><table className="phase5-table zone-table">
          <caption className="sr-only">Heavy-rain frequency bias by forcing stratum</caption>
          <thead><tr><th scope="col">Stratum</th><th scope="col">Cell-case pairs</th><th scope="col">Heavy events (share)</th>{payload.models.map((m) => <th scope="col" key={m}>{MODEL_LABEL[m] ?? m}</th>)}</tr></thead>
          <tbody>{STRATA.map((s, i) => {
            const name = `${key}|${s}`;
            return <tr key={s}><th scope="row">{STRATUM_LABEL[s]}</th>
              <td>{payload.support[name].cell_case_pairs.toLocaleString("en-GB")}</td>
              <td>{events[i].toLocaleString("en-GB")} ({total ? `${Math.round((100 * events[i]) / total)} %` : "undefined"})</td>
              {payload.models.map((m) => <td key={m}>{cell(metricValue(payload.pooled[name]?.[m], "frequency_bias"), 2)}</td>)}</tr>;
          })}</tbody></table></div>
      </div>;
    })}
    <p className="micro-note">Cells show heavy-rain frequency bias: forecast heavy events divided by observed heavy events. A stratum without enough observed events is not scored.</p>
  </section>;
}

export function ZoneEvidence() {
  const [runId, setRunId] = useState(RUNS[0].id);
  const [metric, setMetric] = useState<Metric>("frequency_bias");
  const [layer, setLayer] = useState<Layer>("zone");
  const run = RUNS.find((r) => r.id === runId)!;
  const overview = useQuery({ queryKey: ["zones-overview"], queryFn: () => getZoneOverview(), staleTime: 5 * 60_000 });
  const geography = useQuery({ queryKey: ["zones-geography"], queryFn: () => getZoneGeography(), staleTime: 5 * 60_000 });
  const verification = useQuery({ queryKey: ["zones-verification", run.ty], queryFn: () => getZoneVerification(run.ty), staleTime: 5 * 60_000 });
  const forcing = useQuery({ queryKey: ["zones-forcing", run.ty], queryFn: () => getZoneForcing(run.ty), staleTime: 5 * 60_000 });

  const failed = [overview, geography, verification, forcing].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <div className="page-content"><ErrorState message={integrity ? `Zone evidence integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "Zone evidence is unavailable."} /></div>;
  }
  if (!overview.data || !geography.data || !verification.data || !forcing.data) return <div className="page-content"><LoadingState label="Loading zone evidence" /></div>;
  const ov = overview.data;
  const geo = geography.data;
  const ver = verification.data;
  const postHoc = /POST-HOC/.test(ver.evidence_label);
  const def = METRICS.find((m) => m.key === metric)!;

  return <div className="page-content zones-page">
    <PageHeading title="Geographic Forcing Zones" subtitle="Coastal and orographic stratification of frozen model skill · rule-based zones, not a validated regime" action={<PrototypeNote />} />
    <div className={postHoc ? "zone-banner zone-banner-posthoc" : "zone-banner"} role="note"><strong>{ver.evidence_label}</strong>
      <span>{ver.payload.case_count} cases · reproduces the published verification exactly · paired whole-case bootstrap ({ver.payload.bootstrap.repeats} resamples, optimistic)</span></div>
    <div className="phase5-controls">
      <label>Population<select value={runId} onChange={(event) => setRunId(event.target.value)}>{RUNS.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}</select></label>
      <label>Score<select value={metric} onChange={(event) => setMetric(event.target.value as Metric)}>{METRICS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}</select></label>
      <label>Map layer<select value={layer} onChange={(event) => setLayer(event.target.value as Layer)}>{LAYERS.map((l) => <option key={l.key} value={l.key}>{l.label}</option>)}</select></label>
    </div>

    <div className="zone-top">
      <section className="phase5-analysis-block" aria-labelledby="zone-map-heading"><h2 id="zone-map-heading">Where the zones are</h2>
        <ZoneMap geography={geo} layer={layer} />
        <ul className="zone-legend">{ZONE_NAMES.map((z) => <li key={z}><i style={{ background: ZONE_FILL[z] }} aria-hidden="true" /><span><strong>{ZONE_LABEL[z]}</strong> · {geo.zone_cell_counts[z]} cells<br /><span className="micro-note">{geo.zone_notes[z]}</span></span></li>)}</ul>
      </section>
      <section className="phase5-analysis-block" aria-labelledby="zone-what-heading"><h2 id="zone-what-heading">What this view shows</h2>
        <p>The frozen forecasts and IMD observations are unchanged. Every land cell belongs to exactly one zone (coast distance on a 0.25° land grid, local terrain relief), and the same verification used elsewhere is recomputed inside each zone.</p>
        <ul className="phase5-caveats">{ov.caveats.slice(0, 5).map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
      </section>
    </div>

    <section className="phase5-analysis-block" aria-labelledby="zone-skill-heading">
      <h2 id="zone-skill-heading">{def.label} by zone</h2>
      <SkillTable data={ver} metric={metric} />
      {def.q1 ? <h3>Zone minus all cells, with 95 % interval</h3> : null}
      <DifferenceTable data={ver} metric={metric} />
      <p className="micro-note">{ver.payload.fss.reason}</p>
    </section>

    <ForcingSection data={forcing.data} />

    <section className="phase5-analysis-block" aria-labelledby="zone-rule-heading"><h2 id="zone-rule-heading">Pre-registered decision rule, applied literally</h2>
      <p>{ov.decision_stage1.rule}</p>
      <div className="phase5-metric-strip">{Object.entries(ov.decision_stage1.tracks).map(([track, t]) => <span key={track}>
        <b>Track {track}</b> {t.geographic_gaps ?? 0} of {t.tests} tests flagged · about {t.expected_gaps_by_chance} expected by chance</span>)}</div>
      <p className="phase5-caveat"><b>Read with care: </b>zones are different rainfall climates, so even Raw differs between them and many flags reflect that, not a model failure. The interior zone covers most cells, so its difference from all cells is partly arithmetic. The result worth acting on is the specific, repeated deficiency on the Ghats coast shown in the tables above, not the count of flags.</p>
      <p>Forcing-strength comparison (descriptive only): {Object.entries(ov.decision_stage2.tracks).map(([track, t]) => `Track ${track}: ${t.forcing_gaps ?? 0} of ${t.tests}`).join(" · ")} tests flagged.</p>
      <p className="micro-note">Stage 3, a geography-aware model, is {ov.stage_3_authorised ? "authorised" : "not authorised"}: it needs its own frozen protocol and approval, and it must beat the strongest non-regime model on held-out data.</p>
    </section>

    <p className="micro-note">Frozen protocol v3 {ov.protocol_sha256.slice(0, 12)}… · geography {ov.geography_sha256.slice(0, 12)}… · Stage 1 manifest {ov.stage1_manifest_sha256.slice(0, 12)}… · Stage 2 manifest {ov.stage2_manifest_sha256.slice(0, 12)}… ·
      Terrain: {geo.source.original}; {geo.source.attribution}. Historical scientific prototype, not an operational service.</p>
  </div>;
}
