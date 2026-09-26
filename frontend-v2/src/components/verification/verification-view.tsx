"use client";

import { useState } from "react";
import type { ModelComparison, Verification } from "@/lib/api/science";
import { FssChart, ReliabilityChart, RmseChart } from "./verification-charts";
import { score } from "@/lib/format";
import { SectionHeading } from "@/components/science/common";

export default function VerificationView({ comparison, verification }: { comparison: ModelComparison; verification: Verification }) {
  const [threshold, setThreshold] = useState<"heavy" | "very_heavy">("heavy");
  const metric = verification.metrics.targets[threshold];
  return <>
    <div className="verification-grid"><div><SectionHeading title="RMSE comparison" /><RmseChart comparison={comparison} /></div><div><SectionHeading title="Probability quality" note="Held-out 2019" /><div className="prob-quality"><div><span>Heavy</span><strong>Brier {score(verification.metrics.targets.heavy.brier, 4)}</strong><small>PR-AUC {score(verification.metrics.targets.heavy.pr_auc)}</small></div><div><span>Very Heavy</span><strong>Brier {score(verification.metrics.targets.very_heavy.brier, 4)}</strong><small>PR-AUC {score(verification.metrics.targets.very_heavy.pr_auc)}</small></div></div><p className="micro-note">Very-heavy false-alarm ratio at its frozen threshold is {score(verification.metrics.targets.very_heavy.categorical.metrics.FAR)}. Sparse events limit confidence in upper probability bins.</p></div></div>
    <SectionHeading title="Extreme spatial skill and reliability" note="Actual 2-D fields and frozen calibrated probabilities." /><div className="segmented" role="group" aria-label="Event threshold"><button type="button" className={threshold === "heavy" ? "selected" : ""} onClick={() => setThreshold("heavy")}>Heavy · ≥64.5 mm</button><button type="button" className={threshold === "very_heavy" ? "selected" : ""} onClick={() => setThreshold("very_heavy")}>Very Heavy · ≥115.6 mm</button></div>
    <div className="verification-grid"><div><h3>Fractions Skill Score</h3><FssChart verification={verification} threshold={threshold} /><table className="mini-table"><caption>FSS values and eligible case counts</caption><thead><tr><th>Scale</th><th>Raw FSS / cases</th><th>Corrected FSS / cases</th></tr></thead><tbody>{["1", "3", "5", "9"].map((scale) => { const pair = verification.metrics.fss[threshold][scale]; return <tr key={scale}><th>{scale}×{scale}</th><td>{score(pair.raw.fss)} / {pair.raw.case_count}</td><td>{score(pair.corrected.fss)} / {pair.corrected.case_count}</td></tr>; })}</tbody></table></div><div><h3>Probability reliability</h3><ReliabilityChart verification={verification} threshold={threshold} /><table className="mini-table"><caption>Reliability bins with observed frequencies</caption><thead><tr><th>Predicted bin</th><th>Samples</th><th>Observed</th></tr></thead><tbody>{metric.reliability.map((bin) => <tr key={bin.bin_lower}><th>{Math.round(bin.bin_lower * 100)}–{Math.round(bin.bin_upper * 100)}%</th><td>{bin.sample_count.toLocaleString("en-US")}</td><td>{bin.observed_event_frequency == null ? "Undefined — no samples" : `${(bin.observed_event_frequency * 100).toFixed(1)}%`}</td></tr>)}</tbody></table></div></div>
  </>;
}
