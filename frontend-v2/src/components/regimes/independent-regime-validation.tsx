"use client";

import { EvidenceChip } from "@/components/science/evidence-chip";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/science/common";
import { EvidenceApiError } from "@/lib/api/evidence";
import {
  OBSERVED_STATES, VALIDATION_YEARS, getRegimeValidationOverview, getRegimeValidationResult, type RegimeValidationResult,
} from "@/lib/api/regime-validation";
import { regimeName } from "@/lib/format";
import { HashChip } from "@/components/ui/hash-chip";

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
type TaskKey = "active_vs_not_active" | "break_vs_not_break";

function taskCell(result: RegimeValidationResult, key: TaskKey) {
  const t = result.payload.tasks[key];
  if (t.status !== "scored") return <span data-status="insufficient_support">insufficient support ({t.observed_cases} observed cases)</span>;
  const interval = t.balanced_accuracy_bootstrap?.interval95;
  return <span data-status="scored"><strong>{fixed(t.balanced_accuracy, 3)}</strong>{interval ? ` [${fixed(interval[0], 3)}, ${fixed(interval[1], 3)}]` : ""} · recall {fixed(t.recall, 2)} · precision {fixed(t.precision, 2)}</span>;
}

export function IndependentRegimeValidation() {
  const overview = useQuery({ queryKey: ["regime-validation-overview"], queryFn: () => getRegimeValidationOverview(), staleTime: 5 * 60_000 });
  const results = useQueries({ queries: VALIDATION_YEARS.map((year) => ({ queryKey: ["regime-validation-result", year], queryFn: () => getRegimeValidationResult(year), staleTime: 5 * 60_000 })) });
  const [year, setYear] = useState<number>(2019);

  const failed = [overview, ...results].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <section className="phase5-analysis-block"><ErrorState message={integrity ? `Independent regime validation integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "Independent regime validation is unavailable."} /></section>;
  }
  if (!overview.data || results.some((q) => !q.data)) return <section className="phase5-analysis-block"><LoadingState compact label="Loading independent regime validation" /></section>;
  const ov = overview.data;
  const all = results.map((q) => q.data!);
  const scored = all.filter((r) => r.payload.tasks.active_vs_not_active.status === "scored");
  const below = scored.filter((r) => { const t = r.payload.tasks.active_vs_not_active; return t.status === "scored" && t.balanced_accuracy != null && t.balanced_accuracy < 0.5; });
  const selected = all.find((r) => r.year === year) ?? all[0];
  const table = selected.payload.confusion_predicted_class_by_observed_state;
  const lowShare = scored.map((r) => {
    const t = r.payload.confusion_predicted_class_by_observed_state;
    const total = Object.values(t).reduce((a, row) => a + row.ACTIVE, 0);
    return { year: r.year, low: t.LOW_DEPRESSION_INFLUENCED.ACTIVE, active: t.ACTIVE_MONSOON.ACTIVE, total };
  });

  return <section className="phase5-analysis-block" aria-labelledby="regime-validation-heading" data-testid="regime-validation">
    <h2 id="regime-validation-heading">Independent check against observed active and break spells</h2>
    <div className="zone-banner zone-banner-posthoc" role="note" data-testid="regime-validation-banner"><strong>Partial validation, not the published classification, depression not validated</strong>
      <span>The classes below are pseudo-labels from a forecast-only rule. This panel checks them against rainfall-based active and break spells computed from IMD observations, in the style of Rajeevan et al. (2010) with {ov.criteria.deviations_from_the_published_work.length} documented deviations. It is separate from the pseudo-label agreement figures.</span></div>
    <p data-testid="regime-validation-reading">{scored.length === 0 ? "No population met the support gate, so nothing was scored." : `${scored.length} of ${all.length} populations met the support gate for the active task (${scored.map((r) => r.year).join(" and ")}); the break task met it in ${all.filter((r) => r.payload.tasks.break_vs_not_break.status === "scored").length}. `}
      {scored.length ? `In ${below.length} of ${scored.length} scored populations the balanced accuracy for active versus not active is below the chance level of 0.5. ` : ""}
      {lowShare.length ? `Most observed active days were classified as the low/depression pseudo-class, not the active pseudo-class (${lowShare.map((s) => `${s.year}: ${s.low} against ${s.active} of ${s.total}`).join("; ")}). ` : ""}
      So the pseudo-class named Active does not correspond to observed active spells on this evidence, and the break and depression classes could not be validated.</p>
    <div className="district-table-wrap"><table className="phase5-table zone-table">
      <caption className="sr-only">Observed-state counts and the pre-registered tasks by population</caption>
      <thead><tr><th scope="col">Population</th><th scope="col">Labelled cases</th><th scope="col">Observed active / break / neutral</th><th scope="col">Active versus not active: balanced accuracy [95 % interval]</th><th scope="col">Break versus not break</th></tr></thead>
      <tbody>{all.map((r) => <tr key={r.year} data-testid={`validation-row-${r.year}`}><th scope="row"><EvidenceChip label={r.evidence_label} /><br /><span className="micro-note">Track {r.track} · {r.year}</span></th><td>{r.payload.cases_labelled}</td>
        <td>{r.payload.observed_state_counts.ACTIVE} / {r.payload.observed_state_counts.BREAK} / {r.payload.observed_state_counts.NEUTRAL}</td><td>{taskCell(r, "active_vs_not_active")}</td><td>{taskCell(r, "break_vs_not_break")}</td></tr>)}</tbody></table></div>
    <p className="micro-note">The support gate needs at least {ov.support_gate.min_cases_per_side} cases on both sides of a task; below it no score is shown. A balanced accuracy of 0.5 is no skill; the intervals resample whole initialization dates and are optimistic.</p>
    <div className="phase5-controls"><label>Population for the confusion table<select value={selected.year} onChange={(event) => setYear(Number(event.target.value))}>{all.map((r) => <option key={r.year} value={r.year}>{r.evidence_label}</option>)}</select></label></div>
    <div className="district-table-wrap"><table className="phase5-table zone-table" data-testid="validation-confusion">
      <caption className="sr-only">Predicted regime class by observed state for the selected population</caption>
      <thead><tr><th scope="col">Predicted class</th>{OBSERVED_STATES.map((s) => <th scope="col" key={s}>Observed {s.toLowerCase()}</th>)}</tr></thead>
      <tbody>{Object.entries(table).map(([name, row]) => <tr key={name}><th scope="row">{regimeName(name)}</th>{OBSERVED_STATES.map((s) => <td key={s}>{row[s]}</td>)}</tr>)}</tbody></table></div>
    <details><summary>Criteria, deviations and what was frozen before any score</summary>
      <ul className="phase5-caveats">{ov.criteria.deviations_from_the_published_work.map((d) => <li className="phase5-caveat" key={d}>{d}</li>)}</ul>
      <p>Core-zone box {ov.criteria.core_zone_box.lat.join(" to ")} N, {ov.criteria.core_zone_box.lon.join(" to ")} E; anomaly at least {ov.criteria.threshold_sd} standard deviation for at least {ov.criteria.min_spell_days} consecutive days; labels for months {ov.criteria.label_window_months.join(" and ")} only; climatology {ov.criteria.climatology.years.join(" to ")} ({ov.criteria.climatology.files} IMD files, no year shared with any evaluated population). {ov.approval.note}</p></details>
    <ul className="phase5-caveats">{ov.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
    <p className="micro-note">Protocol <HashChip hash={ov.protocol_sha256} /> · manifest <HashChip hash={ov.manifest_sha256} />. Historical scientific prototype.</p>
  </section>;
}
