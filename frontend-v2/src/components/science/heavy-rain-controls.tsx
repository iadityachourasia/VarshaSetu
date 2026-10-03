"use client";

import { useQuery } from "@tanstack/react-query";
import { getHeavyRainOverview } from "@/lib/api/heavy-rain";
import { mm } from "@/lib/format";

export type CorrectedModel = "m2" | "b1";

/** The two corrected-rainfall models available on the 2019 product. M2 is the frozen global model the product always showed; B1 is the frozen heavy-rain bundle of the reforecast study. */
export function CorrectedModelChoice({ value, onChange }: { value: CorrectedModel; onChange: (next: CorrectedModel) => void }) {
  return <div className="corrected-model-choice" data-testid="corrected-model-choice">
    <span className="small-label">CORRECTED MODEL</span>
    <div className="segmented" role="group" aria-label="Corrected model">
      <button type="button" className={value === "m2" ? "selected" : ""} aria-pressed={value === "m2"} onClick={() => onChange("m2")}>M2 · global model (frozen)</button>
      <button type="button" className={value === "b1" ? "selected" : ""} aria-pressed={value === "b1"} onClick={() => onChange("b1")}>B1 · heavy-rain bundle (reforecast study)</button>
    </div>
  </div>;
}

/**
 * What the heavy-rain layer is and is not, shown wherever it is shown. The governed evidence label is printed in full, the 2019 numbers come from the frozen overview, and the limits are listed rather than linked.
 */
export function HeavyRainNotice() {
  const overview = useQuery({ queryKey: ["heavy-rain-overview"], queryFn: getHeavyRainOverview, staleTime: 10 * 60_000 });
  if (overview.isError) return <div className="zone-banner" role="alert" data-testid="heavy-rain-notice"><strong>Heavy-rain layer unavailable</strong><span>{overview.error instanceof Error ? overview.error.message : "The frozen layer could not be verified."}</span></div>;
  if (!overview.data) return <div className="zone-banner" data-testid="heavy-rain-notice"><strong>Loading the heavy-rain layer…</strong></div>;
  const o = overview.data;
  const rain = o.summary.rainfall;
  return <section className="heavy-rain-notice" data-testid="heavy-rain-notice" aria-label="About the heavy-rain bundle">
    <div className="zone-banner zone-banner-posthoc" role="note"><strong>{o.evidence_label}</strong>
      <span>Heavy-rain bundle B1 from the reforecast study, shown beside the frozen global model. {o.bundle_label}</span></div>
    <p className="micro-note" data-testid="heavy-rain-summary">Across the {o.summary.cases} cases of this product ({o.summary.cells.toLocaleString("en-GB")} cells): RMSE B1 {mm(rain.B1.rmse_mm, 2)} · global model M2 {mm(rain.M2.rmse_mm, 2)} · Raw {mm(rain.M0.rmse_mm, 2)}.
      Mean error of B1 on these cases {mm(rain.B1.bias_mm, 2)}, which is {o.slice_bias_within_limit ? "within" : "above"} the frozen guardrail of {mm(o.bias_guardrail_mm, 1)}. On the pooled confirmatory years the frozen decision tier was {o.confirmation.tier} and the mean error was {o.confirmation.bias_within_limit ? "within" : "above"} the guardrail.</p>
    <details><summary>What this layer is, and what it is not</summary><ul className="phase5-caveats">{o.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
      <p className="micro-note">Protocol {o.protocol_sha256.slice(0, 12)}… · manifest {o.manifest_sha256.slice(0, 12)}… · arrays {o.arrays_sha256.slice(0, 12)}… · verified on every request.</p></details>
  </section>;
}
