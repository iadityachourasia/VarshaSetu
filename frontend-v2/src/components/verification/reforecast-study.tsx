"use client";

import { useQuery } from "@tanstack/react-query";
import { ErrorState, LoadingState } from "@/components/science/common";
import { EvidenceApiError } from "@/lib/api/evidence";
import { R05_MODELS, getR05Confirmation, getR05Result, getReforecastOverview, type ConfirmationResult, type R05Result } from "@/lib/api/reforecast";

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
const MODEL_LABEL: Record<string, string> = { M0: "M0 Raw GEFS control", B0: "B0 event-weighted ML (22 features)", B1: "B1 event-weighted ML + static geography", R_hard: "R hard regime routing", R_soft: "R soft regime mixture" };
const FLAG_LABEL: Record<string, string> = { IMPROVES_RMSE: "RMSE", IMPROVES_HEAVY: "heavy-rain CSI", IMPROVES_VERY_HEAVY: "very-heavy CSI" };

function intervalText(entry: { status: string; point?: number | null; interval95?: [number, number] } | null | undefined, digits: number) {
  if (!entry || entry.status !== "ok" || entry.point == null || !entry.interval95) return "not reported";
  return `${fixed(entry.point, digits)} [${fixed(entry.interval95[0], digits)}, ${fixed(entry.interval95[1], digits)}]`;
}

function Decisions({ result }: { result: R05Result }) {
  const p = result.payload;
  return <div className="evidence-verdicts" data-testid="reforecast-decisions">
    {Object.entries(p.bundle_decisions).map(([arm, d]) => <p key={arm} data-testid={`reforecast-bundle-${arm}`}><strong>{MODEL_LABEL[arm]} with exceedance classifiers: tier {d.decision.tier}.</strong>{" "}
      {(["IMPROVES_RMSE", "IMPROVES_HEAVY", "IMPROVES_VERY_HEAVY"] as const).map((k) => `${FLAG_LABEL[k]} ${d.decision[k] ? "improved" : "not shown to improve"}`).join("; ")}.
      {" "}Against Raw: RMSE difference {intervalText(d.vs_raw.rmse, 2)} mm, heavy CSI {intervalText(d.vs_raw.heavy_csi, 3)}, very-heavy CSI {intervalText(d.vs_raw.very_heavy_csi, 3)}; bias within limits: {d.decision.BIAS_OK ? "yes" : "no"}. {d.components}.</p>)}
    {Object.entries(p.decisions).map(([arm, d]) => <p key={arm} data-testid={`reforecast-decision-${arm}`}><strong>{MODEL_LABEL[arm]}: tier {d.decision.tier}.</strong>{" "}
      {(["IMPROVES_RMSE", "IMPROVES_HEAVY", "IMPROVES_VERY_HEAVY"] as const).map((k) => `${FLAG_LABEL[k]} ${d.decision[k] ? "improved" : "not shown to improve"}`).join("; ")}.
      {" "}Against Raw: RMSE difference {intervalText(d.vs_raw.rmse, 2)} mm, heavy CSI {intervalText(d.vs_raw.heavy_csi, 3)}, very-heavy CSI {intervalText(d.vs_raw.very_heavy_csi, 3)}; bias within limits: {d.decision.BIAS_OK ? "yes" : "no"}.</p>)}
    {Object.entries(p.regime_decisions).map(([arm, d]) => <p key={arm} data-testid={`reforecast-regime-${arm}`}><strong>{MODEL_LABEL[arm]} against B0: regime-awareness {d.adds_value.adds_value ? "adds value" : "is not shown to add value"}.</strong>{" "}
      Heavy CSI difference {intervalText(d.vs_b0.heavy_csi, 3)}, RMSE difference {intervalText(d.vs_b0.rmse, 2)} mm.</p>)}
  </div>;
}

