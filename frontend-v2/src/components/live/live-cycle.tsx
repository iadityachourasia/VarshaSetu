"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeading } from "@/components/science/common";
import { EvidenceApiError } from "@/lib/api/evidence";
import { LIVE_FIELDS, getLiveCycle, getLiveDistricts, getLiveField, getLiveStatus, type LiveCycle, type LiveField } from "@/lib/api/live";
import { HashChip } from "@/components/ui/hash-chip";

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
const PRODUCT_LABEL: Record<string, string> = { day1_24h: "Day 1 (+3 to +27 h)", day2_24h: "Day 2 (+27 to +51 h)", day3_24h: "Day 3 (+51 to +75 h)" };
const REGIME_LABEL: Record<string, string> = { ACTIVE_MONSOON: "Active monsoon (pseudo-regime)", BREAK_WEAK_MONSOON: "Break / weak monsoon (pseudo-regime)", LOW_DEPRESSION_INFLUENCED: "Low / depression influenced (pseudo-regime)" };
const withheldSummary = (reason: string) => reason.includes("negative difference exceeds packing bound")
  ? "Rainfall increments exceeded the GRIB packing tolerance; canonical quality control withheld this lead."
  : "Canonical rainfall reconstruction failed; quality control withheld this lead.";

function ramp(t: number): string {
  const x = Math.min(1, Math.max(0, t));
  const stops = [[247, 251, 255], [158, 202, 225], [49, 130, 189], [8, 48, 107]];
  const i = Math.min(2, Math.floor(x * 3));
  const f = x * 3 - i;
  return `rgb(${stops[i].map((c, k) => Math.round(c + (stops[i + 1][k] - c) * f)).join(",")})`;
}

function Heatmap({ field }: { field: LiveField }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const flat = field.values.flat();
  const low = 0;
  const high = Math.max(...flat, 1e-9);
  useEffect(() => {
    const context = canvas.current?.getContext("2d");
    if (!context) return;
    const size = 10;
    field.values.forEach((row, i) => row.forEach((value, j) => {
      context.fillStyle = ramp((value - low) / (high - low));
      context.fillRect(j * size, (48 - i) * size, size, size);      // latitude ascends upward
    }));
  }, [field, high]);
  const digits = field.units === "probability" ? 3 : 1;
  return <figure className="live-map" data-testid="live-map">
    <div className="live-map-frame">
      <span className="live-axis live-axis-n">22° N</span><span className="live-axis live-axis-s">10° N</span>
      <canvas ref={canvas} width={490} height={490} role="img" aria-label={`${field.label}, ${field.product}, cycle ${field.cycle}: 49 by 49 grid, 10 to 22 N, 68 to 80 E`} />
    </div>
    <div className="live-axis-x"><span>68° E</span><span>80° E</span></div>
    <div className="live-ramp" aria-hidden="true"><span>0</span><i style={{ background: `linear-gradient(90deg, ${[0, 0.25, 0.5, 0.75, 1].map((t) => ramp(t)).join(", ")})` }} /><span>{fixed(high, digits)}</span></div>
    <figcaption className="micro-note">{field.label} · {field.units} · 0 to {fixed(high, digits)} · 10 to 22 N, 68 to 80 E (south at the bottom) · {field.valid_cells} valid cells · {field.source_track} · {field.model_id} · +{field.accumulation_window_hours[0]} to +{field.accumulation_window_hours[1]} h · array <HashChip hash={field.array_sha256} /> · manifest <HashChip hash={field.evidence_manifest_sha256} /></figcaption>
  </figure>;
}

