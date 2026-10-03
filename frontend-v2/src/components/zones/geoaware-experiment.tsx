"use client";

import { useQuery } from "@tanstack/react-query";
import { EvidenceApiError } from "@/lib/api/evidence";
import { getGeoawareEvaluation, getGeoawareFollowup, getGeoawareOverview, type GeoawareEvaluation, type GeoawareFollowup, type GeoawareOverview } from "@/lib/api/geoaware";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { HashChip } from "@/components/ui/hash-chip";

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
    <p className="micro-note">Evidence file <HashChip hash={ev.evidence_sha256} />. G1 heavy CSI no worse than Raw, G2 absolute bias at most the frozen limit, G3 very-heavy frequency bias at least the frozen floor.</p>
  </section>;
}

const FOLLOWUP_YEARS = ["2021", "2023", "2024"] as const;
const ARM_LABEL_V2: Record<string, string> = { B0: "B0 control (no geography)", B1: "B1 geography (candidate)", B0Z: "B0Z control without 500 hPa height", B1Z: "B1Z geography without 500 hPa height" };
const DECISION_ORDER = ["v3_primary", "v2_secondary"];
const SET_LABEL: Record<string, string> = { v3_primary: "Primary (protocol v3 selection)", v2_secondary: "Secondary (protocol v2 selection)" };
const configLabel = (c: { objective: string; weights: string; max_depth: number; n_estimators: number }) =>
  `${c.objective === "reg:tweedie" ? "Tweedie" : "squared error"}, ${c.weights === "capped_event" ? "capped event weights" : "no weights"}, depth ${c.max_depth}, ${c.n_estimators} rounds`;
const interval = (s: { point?: number | null; interval?: [number, number] } | undefined, digits: number) =>
  s?.point == null || !s.interval ? "undefined" : `${signed(s.point, digits)} [${signed(s.interval[0], digits)}, ${signed(s.interval[1], digits)}]`;

