import dynamic from "next/dynamic";
import { Metric, PageHeading, PageToc, PrototypeNote, SectionHeading } from "@/components/science/common";
import { getScience, modelComparisonSchema, verificationSchema } from "@/lib/api/science";
import { mm, score } from "@/lib/format";
import operational2025 from "@/lib/benchmarks/operational-2025.json";
import { OperationalVerification } from "@/components/verification/operational-verification";
import { TrackARegimeVerification } from "@/components/verification/track-a-regime-verification";
import { TrackADistrictVerification } from "@/components/verification/track-a-district-verification";
import { AllIndiaRawVerification } from "@/components/verification/all-india-raw-verification";
import { ReforecastStudy } from "@/components/verification/reforecast-study";

const Charts = dynamic(() => import("@/components/verification/verification-view"));
const names: Record<string, string> = { M0_RAW_GEFS: "Raw GEFS", M1_LINEAR_RIDGE_MOS: "Linear MOS", M2_GLOBAL_XGBOOST: "Global XGBoost", M3_HARD_REGIME_XGBOOST: "Hard Regime", M4_SOFT_REGIME_MOE: "Soft MoE" };

// Phase 5B, section 30: Track A (2019) is fetched directly from the live
// backend with no client-side static fallback, while Track B's operational
// benchmark section below is either a build-time bundled JSON or its own
// client component with its own fallback. Previously a single combined
// Promise.all().catch() meant a Track A outage blanked the *entire* page,
// including the Track B content that never needed Track A at all. Fetching
// it separately keeps that section live even when Track A is unreachable.
export default async function VerificationPage() {
  const trackA = await Promise.all([getScience("/model-comparison", modelComparisonSchema, true), getScience("/verification", verificationSchema, true)]).catch(() => null);
  const operationalReduction = (100 * (operational2025.raw_rmse_mm - operational2025.selected_rmse_mm) / operational2025.raw_rmse_mm).toFixed(2);
  return <div className="page-content verification-page"><PageHeading title="Scientific Verification" subtitle="Two separate completed historical experiments; different GEFS lineages and populations are not pooled." action={<PrototypeNote />} />
    <PageToc items={[...(trackA ? [{ id: "v-2019", label: "2019 benchmark" }] : []), { id: "v-regime", label: "Regime-aware (2019)" }, { id: "v-district", label: "District-level (2019)" }, { id: "v-2025", label: "2025 benchmark" }, { id: "v-allindia", label: "All-India (Raw)" }, { id: "v-reforecast", label: "Reforecast study" }]} />
    <div className="honesty-note"><strong>Two-track boundary</strong><p>Track A (NOAA GEFSv12 reforecast: the 2017-2019 sections and the 2014-2016 reforecast study) and Track B (2023-2025 historical operational GEFS: the 2025 section) are different GEFS lineages with different evaluation populations. Results are never pooled; each section states its own population and evidence label.</p></div>
    {trackA ? renderTrackA(trackA) : <div className="state-message" role="alert"><strong>2019 retrospective benchmark unavailable</strong><p>The Track A (2019 GEFSv12 reforecast) scientific API did not respond. The 2025 historical operational benchmark below is unaffected and does not depend on this API.</p></div>}
    <SectionHeading id="v-regime" title="Regime-aware verification · 2018 / 2019 reforecast" note="By forecast-only pseudo-regime and lead · all five models · downloadable report" />
    <TrackARegimeVerification />
    <SectionHeading id="v-district" title="District-level verification · 2018 / 2019 reforecast" note="District-case events and district-mean error · all five models · protocol frozen before any result" />
    <TrackADistrictVerification />
    <section className="operational-benchmark" id="v-2025" aria-labelledby="operational-benchmark-title"><h2 id="operational-benchmark-title">2025 operational-era historical benchmark</h2><p className="micro-note">Historical NOAA operational GEFS + IMD · one-time final test completed · {operational2025.case_count} cases / {operational2025.paired_cell_count.toLocaleString("en-US")} paired cells. Historical forecast maps are available in Forecast &amp; Atmosphere; they are not live forecasts.</p><div className="operational-benchmark-metrics"><Metric label="2025 Raw GEFS RMSE" value={mm(operational2025.raw_rmse_mm, 2)} /><Metric label="Preselected M1 Ridge RMSE" value={mm(operational2025.selected_rmse_mm, 2)} tone="teal" /><Metric label="2025 RMSE reduction" value={`${operationalReduction}%`} detail="M1 versus Raw; selected on 2024" /></div><p className="micro-note">M2 reached {mm(operational2025.secondary_m2_rmse_mm, 4)} RMSE as a predeclared secondary comparison; it does not replace the preselected M1 final-test headline. Source: frozen FINAL_TEST_RESULT (SHA-256 {operational2025.source_sha256.slice(0, 12)}…).</p><div className="honesty-note"><strong>Extreme-skill limit</strong><p>Continuous-rainfall RMSE improved on the 2025 test, but Raw GEFS retained stronger heavy and very-heavy spatial FSS at every reported scale. The 2025 probability models had positive Brier skill against the frozen reference, while very-heavy threshold FAR remained high ({score(operational2025.very_heavy_far)}).</p></div></section>
    <OperationalVerification />
    <SectionHeading id="v-allindia" title="All-India verification · Raw GEFS only" note="Whole IMD grid by region · no model applied outside the regional box · protocol frozen before any result" />
    <AllIndiaRawVerification />
    <SectionHeading id="v-reforecast" title="Reforecast heavy-rain study · sealed 2014-2016" note="GEFSv12 reforecast control, trained 2000-2011, selected 2012-2013, opened once · never pooled with the operational years" />
    <ReforecastStudy />
  </div>;
}

