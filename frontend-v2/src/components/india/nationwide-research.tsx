"use client";

import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/science/common";
import { ProbabilityLegend, RainLegend } from "@/components/maps/map-legend";
import { HashChip } from "@/components/ui/hash-chip";
import { nearestValidCell, type CellSelection } from "@/lib/maps/grid";
import { EvidenceApiError } from "@/lib/api/evidence";
import { NATIONAL_FIELDS, getNationwideCases, getNationwideDistricts, getNationwideGrid, getNationwideOverview, getNationwideVerification, type NationalField } from "@/lib/api/nationwide-research";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" aria-label="Loading nationwide research map" /> });
const LABEL: Record<NationalField, string> = {
  M0: "M0 · Raw GEFS", M1: "M1 · linear MOS", M2: "M2 · global research correction",
  M3: "M3 · hard pseudo-regime correction", M4: "M4 · soft pseudo-regime correction",
  heavy_p: "Heavy rain probability · research", very_heavy_p: "Very-heavy probability · research",
};

export function NationwideResearch() {
  const [open, setOpen] = useState(false);
  const [caseId, setCaseId] = useState("");
  const [fieldName, setFieldName] = useState<NationalField>("M0");
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const [districtFilter, setDistrictFilter] = useState("");
  const [districtPage, setDistrictPage] = useState(0);
  const [verificationRegion, setVerificationRegion] = useState("ALL_INDIA");
  const [verificationLead, setVerificationLead] = useState<0 | 24 | 48 | 72>(0);
  const overview = useQuery({ queryKey: ["national-research-overview"], queryFn: getNationwideOverview, enabled: open, staleTime: 5 * 60_000, retry: false });
  const catalogue = useQuery({ queryKey: ["national-research-cases"], queryFn: getNationwideCases, enabled: open && overview.isSuccess, staleTime: 5 * 60_000 });
  const available = catalogue.data?.cases.filter((item) => item.available_locally) ?? [];
  const chosen = available.find((item) => item.case_id === caseId) ?? available[0];
  const forecast = useQuery({ queryKey: ["national-research-grid", chosen?.case_id, fieldName],
    queryFn: () => getNationwideGrid(chosen!.case_id, fieldName), enabled: open && Boolean(chosen) });
  const district = useQuery({ queryKey: ["national-research-districts", chosen?.case_id],
    queryFn: () => getNationwideDistricts(chosen!.case_id), enabled: open && Boolean(chosen), staleTime: 5 * 60_000 });
  const verification = useQuery({ queryKey: ["national-research-verification", verificationRegion, verificationLead],
    queryFn: () => getNationwideVerification(verificationRegion, verificationLead), enabled: open && overview.isSuccess, staleTime: 5 * 60_000 });
  const grid = forecast.data;
  const cell = grid ? selected && grid.valid_mask[selected.row]?.[selected.column] ? selected : nearestValidCell(grid.valid_mask) : null;
  const value = grid && cell ? grid.values[cell.row][cell.column] : null;
  const rows = useMemo(() => district.data?.districts.filter((item) => `${item.district_name} ${item.district_id}`.toLowerCase().includes(districtFilter.toLowerCase())) ?? [], [district.data, districtFilter]);
  const pageSize = 20;
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const visibleRows = rows.slice(districtPage * pageSize, (districtPage + 1) * pageSize);
  const probability = fieldName.endsWith("_p");
  const unavailable = overview.error instanceof EvidenceApiError && overview.error.status === 404;
  const weakerRegions = overview.data ? Object.entries(overview.data.regional_gate).filter(([name, result]) => name !== "ALL_INDIA" && result.M0_heavy_csi != null && result.M2_heavy_csi != null && result.M2_heavy_csi < result.M0_heavy_csi).map(([name]) => name.replaceAll("_", " ").toLowerCase()) : [];

  return <section id="india-research" className="phase5-analysis-block india-research" aria-label="Nationwide model development research" data-testid="nationwide-research">
    <div className="india-research-intro"><div><span className="india-section-number">03 / Model research</span><h2>Nationwide model research · 2024 development</h2><p>Explore the sealed M0–M4 comparison and probability fields. These are consumed development results; the regional M2 remains the live default.</p></div><button type="button" className="india-research-toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open} data-testid="nationwide-research-toggle">{open ? "Close research comparison" : "Open research comparison"}<span aria-hidden="true">{open ? "−" : "↗"}</span></button></div>
    {open && (overview.isPending ? <LoadingState label="Checking local nationwide research evidence" />
      : unavailable ? <EmptyState message="The local-only research API is disabled. Start FastAPI with VARSHASETU_LOCAL_NATIONWIDE_RESEARCH=1 to inspect the sealed development artifacts on this machine." />
      : overview.isError ? <ErrorState message={(overview.error as Error).message} />
      : <>
        <div className="india-research-summary"><div><span>Historical cases</span><strong>{overview.data.cases}</strong><small>sealed 2024 forecasts</small></div><div><span>Paired grid cells</span><strong>{overview.data.paired_cells.toLocaleString("en-IN")}</strong><small>same-case comparison</small></div><div><span>Product decision</span><strong>No promotion</strong><small>regional M2 remains default</small></div></div>
        <div className="india-scope-note india-research-boundary" role="note" data-testid="nationwide-research-boundary"><div><span className="india-scope-kicker">Scientific result</span><strong>Consumed 2024 development · no promotion</strong></div><p>{overview.data.m2_selection_passed ? "M2 passed its 2023 selection gate." : "M2 failed its prespecified 2023 selection gate."} {weakerRegions.length ? `2024 heavy CSI fell below Raw in ${weakerRegions.join(", ")}. ` : ""}{overview.data.models.M2.very_heavy_csi != null && overview.data.models.M0.very_heavy_csi != null && overview.data.models.M2.very_heavy_csi < overview.data.models.M0.very_heavy_csi ? "National very-heavy CSI also fell below Raw. " : ""}The original probability fields failed a methodology audit; their reliability and warning cutoffs are unvalidated. This map is an experiment, not a warning.</p></div>
        <p className="micro-note india-research-hashes">Protocol <HashChip hash={overview.data.protocol_sha256} /> · score <HashChip hash={overview.data.score_sha256} /></p>
        <h3 className="india-subheading">Same-case model comparison</h3>
        <div className="district-table-wrap" tabIndex={0}><table className="phase5-table"><caption className="sr-only">Nationwide same-case development scores</caption><thead><tr><th scope="col">Arm</th><th scope="col">RMSE mm/24 h</th><th scope="col">Heavy CSI</th><th scope="col">Very-heavy CSI</th></tr></thead><tbody>{(["M0", "M1", "M2", "M3", "M4"] as const).map((model) => <tr key={model}><th scope="row">{LABEL[model]}</th><td>{overview.data.models[model].rmse_mm.toFixed(2)}</td><td>{overview.data.models[model].heavy_csi?.toFixed(3) ?? "undefined"}</td><td>{overview.data.models[model].very_heavy_csi?.toFixed(3) ?? "undefined"}</td></tr>)}</tbody></table></div>
        <h3 className="india-subheading">Verification detail · consumed development</h3>
        <div className="phase5-controls india-control-panel" role="group" aria-label="Development verification controls">
          <label>Region<select value={verificationRegion} onChange={(event) => setVerificationRegion(event.target.value)}>{Object.keys(overview.data.regional_gate).map((name) => <option value={name} key={name}>{name.replaceAll("_", " ")}</option>)}</select></label>
          <label>Lead<select value={verificationLead} onChange={(event) => setVerificationLead(Number(event.target.value) as 0 | 24 | 48 | 72)}><option value={0}>All leads</option><option value={24}>Day 1 · +24 h</option><option value={48}>Day 2 · +48 h</option><option value={72}>Day 3 · +72 h</option></select></label>
        </div>
        {verification.isError ? <ErrorState message={(verification.error as Error).message} /> : verification.isPending ? <LoadingState compact label="Loading sealed verification" /> : verification.data ? <>
          <p className="micro-note" data-testid="nationwide-verification-support">{verification.data.paired_cases} initialization/lead cases · {verification.data.paired_cells.toLocaleString("en-IN")} identical eligible cells per arm · IMD RF25 03–03 UTC reference · score <HashChip hash={verification.data.score_sha256} /> · uncertainty <HashChip hash={verification.data.uncertainty_sha256} /></p>
          <div className="district-table-wrap" tabIndex={0}><table className="phase5-table" data-testid="nationwide-verification-table"><caption className="sr-only">Sealed 2024 same-case verification with 24-hour heavy-event counts and spatial FSS</caption><thead><tr><th scope="col">Arm</th><th scope="col">Bias mm</th><th scope="col">RMSE mm</th><th scope="col">Heavy H / FA / M</th><th scope="col">CSI</th><th scope="col">ETS</th><th scope="col">POD</th><th scope="col">FAR</th><th scope="col">FSS 5</th><th scope="col">CSI − Raw 95% date CI</th></tr></thead><tbody>{(["M0", "M1", "M2", "M3", "M4"] as const).map((model) => { const v = verification.data!.models[model]; const h = v.metrics.heavy; const ci = verification.data!.uncertainty[model].heavy_csi_delta_ci95; return <tr key={model}><th scope="row">{model}</th><td>{v.metrics.continuous.bias_mm.toFixed(2)}</td><td>{v.metrics.continuous.rmse_mm.toFixed(2)}</td><td>{h.hits} / {h.false_alarms} / {h.misses}</td><td>{h.metrics.CSI?.toFixed(3) ?? "undefined"}</td><td>{h.metrics.ETS?.toFixed(3) ?? "undefined"}</td><td>{h.metrics.POD?.toFixed(3) ?? "undefined"}</td><td>{h.metrics.FAR?.toFixed(3) ?? "undefined"}</td><td>{v.fss.heavy["5"]?.fss?.toFixed(3) ?? "undefined"}</td><td>{ci ? `[${ci[0].toFixed(3)}, ${ci[1].toFixed(3)}]` : "undefined"}</td></tr>; })}</tbody></table></div>
          <p className="phase5-caveat">H = hits, FA = false alarms, M = misses. FSS 5 uses a five-cell neighbourhood on aligned 2-D fields. The date-block interval does not remove spatial or serial dependence. Very-heavy counts and scores, plus 1- and 3-cell FSS, are available in the typed verification API. {verification.data.caveat}</p>
        </> : null}
        <div className="india-section-heading india-research-map-heading"><div><span className="india-section-number">Historical field</span><h3>Inspect a forecast grid</h3><p>Switch between Raw, corrected research arms, and unvalidated probabilities.</p></div></div>
        <div className="phase5-controls india-control-panel" role="group" aria-label="Nationwide research map controls">
          <label>Historical case<select value={chosen?.case_id ?? ""} onChange={(event) => { setCaseId(event.target.value); setSelected(null); }} disabled={!available.length}>{available.map((item) => <option value={item.case_id} key={item.case_id}>{item.case_id.slice(0, 8)} · +{item.lead_hours} h</option>)}</select></label>
          <label>Research field<select value={fieldName} onChange={(event) => { setFieldName(event.target.value as NationalField); setSelected(null); }} data-testid="nationwide-field-select">{NATIONAL_FIELDS.map((name) => <option value={name} key={name}>{LABEL[name]}</option>)}</select></label>
        </div>
        {catalogue.isError ? <ErrorState message={(catalogue.error as Error).message} /> : catalogue.isPending ? <LoadingState label="Loading development case catalogue" /> : !available.length ? <EmptyState message="No sealed local development predictions are available." /> : null}
        {forecast.isError ? <ErrorState message={(forecast.error as Error).message} /> : forecast.isPending && chosen ? <LoadingState label="Loading sealed nationwide research field" /> : grid ? <>
          <div className="case-meta"><span><b>CASE</b> {grid.case_id}</span><span><b>WINDOW</b> +{grid.accumulation_window_hours[0]} to +{grid.accumulation_window_hours[1]} h</span><span><b>GRID</b> 129 × 135</span><span><b>STATUS</b> 2024 development</span></div>
          <div className="india-map-card"><div className="phase5-map-grid phase5-map-1" data-testid="nationwide-research-map"><GridMap id="nationwide-research" title={LABEL[fieldName]} subtitle="Sealed nationwide historical development forecast" values={grid.values} mask={grid.valid_mask} grid={grid.grid} palette={probability ? "probability" : "rainfall"} unit={probability ? "probability" : "mm / 24 h"} selected={cell} onSelect={setSelected} /></div><div className="india-map-legend">{probability ? <ProbabilityLegend /> : <RainLegend />}</div></div>
          <p className="phase5-caveat">{grid.caveat} {probability ? "Independent probability reliability is unverified." : ""} The visual footprint is a 2021 research polygon overlap, not the IMD reference mask.</p>
          <div className="phase5-inspector"><div><span className="small-label">SELECTED CELL</span><h3>{cell ? `${grid.grid.latitude_centers[cell.row].toFixed(2)}° N · ${grid.grid.longitude_centers[cell.column].toFixed(2)}° E` : "Select a cell"}</h3><p>{value == null ? "Unavailable" : probability ? `${(value * 100).toFixed(1)}% · research probability` : `${value.toFixed(2)} mm / 24 h`}</p></div><div><span className="small-label">LINEAGE</span><p>Forecast bundle <HashChip hash={grid.prediction_sha256} /> · fit seal <HashChip hash={grid.fit_seal_sha256} /></p></div></div>
        </> : null}
        <div className="india-section-heading india-district-heading"><div><span className="india-section-number">Research geometry</span><h3>District table</h3><p>Simplified 2021 boundaries are non-official; redistribution rights remain open. Coverage measures sampled polygon/grid overlap, not district area.</p></div></div>
        <label className="phase5-district-filter india-district-search">Find district <input type="search" value={districtFilter} onChange={(event) => { setDistrictFilter(event.target.value); setDistrictPage(0); }} placeholder="District name or ID" /></label>
        {district.isError ? <ErrorState message={(district.error as Error).message} /> : district.isPending && chosen ? <LoadingState compact label="Loading research district rows" /> : district.data ? <><p className="micro-note">{rows.length} of {district.data.districts.length} districts · table <HashChip hash={district.data.table_sha256} /></p><div className="district-table-wrap" tabIndex={0}><table className="phase5-table"><caption className="sr-only">Non-official research district mean forecast</caption><thead><tr><th scope="col">District</th><th scope="col">Coverage</th><th scope="col">Raw mean</th><th scope="col">Research {fieldName} mean</th></tr></thead><tbody>{visibleRows.map((item) => <tr key={item.district_id}><th scope="row">{item.district_name}</th><td>{(item.weighted_grid_coverage_fraction * 100).toFixed(0)}%</td><td>{item.M0?.toFixed(1) ?? "withheld"}</td><td>{item[fieldName]?.toFixed(probability ? 3 : 1) ?? "withheld"}</td></tr>)}</tbody></table></div><div className="india-pagination"><span>Showing {rows.length ? districtPage * pageSize + 1 : 0}–{Math.min((districtPage + 1) * pageSize, rows.length)} of {rows.length}</span><div><button type="button" disabled={districtPage === 0} onClick={() => setDistrictPage((page) => Math.max(0, page - 1))}>Previous</button><span>Page {districtPage + 1} of {pageCount}</span><button type="button" disabled={districtPage + 1 >= pageCount} onClick={() => setDistrictPage((page) => Math.min(pageCount - 1, page + 1))}>Next</button></div></div></> : null}
      </>)}
  </section>;
}