function IndependentTest({ data }: { data: GeoawareFollowup }) {
  const t = data.test_2022;
  const labels = ["M0", ...Object.keys(t.models).filter((label) => label in t.pooled_summary).sort()];
  const roleOf = (label: string) => {
    const primary = t.candidate_sets.v3_primary, secondary = t.candidate_sets.v2_secondary;
    if (label === "M0") return "Raw forecast";
    const parts = [];
    if (label === primary.candidate) parts.push("primary candidate");
    if (label === secondary.candidate) parts.push("secondary candidate");
    if (label === primary.comparator) parts.push("control");
    return parts.join(", ") || "other";
  };
  return <div data-testid="geoaware-test-2022">
    <div className="zone-banner zone-banner-posthoc" role="note" data-testid="geoaware-sealed">
      <strong>{data.sealed_test.year} was opened once, under the owner&apos;s unseal record · {t.label}</strong>
      <span>{t.cases} cases · one test, never re-run · the owner message was &quot;{data.unseal_record.owner_message.verbatim}&quot; · {data.unseal_record.hashes_listed} hashes were frozen and checked before any {data.sealed_test.year} observation was read.</span></div>
    <h3>Result on the independent year</h3>
    <p data-testid="geoaware-claim"><strong>{t.claim_wording}.</strong> Multiplicity: {t.multiplicity}. The test scored two pre-registered candidate sets together, so each decision interval is 97.5 percent, not 95 percent.</p>
    <div className="district-table-wrap"><table className="phase5-table zone-table">
      <caption className="sr-only">Pre-registered decision for each candidate set on the independent year</caption>
      <thead><tr><th scope="col">Candidate set</th><th scope="col">Candidate against control</th><th scope="col">P1 Ghats-coast heavy CSI difference (97.5 % interval)</th><th scope="col">P2 overall RMSE difference, mm (97.5 % interval)</th><th scope="col">P3 guardrails G1, G2, G4 (G3 reported)</th><th scope="col">Adds value</th></tr></thead>
      <tbody>{DECISION_ORDER.filter((key) => key in t.decisions).map((key) => [key, t.decisions[key]] as const).map(([key, d]) => <tr key={key} data-testid={`decision-${key}`}><th scope="row">{SET_LABEL[key] ?? key}</th><td>{d.candidate} against {d.comparator}</td>
        <td>{interval(d.zone_heavy_csi_difference, 3)} · {d.P1_zone_heavy_csi_beats_comparator_975 ? "passes" : "does not pass"}</td><td>{interval(d.overall_rmse_difference, 2)} · {d.P2_overall_rmse_within_tolerance ? "within the 0.2 mm tolerance" : "outside the tolerance"}</td>
        <td>{d.guardrails ? `G1 ${yesNo(d.guardrails.G1)} · G2 ${yesNo(d.guardrails.G2)} · G4 ${yesNo(d.guardrails.G4)} · G3 ${d.guardrails.G3 ? "met" : "not met"}` : "undefined"} · {d.P3_gating_guardrails_G1_G2_G4 ? "passes" : "does not pass"}</td><td>{d.adds_value == null ? "unevaluable" : d.adds_value ? "yes" : "no"}</td></tr>)}</tbody></table></div>
    <div className="district-table-wrap"><table className="phase5-table zone-table">
      <caption className="sr-only">Pooled scores of Raw and the scored models on the independent year</caption>
      <thead><tr><th scope="col">Model</th><th scope="col">Role</th><th scope="col">RMSE (mm)</th><th scope="col">Bias (mm)</th><th scope="col">Heavy CSI, all cells</th><th scope="col">Very-heavy frequency bias</th><th scope="col">Ghats-coast heavy CSI</th><th scope="col">Ghats-coast heavy frequency bias</th></tr></thead>
      <tbody>{labels.map((label) => { const m = t.pooled_summary[label]; return <tr key={label}><th scope="row">{label}</th><td>{roleOf(label)}</td><td>{fixed(m.rmse_mm, 2)}</td><td>{signed(m.bias_mm, 2)}</td><td>{fixed(m.heavy_csi, 3)}</td><td>{fixed(m.very_heavy_frequency_bias, 3)}</td><td>{fixed(m.zone_heavy_csi, 3)}</td><td>{fixed(m.zone_heavy_frequency_bias, 2)}</td></tr>; })}</tbody></table></div>
    <p data-testid="geoaware-test-reading">{(() => {
      const prim = t.decisions.v3_primary, sec = t.decisions.v2_secondary;
      const mp = t.pooled_summary[prim.candidate], mc = t.pooled_summary[prim.comparator];
      return `The primary candidate ${prim.candidate} ${prim.adds_value ? "satisfied" : "did not satisfy"} the pre-registered rule against its control ${prim.comparator}. Its Ghats-coast heavy-rain frequency bias is ${fixed(mp.zone_heavy_frequency_bias, 2)} against ${fixed(mc.zone_heavy_frequency_bias, 2)} for the control, so part of its higher CSI comes with mild over-forecasting of heavy rain in the zone. The secondary candidate ${sec.candidate} ${sec.adds_value ? "also satisfied" : "did not satisfy"} the rule: its Ghats-coast heavy CSI difference against the same control is ${interval(sec.zone_heavy_csi_difference, 3)}.`;
    })()}</p>
    <div className="district-table-wrap"><table className="phase5-table zone-table">
      <caption className="sr-only">Ghats-coast heavy-rain CSI by lead day</caption>
      <thead><tr><th scope="col">Lead</th><th scope="col">Cases</th>{[t.candidate_sets.v3_primary.candidate, t.candidate_sets.v3_primary.comparator, t.candidate_sets.v2_secondary.candidate, "M0"].map((l) => <th scope="col" key={l}>{l}</th>)}</tr></thead>
      <tbody>{Object.entries(t.by_lead).map(([lead, block]) => <tr key={lead}><th scope="row">{lead.replace("_24h", "").replace("day", "Day ")}</th><td>{block.cases}</td>
        {[t.candidate_sets.v3_primary.candidate, t.candidate_sets.v3_primary.comparator, t.candidate_sets.v2_secondary.candidate, "M0"].map((l) => <td key={l}>{fixed(block.models[l]?.zone_heavy_csi, 3)}</td>)}</tr>)}</tbody></table></div>
    <p className="micro-note">Sensitivity to the 500 hPa height features, models without those features minus the matching models with them (descriptive, 97.5 percent intervals): {t.sensitivity.map((s) => `${s.a} minus ${s.b}: Ghats-coast heavy CSI ${interval(s.zone_heavy_csi_difference ?? undefined, 3)}`).join("; ")}. A pair whose interval excludes zero differs; a pair whose interval includes zero shows no evidence of a difference.</p>
    <details><summary>The owner message, its interpretation and what was disclosed before opening</summary>
      <p>{data.unseal_record.owner_message.interpretation}</p>
      <ul className="phase5-caveats">{data.unseal_record.disclosed_before_opening.map((line) => <li className="phase5-caveat" key={line}>{line}</li>)}</ul>
      <p>Not authorised: {data.unseal_record.what_is_not_authorised.join("; ")}.</p></details>
  </div>;
}