function renderTrackA([comparison, verification]: [import("@/lib/api/science").ModelComparison, import("@/lib/api/science").Verification]) {
  const raw = comparison.results.M0_RAW_GEFS.overall.continuous.rmse_mm;
  const global = comparison.results.M2_GLOBAL_XGBOOST.overall.continuous.rmse_mm;
  const reduction = ((raw - global) / raw * 100).toFixed(2);
  return <>
    <SectionHeading id="v-2019" title="2019 retrospective benchmark" note="NOAA GEFSv12 reforecast + IMD · 255 cases · completed held-out test" />
    <div className="verification-headline"><div><span className="small-label">2019 REFORECAST · PRIMARY DETERMINISTIC RESULT</span><strong>{reduction}% lower RMSE</strong><p>Global XGBoost versus Raw GEFS on the completed 2019 final test</p></div><div><Metric label="2019 Raw GEFS" value={mm(raw, 4)} /><Metric label="2019 Global XGBoost" value={mm(global, 4)} tone="teal" /><Metric label="Paired valid cells" value={comparison.results.M2_GLOBAL_XGBOOST.same_cell_count.toLocaleString("en-US")} /></div></div>
    <SectionHeading title="2019 model ladder" note="Same 2019 cases and valid-cell mask for M0–M4." /><div className="comparison-table-wrap" role="region" aria-label="2019 model ladder table" tabIndex={0}><table className="science-table"><caption className="sr-only">2019 retrospective deterministic model comparison</caption><thead><tr><th scope="col">Model</th><th scope="col">RMSE · mm</th><th scope="col">MAE · mm</th><th scope="col">Bias · mm</th><th scope="col">Heavy CSI</th><th scope="col">Very Heavy CSI</th></tr></thead><tbody>{Object.entries(comparison.results).map(([key, item]) => <tr key={key} className={key === "M2_GLOBAL_XGBOOST" ? "best-row" : ""}><th scope="row">{names[key] ?? key}{key === "M2_GLOBAL_XGBOOST" ? <span className="inline-badge">Best 2019 RMSE</span> : null}</th><td>{item.overall.continuous.rmse_mm.toFixed(4)}</td><td>{item.overall.continuous.mae_mm.toFixed(4)}</td><td>{item.overall.continuous.bias_mm.toFixed(4)}</td><td>{score(item.overall.thresholds.heavy_64_5.metrics.CSI)}</td><td>{score(item.overall.thresholds.very_heavy_115_6.metrics.CSI)}</td></tr>)}</tbody></table></div>
    <div className="honesty-note"><strong>2019 interpretation</strong><p>Soft routing improves on hard routing for RMSE, but neither beats Global ML. Raw GEFS remains stronger on deterministic Heavy and Very Heavy CSI/ETS and the reported FSS scales. Overall rainfall RMSE is not a substitute for extreme-event spatial skill.</p></div>
    <Charts comparison={comparison} verification={verification} />
  </>;
}
