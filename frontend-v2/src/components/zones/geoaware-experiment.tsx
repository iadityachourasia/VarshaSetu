"use client";

import { useQuery } from "@tanstack/react-query";
import { EvidenceApiError } from "@/lib/api/evidence";
import { getGeoawareEvaluation, getGeoawareOverview, type GeoawareEvaluation, type GeoawareOverview } from "@/lib/api/geoaware";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";

const ZONE = "COASTAL_AND_OROGRAPHIC";
const MODELS: { key: string; label: string }[] = [
  { key: "M0", label: "M0 Raw" }, { key: "M2", label: "M2 Global ML" }, { key: "A1", label: "A1 Geography features" }, { key: "A3", label: "A3 Geography and forcing" },
];
const ARM_LABEL: Record<string, string> = { A0: "A0 control (no geography)", A1: "A1 static geography", A2: "A2 forcing only", A3: "A3 geography and forcing" };

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
const signed = (value: number, digits: number) => `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
const yesNo = (value: boolean) => (value ? "met" : "not met");

type Stat = { status: string; point?: number | null; interval95?: [number, number]; excludes_zero?: boolean } | undefined;
function statText(stat: Stat, digits: number) {
  if (!stat || stat.status !== "ok" || stat.point == null || !stat.interval95) return stat?.status === "insufficient_support" ? "insufficient support" : "not reported";
  return `${signed(stat.point, digits)} [${signed(stat.interval95[0], digits)}, ${signed(stat.interval95[1], digits)}] ${stat.excludes_zero ? "· excludes 0" : "· includes 0"}`;
}

function ModelTable({ ev }: { ev: GeoawareEvaluation }) {
  const { payload } = ev;
  const support = payload.support[ZONE];
  const block = (zone: string, model: string) => payload.pooled[zone]?.[model];
  const rows: { label: string; zone: string; heavy: boolean }[] = [
    { label: "Ghats coast (coastal and orographic)", zone: ZONE, heavy: true }, { label: "All land cells", zone: "ALL", heavy: true },
  ];
  return <div className="district-table-wrap"><table className="phase5-table zone-table">
    <caption className="sr-only">RMSE, bias, heavy-rain CSI and heavy-rain frequency bias for Raw, the global model and the geography-aware arms</caption>
    <thead><tr><th scope="col">Score</th><th scope="col">Population</th>{MODELS.map((m) => <th scope="col" key={m.key}>{m.label}</th>)}</tr></thead>
    <tbody>{[
      { score: "RMSE (mm per 24 h)", pick: (b: ReturnType<typeof block>) => fixed(b?.rmse_mm, 2) },
      { score: "Bias, forecast minus IMD (mm)", pick: (b: ReturnType<typeof block>) => fixed(b?.bias_mm, 2) },
      { score: "Heavy-rain CSI", pick: (b: ReturnType<typeof block>) => fixed(b?.categorical?.heavy?.CSI, 3) },
      { score: "Heavy-rain frequency bias", pick: (b: ReturnType<typeof block>) => fixed(b?.categorical?.heavy?.frequency_bias, 2) },
    ].flatMap((metric) => rows.map((row) => <tr key={`${metric.score}-${row.zone}`}>
      <th scope="row">{metric.score}</th><td>{row.label}{row.zone === ZONE ? ` · ${support.heavy.observed_event_pairs.toLocaleString("en-GB")} observed heavy cell-days` : ""}</td>
      {MODELS.map((m) => <td key={m.key}>{metric.pick(block(row.zone, m.key))}</td>)}</tr>))}</tbody></table></div>;
}

function YearSection({ ev, ov }: { ev: GeoawareEvaluation; ov: GeoawareOverview }) {
  const decision = ov.decision.per_year[String(ev.year)];
  const postHoc = /POST-HOC/.test(ev.evidence_label);
  const g = ev.payload.guardrails_on_evaluation_population.A3;
  return <section className="phase5-analysis-block" aria-labelledby={`geo-${ev.year}-heading`}>
    <h2 id={`geo-${ev.year}-heading`}>{ev.year} · {postHoc ? "completed final test, post-hoc" : "development year"}</h2>
    <div className={postHoc ? "zone-banner zone-banner-posthoc" : "zone-banner"} role="note"><strong>{ev.evidence_label}</strong>
      <span>{ev.payload.case_count} cases · reproduces the published verification exactly ({ev.payload.reproduction.status}) · paired whole-case bootstrap ({ev.payload.bootstrap.repeats} resamples, optimistic)</span></div>
    <ModelTable ev={ev} />
    <div className="phase5-metric-strip">
      <span><b>Heavy CSI on the Ghats coast, A3 minus M2</b> {statText(decision.heavy_csi_zone_A3_minus_M2, 3)}</span>
      <span><b>Overall RMSE, A3 minus M2</b> {statText(decision.overall_rmse_A3_minus_M2, 2)} mm</span>
      <span><b>Guardrails on this year</b> G1 {yesNo(g.G1)} · G2 {yesNo(g.G2)} · G3 {yesNo(g.G3)}</span>
    </div>
    <p className="micro-note">Evidence file {ev.evidence_sha256.slice(0, 12)}…. G1 heavy CSI no worse than Raw, G2 absolute bias at most the frozen limit, G3 very-heavy frequency bias at least the frozen floor.</p>
  </section>;
}

export function GeoawareExperiment() {
  const overview = useQuery({ queryKey: ["geoaware-overview"], queryFn: () => getGeoawareOverview(), staleTime: 5 * 60_000 });
  const e2024 = useQuery({ queryKey: ["geoaware-evaluation", 2024], queryFn: () => getGeoawareEvaluation(2024), staleTime: 5 * 60_000 });
  const e2025 = useQuery({ queryKey: ["geoaware-evaluation", 2025], queryFn: () => getGeoawareEvaluation(2025), staleTime: 5 * 60_000 });

  const failed = [overview, e2024, e2025].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <div className="page-content"><ErrorState message={integrity ? `Geography-aware evidence integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "Geography-aware evidence is unavailable."} /></div>;
  }
  if (!overview.data || !e2024.data || !e2025.data) return <div className="page-content"><LoadingState label="Loading geography-aware experiment" /></div>;
  const ov = overview.data;
  const arms = Object.keys(ov.selection);
  const years = Object.entries(ov.decision.per_year);
  const bothBeat = years.every(([, d]) => d.csi_beats_M2);
  const failedYears = years.filter(([, d]) => !d.rmse_within_tolerance || !d.guardrails_pass).map(([y]) => y);
  const passing = (arm: string) => ov.configurations.filter((c) => c.arm === arm && c.passes_guardrails).length;
  const total = (arm: string) => ov.configurations.filter((c) => c.arm === arm).length;

  return <div className="page-content zones-page">
    <PageHeading title="Geography-Aware Model Experiment" subtitle="A pre-registered attempt to fix the Ghats-coast heavy-rain deficiency · development-only evidence" action={<PrototypeNote />} />
    <div className="zone-banner zone-banner-posthoc" role="note" data-testid="geoaware-verdict">
      <strong>{ov.decision.adds_value ? "Pre-registered rule met" : "Pre-registered rule NOT met"}</strong>
      <span>{ov.decision.wording}. Coverage status for coastal and orographic regimes: {/stays PARTIAL/.test(ov.decision.coverage_status_consequence) ? "stays PARTIAL" : "see the compliance page"}.</span></div>

    <section className="phase5-analysis-block" aria-labelledby="geo-what-heading">
      <h2 id="geo-what-heading">What was tried, and what happened</h2>
      <p>The protocol, the feature sets, the guardrails and the decision rule were frozen before any training. A gradient-boosted model was trained on 2023 only with static geography (terrain relief, elevation, distance to coast, slope) and forecast-time forcing, a configuration was selected on 2023 out-of-fold results alone and frozen, and only then were 2024 and 2025 scored.</p>
      <p>{bothBeat ? `Heavy-rain detection on the Ghats coast improved over the global model in both years, and the sign agrees (${ov.decision.sign_agrees_2024_2025 ? "yes" : "no"}). ` : "Heavy-rain detection on the Ghats coast did not improve over the global model in both years. "}The rule also requires overall error not worse than the global model and all guardrails to pass{failedYears.length ? `, and ${failedYears.join(" and ")} did not satisfy that` : ""}. So the result is reported as {ov.decision.adds_value ? "met" : "a negative one"}.</p>
      <ul className="phase5-caveats">{ov.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
    </section>

    <YearSection ev={e2024.data} ov={ov} />
    <YearSection ev={e2025.data} ov={ov} />

    <section className="phase5-analysis-block" aria-labelledby="geo-selection-heading">
      <h2 id="geo-selection-heading">Selection on the 2023 training year</h2>
      <p>Each feature arm was searched over {total("A0")} configurations with embargoed, blocked cross-validation. A configuration is eligible only if it passes all guardrails on the pooled out-of-fold predictions.</p>
      <div className="district-table-wrap"><table className="phase5-table zone-table">
        <caption className="sr-only">Feature arms, eligible configurations and the frozen selection</caption>
        <thead><tr><th scope="col">Arm</th><th scope="col">Features</th><th scope="col">Eligible configurations</th><th scope="col">Frozen selection</th></tr></thead>
        <tbody>{arms.map((arm) => <tr key={arm}><th scope="row">{ARM_LABEL[arm] ?? arm}</th><td>{ov.arms[arm]?.length ?? "undefined"}</td>
          <td>{passing(arm)} of {total(arm)}</td>
          <td>{ov.selection[arm].selected ? `configuration ${ov.selection[arm].selected!.grid_index}` : `none: ${ov.selection[arm].reason ?? "no eligible configuration"}`}</td></tr>)}</tbody></table></div>
    </section>

    <section className="phase5-analysis-block" aria-labelledby="geo-gap-heading">
      <h2 id="geo-gap-heading">What we cannot conclude, and the next step</h2>
      <p>{ov.decision.protocol_gap}</p>
      <p>The 2024 and 2025 results have now been seen, so tuning against them would only fit the years used to judge the result. A fair follow-up needs new years of data that were not used. Approval: {ov.approval.option_D1}.</p>
    </section>

    <p className="micro-note">Frozen protocol {ov.protocol_sha256.slice(0, 12)}… · selection freeze {ov.selection_freeze_sha256.slice(0, 12)}… · manifest {ov.manifest_sha256.slice(0, 12)}… · Historical scientific prototype, not an operational service.</p>
  </div>;
}