function FollowupSection({ data }: { data: GeoawareFollowup }) {
  const b0 = data.v2_selection.B0, b1 = data.v2_selection.B1;
  const csiGap = b0 && b1 ? FOLLOWUP_YEARS.map((y) => ({ year: y, gap: (b1.by_year[y].zone_heavy_csi ?? NaN) - (b0.by_year[y].zone_heavy_csi ?? NaN) })) : [];
  const b1Wins = csiGap.filter((g) => g.gap > 0).map((g) => g.year);
  const b0Wins = csiGap.filter((g) => g.gap < 0).map((g) => g.year);
  const arms = Object.keys(data.v2_selection);
  return <section className="phase5-analysis-block" aria-labelledby="geo-followup-heading" data-testid="geoaware-followup">
    <h2 id="geo-followup-heading">Follow-up with an independent year</h2>
    <IndependentTest data={data} />
    <h3>How the candidates were chosen (development years only)</h3>
    <p>{data.v1_outcome.all_arms_without_candidate ? "Under the first frozen protocol (v1) no arm had an eligible candidate: no configuration passed every guardrail in every held-out year." : "Under the first frozen protocol (v1) at least one arm had a candidate."} {data.changes.map((c) => `${c.id}: ${c.what}`).join(" ")} The second change was decided after {data.post_hoc_disclosure.decided_after}. {data.post_hoc_disclosure.consequence}</p>
    <div className="district-table-wrap"><table className="phase5-table zone-table">
      <caption className="sr-only">Selected configuration per arm under protocols v2 and v3</caption>
      <thead><tr><th scope="col">Arm</th><th scope="col">Eligible configurations</th><th scope="col">Protocol v2 selection (lowest RMSE)</th><th scope="col">Protocol v3 selection (aligned with the test)</th></tr></thead>
      <tbody>{arms.map((arm) => { const m2 = data.v2_selection[arm], m3 = data.v3_selection[arm]; return <tr key={arm}><th scope="row">{ARM_LABEL_V2[arm] ?? arm}</th><td>{data.eligible_v2_by_arm[arm]} of 16</td>
        <td>{m2 ? `#${m2.grid_index}: ${configLabel(m2.config)}; pooled RMSE ${fixed(m2.pooled_rmse_mm, 2)}` : "none"}</td><td>{m3 ? `#${m3.grid_index}: ${configLabel(m3.config)}; pooled RMSE ${fixed(m3.pooled_rmse_mm, 2)}` : "none"}</td></tr>; })}</tbody></table></div>
    {b0 && b1 ? <p data-testid="geoaware-followup-reading">On the development years, as selected under protocol v2 the geography model (B1) had the higher Ghats-coast heavy-rain CSI in {b1Wins.length ? b1Wins.join(", ") : "no held-out year"} and the control (B0) in {b0Wins.length ? b0Wins.join(", ") : "no held-out year"}, which is why the aligned selection of protocol v3 was introduced. At matched configurations geography had the higher Ghats-coast heavy CSI in every held-out year in {data.matched_configuration_comparison.zone_heavy_csi_higher_in_every_held_out_year} of {data.matched_configuration_comparison.configurations} configurations.</p> : null}
    <p>The pre-registered rule required all of:</p>
    <ol className="phase5-caveats">{data.decision_rule.adds_value_requires_all.map((rule) => <li className="phase5-caveat" key={rule}>{rule}</li>)}</ol>
    <ul className="phase5-caveats">{data.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
    <p className="micro-note">Protocol v3 <HashChip hash={data.protocol_v3_sha256} /> · selection freeze v3 <HashChip hash={data.freeze_v3_sha256} /> · unseal record <HashChip hash={data.unseal_record_sha256} /> · test result <HashChip hash={data.test_result_sha256} /> · protocol v2 <HashChip hash={data.protocol_v2_sha256} /> · protocol v1 <HashChip hash={data.protocol_v1_sha256} />.</p>
  </section>;
}

export function GeoawareExperiment() {
  const overview = useQuery({ queryKey: ["geoaware-overview"], queryFn: () => getGeoawareOverview(), staleTime: 5 * 60_000 });
  const e2024 = useQuery({ queryKey: ["geoaware-evaluation", 2024], queryFn: () => getGeoawareEvaluation(2024), staleTime: 5 * 60_000 });
  const e2025 = useQuery({ queryKey: ["geoaware-evaluation", 2025], queryFn: () => getGeoawareEvaluation(2025), staleTime: 5 * 60_000 });
  const followup = useQuery({ queryKey: ["geoaware-followup"], queryFn: () => getGeoawareFollowup(), staleTime: 5 * 60_000 });

  const failed = [overview, e2024, e2025, followup].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <div className="page-content"><ErrorState message={integrity ? `Geography-aware evidence integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "Geography-aware evidence is unavailable."} /></div>;
  }
  if (!overview.data || !e2024.data || !e2025.data || !followup.data) return <div className="page-content"><LoadingState compact label="Loading geography-aware experiment" /></div>;
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

    <FollowupSection data={followup.data} />

    <section className="phase5-analysis-block" aria-labelledby="geo-gap-heading">
      <h2 id="geo-gap-heading">What we cannot conclude, and the next step</h2>
      <p>{ov.decision.protocol_gap}</p>
      <p>The 2024 and 2025 results have now been seen, so tuning against them would only fit the years used to judge the result. A fair follow-up needs new years of data that were not used. Approval: {ov.approval.option_D1}.</p>
    </section>

    <p className="micro-note">Frozen protocol <HashChip hash={ov.protocol_sha256} /> · selection freeze <HashChip hash={ov.selection_freeze_sha256} /> · manifest <HashChip hash={ov.manifest_sha256} /> · Historical scientific prototype, not an operational service.</p>
  </div>;
}