function Confirmation({ result }: { result: ConfirmationResult }) {
  const p = result.payload;
  const d = p.bundle_decision;
  const h = p.exceedance["B1:heavy"];
  const v = p.exceedance["B1:very_heavy"];
  return <div className="evidence-stack" data-testid="reforecast-confirmation">
    <h3>Round 2: confirmatory test on 2017-2019</h3>
    <div className="zone-banner" role="note" data-testid="reforecast-confirmation-banner"><strong>{result.evidence_label}</strong>
      <span>The frozen B1 bundle, no refit. One parameter was added after round 1: the regression is reduced by {fixed(p.delta_mm, 2)} mm, the mean error of the same model on 2014-2016 ({p.delta_source}). {p.cases} cases on {p.initialization_dates} initialization dates.</span></div>
    <div className="district-table-wrap"><table className="phase5-table zone-table" data-testid="reforecast-confirmation-table">
      <caption className="sr-only">RMSE, mean error and heavy and very-heavy rain skill of Raw and the frozen bundle on 2017-2019</caption>
      <thead><tr><th scope="col">Forecast</th><th scope="col">RMSE (mm per 24 h)</th><th scope="col">Mean error (mm)</th><th scope="col">Heavy CSI / frequency bias</th><th scope="col">Very-heavy CSI / frequency bias</th></tr></thead>
      <tbody><tr data-testid="reforecast-confirmation-M0"><th scope="row">M0 Raw</th><td>{fixed(p.pooled.M0.rmse_mm, 3)}</td><td>{fixed(p.pooled.M0.bias_mm, 3)}</td><td>{fixed(p.raw_categorical.heavy.csi, 3)} / {fixed(p.raw_categorical.heavy.frequency_bias, 2)}</td><td>{fixed(p.raw_categorical.very_heavy.csi, 3)} / {fixed(p.raw_categorical.very_heavy.frequency_bias, 2)}</td></tr>
        <tr data-testid="reforecast-confirmation-uncorrected"><th scope="row">B1 regression before the mean-error correction</th><td>{fixed(p.pooled.B1_uncorrected.rmse_mm, 3)}</td><td>{fixed(p.pooled.B1_uncorrected.bias_mm, 3)}</td><td colSpan={2}>not used for the verdict</td></tr>
        <tr data-testid="reforecast-confirmation-bundle"><th scope="row">B1 bundle: corrected regression (RMSE, mean error) + exceedance classifiers (categorical)</th><td>{fixed(p.pooled.B1_shifted.rmse_mm, 3)}</td><td>{fixed(p.pooled.B1_shifted.bias_mm, 3)}</td>
          <td>{fixed(h.test.csi, 3)} / {fixed(h.test.frequency_bias, 2)}</td><td>{fixed(v.test.csi, 3)} / {fixed(v.test.frequency_bias, 2)}</td></tr></tbody></table></div>
    <p data-testid="reforecast-confirmation-decision"><strong>Frozen verdict: tier {d.decision.tier}.</strong> {(["IMPROVES_RMSE", "IMPROVES_HEAVY", "IMPROVES_VERY_HEAVY"] as const).map((k) => `${FLAG_LABEL[k]} ${d.decision[k] ? "improved" : "not shown to improve"}`).join("; ")}; bias within limits: {d.decision.BIAS_OK ? "yes" : "no"}.
      {" "}Against Raw: RMSE difference {intervalText(d.vs_raw.rmse, 2)} mm, heavy CSI {intervalText(d.vs_raw.heavy_csi, 3)}, very-heavy CSI {intervalText(d.vs_raw.very_heavy_csi, 3)}. {d.components}.</p>
  </div>;
}

