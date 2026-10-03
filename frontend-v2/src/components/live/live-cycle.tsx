"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeading } from "@/components/science/common";
import { EvidenceApiError } from "@/lib/api/evidence";
import { LIVE_FIELDS, getLiveCycle, getLiveField, getLiveStatus, type LiveCycle, type LiveField } from "@/lib/api/live";

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
const PRODUCT_LABEL: Record<string, string> = { day1_24h: "Day 1 (+3 to +27 h)", day2_24h: "Day 2 (+27 to +51 h)", day3_24h: "Day 3 (+51 to +75 h)" };
const REGIME_LABEL: Record<string, string> = { ACTIVE_MONSOON: "Active monsoon (pseudo-regime)", BREAK_WEAK_MONSOON: "Break / weak monsoon (pseudo-regime)", LOW_DEPRESSION_INFLUENCED: "Low / depression influenced (pseudo-regime)" };

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
    <figcaption className="micro-note">{field.label} · {field.units} · 0 to {fixed(high, digits)} · 10 to 22 N, 68 to 80 E (south at the bottom) · array {field.array_sha256.slice(0, 12)}…</figcaption>
  </figure>;
}

function Detail({ kind, date }: { kind: string; date: string }) {
  const cycle = useQuery({ queryKey: ["live-cycle", kind, date], queryFn: () => getLiveCycle(kind, date) });
  const [product, setProduct] = useState<string>("");
  const [fieldName, setFieldName] = useState<string>("M1");
  const chosen = cycle.data ? (cycle.data.summary.products.includes(product) ? product : cycle.data.summary.products[0]) : "";
  const field = useQuery({ queryKey: ["live-field", kind, date, chosen, fieldName], queryFn: () => getLiveField(kind, date, chosen, fieldName), enabled: Boolean(chosen) });
  if (cycle.isError) return <ErrorState message={cycle.error instanceof EvidenceApiError && cycle.error.code === "SCIENCE_INTEGRITY_FAILURE" ? `Live bundle integrity check failed: ${cycle.error.message}. This is a hard failure.` : (cycle.error as Error).message} />;
  if (!cycle.data) return <LoadingState label="Loading the cycle" />;
  const c: LiveCycle = cycle.data;
  const replayWorst = c.replay_comparison ? Math.max(...Object.values(c.replay_comparison.products).flatMap((p) => Object.entries(p).filter(([k]) => k.endsWith("difference")).map(([, v]) => v))) : null;
  return <div data-testid="live-detail">
    <div className="phase5-controls">
      <label>Lead<select value={chosen} onChange={(e) => setProduct(e.target.value)}>{c.summary.products.map((p) => <option key={p} value={p}>{PRODUCT_LABEL[p] ?? p}</option>)}</select></label>
      <label>Field<select value={fieldName} onChange={(e) => setFieldName(e.target.value)}>{LIVE_FIELDS.map((f) => <option key={f} value={f}>{c.fields[f]}</option>)}</select></label>
    </div>
    {Object.entries(c.summary.withheld_products).length ? <div className="zone-banner zone-banner-posthoc" role="note" data-testid="live-withheld"><strong>Withheld leads (canonical rainfall quality control failed, as in the study corpus)</strong>
      {Object.entries(c.summary.withheld_products).map(([p, why]) => <span key={p}>{PRODUCT_LABEL[p] ?? p}: {why}</span>)}</div> : null}
    <div className="live-grid">
    {field.isError ? <ErrorState message={(field.error as Error).message} /> : field.data ? <Heatmap field={field.data} /> : <LoadingState label="Loading the field" />}
    <div className="live-side">
    <div className="district-table-wrap"><table className="phase5-table zone-table" data-testid="live-stats">
      <caption className="sr-only">Domain minimum, mean and maximum of each field for the selected lead</caption>
      <thead><tr><th scope="col">Field</th><th scope="col">Minimum</th><th scope="col">Mean</th><th scope="col">Maximum</th></tr></thead>
      <tbody>{LIVE_FIELDS.map((f) => { const s = c.domain_statistics[chosen]?.[f]; return <tr key={f}><th scope="row">{c.fields[f]}</th><td>{fixed(s?.min, 3)}</td><td>{fixed(s?.mean, 3)}</td><td>{fixed(s?.max, 3)}</td></tr>; })}</tbody></table></div>
    <h3>Regime probabilities for this lead (forecast-only pseudo-regimes, not meteorological accuracy)</h3>
    <ul className="live-regime-bars" data-testid="live-regime">{Object.entries(c.regime_probabilities[chosen] ?? {}).map(([name, p]) => <li key={name}><span>{REGIME_LABEL[name] ?? name}</span><i aria-hidden="true"><b style={{ width: `${Math.round(100 * p)}%` }} /></i><strong>{fixed(p, 3)}</strong></li>)}</ul>
    </div>
    </div>
    <p className="micro-note" data-testid="live-applicability">Applicability: {c.applicability ? `${c.applicability.status}${c.applicability.largest_share ? `; largest share of cells outside the 2023 training range ${fixed(100 * c.applicability.largest_share.share, 1)} % (${c.applicability.largest_share.feature}, ${PRODUCT_LABEL[c.applicability.largest_share.product] ?? c.applicability.largest_share.product})` : ""}. A range heuristic, not a validity test.` : "not computed for this bundle"}</p>
    {replayWorst != null ? <p className="micro-note" data-testid="live-replay-gate">Replay gate: the largest absolute difference between this path and the frozen 2025 artifacts is {replayWorst.toExponential(2)} (features, regime probabilities, M0 to M4 and probabilities over the paired cells).</p> : null}
    <p className="micro-note" data-testid="live-provenance">{c.messages} NOAA messages, {(c.transferred_bytes / 1e6).toFixed(2)} MB · manifest {c.manifest_sha256.slice(0, 12)}… · frozen models {Object.entries(c.frozen_models).map(([k, v]) => `${k} ${v.slice(0, 8)}…`).join(", ")} · no observation read, no retraining or recalibration.</p>
  </div>;
}

export function LiveCyclePage() {
  const status = useQuery({ queryKey: ["live-status"], queryFn: () => getLiveStatus() });
  const [selected, setSelected] = useState<string>("");
  if (status.isError) return <div className="page-content"><PageHeading title="Experimental Live Cycle" subtitle="Frozen models applied to a new forecast cycle" /><ErrorState message={status.error instanceof EvidenceApiError && status.error.code === "SCIENCE_INTEGRITY_FAILURE" ? `Live bundle integrity check failed: ${status.error.message}. This is a hard failure.` : (status.error as Error).message} /></div>;
  if (!status.data) return <div className="page-content"><PageHeading title="Experimental Live Cycle" subtitle="Frozen models applied to a new forecast cycle" /><LoadingState label="Loading the experimental cycles" /></div>;
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