function Detail({ kind, date }: { kind: string; date: string }) {
  const cycle = useQuery({ queryKey: ["live-cycle", kind, date], queryFn: () => getLiveCycle(kind, date) });
  const [product, setProduct] = useState<string>("");
  const [fieldName, setFieldName] = useState<string>("M2");
  const [showDistricts, setShowDistricts] = useState(false);
  const [districtModel, setDistrictModel] = useState<"M1" | "M2" | "M3" | "M4">("M2");
  const [districtFilter, setDistrictFilter] = useState("");
  const chosen = cycle.data ? (cycle.data.summary.products.includes(product) ? product : cycle.data.summary.products[0]) : "";
  const field = useQuery({ queryKey: ["live-field", kind, date, chosen, fieldName], queryFn: () => getLiveField(kind, date, chosen, fieldName), enabled: Boolean(chosen) });
  const districts = useQuery({ queryKey: ["live-districts", kind, date, chosen, districtModel], queryFn: () => getLiveDistricts(kind, date, chosen, districtModel), enabled: showDistricts && Boolean(chosen) });
  if (cycle.isError) return <ErrorState message={cycle.error instanceof EvidenceApiError && cycle.error.code === "SCIENCE_INTEGRITY_FAILURE" ? `Live bundle integrity check failed: ${cycle.error.message}. This is a hard failure.` : (cycle.error as Error).message} />;
  if (!cycle.data) return <LoadingState compact label="Loading the cycle" />;
  const c: LiveCycle = cycle.data;
  const replayWorst = c.replay_comparison ? Math.max(...Object.values(c.replay_comparison.products).flatMap((p) => Object.entries(p).filter(([k]) => k.endsWith("difference")).map(([, v]) => v))) : null;
  return <div data-testid="live-detail">
    {c.summary.season_scope === "OUTSIDE_JJAS_RESEARCH_SCOPE" ? <div className="zone-banner zone-banner-posthoc" role="note" data-testid="live-season-scope"><strong>Outside the June–September research season</strong><span>This cycle demonstrates forecast-only inference. The frozen rainfall and probability models were developed for monsoon-season cases; no October skill or reliability claim is supported.</span></div> : null}
    <div className="phase5-controls">
      <label>Lead<select value={chosen} onChange={(e) => setProduct(e.target.value)}>{c.summary.products.map((p) => <option key={p} value={p}>{PRODUCT_LABEL[p] ?? p}</option>)}</select></label>
      <label>Field<select value={fieldName} onChange={(e) => setFieldName(e.target.value)}>{LIVE_FIELDS.map((f) => <option key={f} value={f}>{c.fields[f]}</option>)}</select></label>
    </div>
    <p className="micro-note" data-testid="live-model-default">Default correction: M2 global XGBoost. M3 and M4 remain comparison arms; regime conditioning has not demonstrated added heavy-rain skill over the matched global control.</p>
    {field.data?.probability_status ? <div className="zone-banner zone-banner-posthoc" role="note" data-testid="live-probability-status"><strong>Research probability · reliability unverified for this cycle</strong><span>Threshold and 24-hour window are shown in the selected field. This is not a public warning probability.</span></div> : null}
    {Object.entries(c.summary.withheld_products).length ? <div className="zone-banner zone-banner-posthoc" role="note" data-testid="live-withheld"><strong>Withheld leads · canonical rainfall quality control</strong>
      {Object.entries(c.summary.withheld_products).map(([p, why]) => <div className="live-withheld-item" key={p}><span>{PRODUCT_LABEL[p] ?? p}: {withheldSummary(why)}</span><details><summary>Technical QC detail</summary><code>{why}</code></details></div>)}</div> : null}
    <div className="live-grid">
    {field.isError ? <ErrorState message={(field.error as Error).message} /> : field.data ? <Heatmap field={field.data} /> : <LoadingState compact label="Loading the field" />}
    <div className="live-side">
    <div className="district-table-wrap" tabIndex={0}><table className="phase5-table zone-table" data-testid="live-stats">
      <caption className="sr-only">Domain minimum, mean and maximum of each field for the selected lead</caption>
      <thead><tr><th scope="col">Field</th><th scope="col">Minimum</th><th scope="col">Mean</th><th scope="col">Maximum</th></tr></thead>
      <tbody>{LIVE_FIELDS.map((f) => { const s = c.domain_statistics[chosen]?.[f]; return <tr key={f}><th scope="row">{c.fields[f]}</th><td>{fixed(s?.min, 3)}</td><td>{fixed(s?.mean, 3)}</td><td>{fixed(s?.max, 3)}</td></tr>; })}</tbody></table></div>
    <h3>Regime probabilities for this lead (forecast-only pseudo-regimes, not meteorological accuracy)</h3>
    <ul className="live-regime-bars" data-testid="live-regime">{Object.entries(c.regime_probabilities[chosen] ?? {}).map(([name, p]) => <li key={name}><span>{REGIME_LABEL[name] ?? name}</span><i aria-hidden="true"><b style={{ width: `${Math.round(100 * p)}%` }} /></i><strong>{fixed(p, 3)}</strong></li>)}</ul>
    </div>
    </div>
    <p className="micro-note" data-testid="live-applicability">Applicability: {c.applicability ? `${c.applicability.status}${c.applicability.largest_share ? `; largest share of cells outside the 2023 training range ${fixed(100 * c.applicability.largest_share.share, 1)} % (${c.applicability.largest_share.feature}, ${PRODUCT_LABEL[c.applicability.largest_share.product] ?? c.applicability.largest_share.product})` : ""}. A range heuristic, not a validity test.` : "not computed for this bundle"}</p>
    {replayWorst != null ? <p className="micro-note" data-testid="live-replay-gate">Replay gate: the largest absolute difference between this path and the frozen 2025 artifacts is {replayWorst.toExponential(2)} (features, regime probabilities, M0 to M4 and probabilities over the paired cells).</p> : null}
    <p className="micro-note" data-testid="live-provenance">{c.messages} NOAA messages, {(c.transferred_bytes / 1e6).toFixed(2)} MB · manifest <HashChip hash={c.manifest_sha256} /> · frozen models {Object.entries(c.frozen_models).map(([k, v]) => `${k} ${v.slice(0, 8)}…`).join(", ")} · no observation read, no retraining or recalibration.</p>
    <section className="live-district-section" aria-label="Regional district forecast">
      <h2>Regional district forecast</h2>
      <p className="micro-note">Forecast-only area-weighted aggregates for districts overlapping 10–22° N, 68–80° E. The geometry is a simplified 2021 research boundary. A district mean probability is not the chance that any location in that district exceeds the threshold.</p>
      <button type="button" className="live-district-toggle" onClick={() => setShowDistricts((value) => !value)} aria-expanded={showDistricts} data-testid="live-district-toggle">{showDistricts ? "Hide district table" : "Load district table"}</button>
      {showDistricts ? <>
        <div className="phase5-controls">
          <label>Correction model<select value={districtModel} onChange={(e) => setDistrictModel(e.target.value as typeof districtModel)}>{(["M1", "M2", "M3", "M4"] as const).map((name) => <option key={name} value={name}>{c.fields[name]}</option>)}</select></label>
          <label>Find district<input value={districtFilter} onChange={(e) => setDistrictFilter(e.target.value)} placeholder="District name" /></label>
        </div>
        {districts.isError ? <ErrorState message={districts.error instanceof EvidenceApiError && districts.error.code === "SCIENCE_INTEGRITY_FAILURE" ? `District product integrity check failed: ${districts.error.message}. This is a hard failure.` : (districts.error as Error).message} /> : districts.data ? <>
          <p className="micro-note" data-testid="live-district-provenance">{districts.data.district_count} regional districts · {districts.data.withheld_district_count} withheld below {(districts.data.coverage_threshold_fraction * 100).toFixed(0)}% represented-grid coverage · {districts.data.source_track} · {districts.data.model_id} · {districts.data.season_scope === "OUTSIDE_JJAS_RESEARCH_SCOPE" ? "outside JJAS research scope" : "JJAS research scope"} · +{districts.data.accumulation_window_hours[0]} to +{districts.data.accumulation_window_hours[1]} h · manifest <HashChip hash={districts.data.evidence_manifest_sha256} /> · geometry <HashChip hash={districts.data.geometry_sha256} /> · weights <HashChip hash={districts.data.weights_sha256} /></p>
          <p className="phase5-caveat" data-testid="live-district-probability-status">Heavy ≥64.5 mm/24 h and very heavy ≥115.6 mm/24 h: research probabilities; reliability is unverified for this cycle. The displayed means are area averages, not district-wide exceedance chances or public warnings.</p>
          <div className="district-table-wrap" tabIndex={0}><table className="phase5-table zone-table" data-testid="live-district-table">
            <caption className="sr-only">Forecast-only regional district means for the chosen correction model</caption>
            <thead><tr><th scope="col">District</th><th scope="col">Cells</th><th scope="col">Grid coverage</th><th scope="col">Raw mean (mm)</th><th scope="col">Corrected mean (mm)</th><th scope="col">Heavy mean p</th><th scope="col">Very-heavy mean p</th></tr></thead>
            <tbody>{districts.data.districts.filter((row) => row.district_name.toLowerCase().includes(districtFilter.trim().toLowerCase())).map((row) => <tr key={row.district_id}><th scope="row">{row.district_name}</th><td>{row.valid_grid_cells}</td><td>{fixed(100 * row.weighted_grid_coverage_fraction, 0)}%</td><td>{fixed(row.raw_mean_mm, 1)}</td><td>{fixed(row.corrected_mean_mm, 1)}</td><td>{fixed(row.heavy_probability, 3)}</td><td>{fixed(row.very_heavy_probability, 3)}</td></tr>)}</tbody>
          </table></div>
          <ul className="phase5-caveats">{districts.data.caveats.slice(0, 3).map((item) => <li className="phase5-caveat" key={item}>{item}</li>)}</ul>
        </> : <LoadingState compact label="Loading verified district data" />}
      </> : null}
    </section>
  </div>;
}

