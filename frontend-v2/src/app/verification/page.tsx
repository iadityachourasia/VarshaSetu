import dynamic from "next/dynamic";
import { ErrorState, Metric, PageHeading, PrototypeNote, SectionHeading } from "@/components/science/common";
import { getScience, modelComparisonSchema, verificationSchema } from "@/lib/api/science";
import { mm, score } from "@/lib/format";
import operational2025 from "@/lib/benchmarks/operational-2025.json";
import { OperationalVerification } from "@/components/verification/operational-verification";

const Charts = dynamic(() => import("@/components/verification/verification-view"));
const names: Record<string, string> = { M0_RAW_GEFS: "Raw GEFS", M1_LINEAR_RIDGE_MOS: "Linear MOS", M2_GLOBAL_XGBOOST: "Global XGBoost", M3_HARD_REGIME_XGBOOST: "Hard Regime", M4_SOFT_REGIME_MOE: "Soft MoE" };

export default async function VerificationPage() {
  const result = await Promise.all([getScience("/model-comparison", modelComparisonSchema, true), getScience("/verification", verificationSchema, true)]).catch(() => null);
  if (!result) return <div className="page-content"><ErrorState /></div>;
  const [comparison, verification] = result;
    const raw = comparison.results.M0_RAW_GEFS.overall.continuous.rmse_mm;
    const global = comparison.results.M2_GLOBAL_XGBOOST.overall.continuous.rmse_mm;
    const reduction = ((raw - global) / raw * 100).toFixed(2);
    const operationalReduction = (100 * (operational2025.raw_rmse_mm - operational2025.selected_rmse_mm) / operational2025.raw_rmse_mm).toFixed(2);
    return <div className="page-content verification-page"><PageHeading title="Scientific Verification" subtitle="Two separate completed historical experiments; different GEFS lineages and populations are not pooled." action={<PrototypeNote />} />
      <SectionHeading title="2019 retrospective benchmark" note="NOAA GEFSv12 reforecast + IMD · 255 cases · completed held-out test" />
      <div className="verification-headline"><div><span className="small-label">2019 REFORECAST · PRIMARY DETERMINISTIC RESULT</span><strong>{reduction}% lower RMSE</strong><p>Global XGBoost versus Raw GEFS on the completed 2019 final test</p></div><div><Metric label="2019 Raw GEFS" value={mm(raw, 4)} /><Metric label="2019 Global XGBoost" value={mm(global, 4)} tone="teal" /><Metric label="Paired valid cells" value={comparison.results.M2_GLOBAL_XGBOOST.same_cell_count.toLocaleString("en-US")} /></div></div>
      <SectionHeading title="2019 model ladder" note="Same 2019 cases and valid-cell mask for M0–M4." /><div className="comparison-table-wrap"><table className="science-table"><caption className="sr-only">2019 retrospective deterministic model comparison</caption><thead><tr><th scope="col">Model</th><th scope="col">RMSE · mm</th><th scope="col">MAE · mm</th><th scope="col">Bias · mm</th><th scope="col">Heavy CSI</th><th scope="col">Very Heavy CSI</th></tr></thead><tbody>{Object.entries(comparison.results).map(([key, item]) => <tr key={key} className={key === "M2_GLOBAL_XGBOOST" ? "best-row" : ""}><th scope="row">{names[key] ?? key}{key === "M2_GLOBAL_XGBOOST" ? <span className="inline-badge">Best 2019 RMSE</span> : null}</th><td>{item.overall.continuous.rmse_mm.toFixed(4)}</td><td>{item.overall.continuous.mae_mm.toFixed(4)}</td><td>{item.overall.continuous.bias_mm.toFixed(4)}</td><td>{score(item.overall.thresholds.heavy_64_5.metrics.CSI)}</td><td>{score(item.overall.thresholds.very_heavy_115_6.metrics.CSI)}</td></tr>)}</tbody></table></div>
      <div className="honesty-note"><strong>2019 interpretation</strong><p>Soft routing improves on hard routing for RMSE, but neither beats Global ML. Raw GEFS remains stronger on deterministic Heavy and Very Heavy CSI/ETS and the reported FSS scales. Overall rainfall RMSE is not a substitute for extreme-event spatial skill.</p></div>
      <section className="operational-benchmark" aria-labelledby="operational-benchmark-title"><h2 id="operational-benchmark-title">2025 operational-era historical benchmark</h2><p className="micro-note">Historical NOAA operational GEFS + IMD · one-time final test completed · {operational2025.case_count} cases / {operational2025.paired_cell_count.toLocaleString("en-US")} paired cells. Historical forecast maps are available in Forecast &amp; Atmosphere; they are not live forecasts.</p><div className="operational-benchmark-metrics"><Metric label="2025 Raw GEFS RMSE" value={mm(operational2025.raw_rmse_mm, 2)} /><Metric label="Preselected M1 Ridge RMSE" value={mm(operational2025.selected_rmse_mm, 2)} tone="teal" /><Metric label="2025 RMSE reduction" value={`${operationalReduction}%`} detail="M1 versus Raw; selected on 2024" /></div><p className="micro-note">M2 reached {mm(operational2025.secondary_m2_rmse_mm, 4)} RMSE as a predeclared secondary comparison; it does not replace the preselected M1 final-test headline. Source: frozen FINAL_TEST_RESULT (SHA-256 {operational2025.source_sha256.slice(0, 12)}…).</p><div className="honesty-note"><strong>Extreme-skill limit</strong><p>Continuous-rainfall RMSE improved on the 2025 test, but Raw GEFS retained stronger heavy and very-heavy spatial FSS at every reported scale. The 2025 probability models had positive Brier skill against the frozen reference, while very-heavy threshold FAR remained high ({score(operational2025.very_heavy_far)}).</p></div></section>
      <OperationalVerification />
      <Charts comparison={comparison} verification={verification} />
    </div>;
}