export function ReforecastStudy() {
  const overview = useQuery({ queryKey: ["reforecast-overview"], queryFn: () => getReforecastOverview(), staleTime: 5 * 60_000 });
  const result = useQuery({ queryKey: ["reforecast-r05"], queryFn: () => getR05Result(), staleTime: 5 * 60_000 });
  const confirmation = useQuery({ queryKey: ["reforecast-r05-confirmation"], queryFn: () => getR05Confirmation(), staleTime: 5 * 60_000 });
  const failed = [overview, result, confirmation].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <section className="phase5-analysis-block"><ErrorState message={integrity ? `Reforecast study integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "The reforecast study evidence is unavailable."} /></section>;
  }
  if (!overview.data || !result.data || !confirmation.data) return <section className="phase5-analysis-block"><LoadingState label="Loading the reforecast study" /></section>;
  const ov = overview.data;
  const r = result.data;
  const p = r.payload;
  return <section className="phase5-analysis-block evidence-stack" aria-labelledby="reforecast-heading" data-testid="reforecast-study">
    <h2 id="reforecast-heading">Heavy-rain correction on independent reforecast years (sealed 2014-2016)</h2>
    <div className="zone-banner" role="note" data-testid="reforecast-banner"><strong>{r.evidence_label}</strong>
      <span>GEFSv12 reforecast control member, June to September. Trained on {ov.populations.train_years[0]}-{ov.populations.train_years[ov.populations.train_years.length - 1]}, selected on {ov.populations.validation_years.join(" and ")}; {p.cases} cases on {p.initialization_dates} initialization dates, {p.rows.toLocaleString("en-GB")} paired cells. Never pooled with the operational years.</span></div>
    <h3>Round 1: sealed years 2014-2016</h3>
    <div className="district-table-wrap"><table className="phase5-table zone-table" data-testid="reforecast-table">
      <caption className="sr-only">RMSE, bias, heavy-rain and very-heavy-rain skill of Raw and the frozen models on the sealed years</caption>
      <thead><tr><th scope="col">Model</th><th scope="col">RMSE (mm per 24 h)</th><th scope="col">Bias (mm)</th><th scope="col">Heavy CSI / frequency bias</th><th scope="col">Very-heavy CSI / frequency bias</th></tr></thead>
      <tbody>{R05_MODELS.filter((m) => p.pooled[m]).map((m) => { const x = p.pooled[m]; return <tr key={m} data-testid={`reforecast-row-${m}`}><th scope="row">{MODEL_LABEL[m]}</th><td>{fixed(x.rmse_mm, 3)}</td><td>{fixed(x.bias_mm, 3)}</td>
        <td>{fixed(x.heavy.csi, 3)} / {fixed(x.heavy.frequency_bias, 2)}</td><td>{fixed(x.very_heavy.csi, 3)} / {fixed(x.very_heavy.frequency_bias, 2)}</td></tr>; })}</tbody></table></div>
    <h4>Yes/no forecasts of heavy and very-heavy rain</h4>
    <div className="district-table-wrap"><table className="phase5-table zone-table" data-testid="reforecast-exceedance-table">
      <caption className="sr-only">Heavy and very-heavy rain yes/no forecasts: Raw against the exceedance classifiers on the sealed years</caption>
      <thead><tr><th scope="col">Forecast</th><th scope="col">Heavy CSI / frequency bias</th><th scope="col">Very-heavy CSI / frequency bias</th><th scope="col">Probability AUC (heavy / very heavy)</th></tr></thead>
      <tbody><tr data-testid="reforecast-exc-M0"><th scope="row">M0 Raw (rain at or above the threshold)</th><td>{fixed(p.raw_categorical.heavy.csi, 3)} / {fixed(p.raw_categorical.heavy.frequency_bias, 2)}</td><td>{fixed(p.raw_categorical.very_heavy.csi, 3)} / {fixed(p.raw_categorical.very_heavy.frequency_bias, 2)}</td><td>not a probability</td></tr>
        {["B0", "B1"].filter((a) => p.exceedance[`${a}:heavy`] && p.exceedance[`${a}:very_heavy`]).map((a) => { const h = p.exceedance[`${a}:heavy`]; const v = p.exceedance[`${a}:very_heavy`]; return <tr key={a} data-testid={`reforecast-exc-${a}`}><th scope="row">{a} exceedance classifiers (probability at or above a validation-fixed threshold)</th>
          <td>{fixed(h.test.csi, 3)} / {fixed(h.test.frequency_bias, 2)}</td><td>{fixed(v.test.csi, 3)} / {fixed(v.test.frequency_bias, 2)}</td><td>{fixed(h.auc, 3)} / {fixed(v.auc, 3)}</td></tr>; })}</tbody></table></div>
    <Decisions result={r} />
    <Confirmation result={confirmation.data} />
    <p className="micro-note">Observed event pairs in the sealed years: heavy {p.support.observed_event_pairs.heavy.toLocaleString("en-GB")}, very heavy {p.support.observed_event_pairs.very_heavy.toLocaleString("en-GB")}. Intervals: 95 percent for RMSE and 97.5 percent for the two CSI differences, whole initialization dates resampled (optimistic). Protocol {ov.protocol_sha256.slice(0, 12)}… · evidence {r.evidence_sha256.slice(0, 12)}….</p>
    <ul className="phase5-caveats">{ov.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
  </section>;
}