export function LiveCyclePage() {
  const status = useQuery({ queryKey: ["live-status"], queryFn: () => getLiveStatus() });
  const [selected, setSelected] = useState<string>("");
  if (status.isError) return <div className="page-content"><PageHeading title="Experimental Live Cycle" subtitle="Frozen models applied to a new forecast cycle" /><ErrorState message={status.error instanceof EvidenceApiError && status.error.code === "SCIENCE_INTEGRITY_FAILURE" ? `Live bundle integrity check failed: ${status.error.message}. This is a hard failure.` : (status.error as Error).message} /></div>;
  if (!status.data) return <div className="page-content"><PageHeading title="Experimental Live Cycle" subtitle="Frozen models applied to a new forecast cycle" /><LoadingState compact label="Loading the experimental cycles" /></div>;
  const s = status.data;
  const keyOf = (c: { kind: string; cycle: string }) => `${c.kind}:${c.cycle}`;
  const current = s.cycles.find((c) => keyOf(c) === selected) ?? s.latest_live ?? s.cycles[0];
  return <div className="page-content">
    <PageHeading title="Experimental Live Cycle" subtitle="The frozen Track B models applied to a new NOAA GEFS cycle by a separate worker. Experimental, unverified, not an official warning." />
    <div className="zone-banner zone-banner-posthoc" role="note" data-testid="live-banner"><strong>{current ? current.label : "EXPERIMENTAL FORECAST: frozen models, no verification yet, not an official warning"}</strong>
      <span data-testid="live-status-message">{s.message}</span></div>
    {s.cycles.length ? <>
      <div className="phase5-controls"><label>Cycle<select value={current ? keyOf(current) : ""} onChange={(e) => setSelected(e.target.value)} data-testid="live-cycle-select">
        {s.cycles.map((c) => <option key={keyOf(c)} value={keyOf(c)}>{c.kind === "live" ? "Live" : "Replay"} · {c.cycle} · {c.age_days} d old{c.stale ? " (stale)" : ""}</option>)}</select></label></div>
      {current ? <Detail kind={current.kind} date={current.cycle} /> : null}
    </> : <EmptyState message="No cycle bundle exists. Run the worker (scripts/live/run_live_cycle.py) to publish one; nothing is shown until a verified bundle exists." />}
    <ul className="phase5-caveats">{s.caveats.map((t) => <li className="phase5-caveat" key={t}>{t}</li>)}</ul>
  </div>;
}
