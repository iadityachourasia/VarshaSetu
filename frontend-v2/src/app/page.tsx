import Link from "next/link";
import { ArrowRight, CloudRain, Compass, Database, MapPinned, ShieldCheck } from "lucide-react";
import { ErrorState, Metric, PrototypeNote, SectionHeading } from "@/components/science/common";
import { demoCasesSchema, getScience, modelComparisonSchema, statusSchema, verificationSchema } from "@/lib/api/science";
import { score, utc } from "@/lib/format";
import { defaultDemoCase } from "@/lib/demo";
import operational2025 from "@/lib/benchmarks/operational-2025.json";

export default async function OverviewPage() {
  const result = await Promise.all([
      getScience("/status", statusSchema, true), getScience("/model-comparison", modelComparisonSchema, true),
      getScience("/verification", verificationSchema, true), getScience("/demo-cases", demoCasesSchema, true),
    ]).catch(() => null);
  if (!result) return <div className="page-content"><ErrorState /></div>;
  const [status, comparison, verification, demos] = result;
    const raw = comparison.results.M0_RAW_GEFS.overall.continuous.rmse_mm;
    const corrected = comparison.results.M2_GLOBAL_XGBOOST.overall.continuous.rmse_mm;
    const reduction = ((raw - corrected) / raw * 100).toFixed(2);
    const demoId = defaultDemoCase(demos.cases, demos.cases);
    const demo = demos.cases.find((item) => item.case_id === demoId);
    return <div className="page-content overview-page">
      <div className="overview-hero"><div className="overview-main"><PrototypeNote /><h1>VarshaSetu</h1><p className="overview-subtitle">Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts</p><p className="overview-deck">Bridging Raw NWP Forecasts and Actionable Rainfall Intelligence.</p><div className="overview-actions"><Link className="primary-link" href={demo ? `/forecast?case=${encodeURIComponent(demo.case_id)}` : "/forecast"}>Explore forecast intelligence <ArrowRight size={16} /></Link><Link className="secondary-link" href="/verification">View scientific validation</Link></div></div>
        <div className="overview-result"><span className="small-label">2019 RETROSPECTIVE BENCHMARK · 255 CASES</span><strong>{reduction}<span>%</span></strong><p>lower RMSE on the GEFSv12 reforecast test</p><div className="result-pair"><span>Raw GEFS <b>{raw.toFixed(4)} mm</b></span><span>Global XGBoost <b>{corrected.toFixed(4)} mm</b></span></div><small>Best 2019 deterministic RMSE: frozen Phase 2B M2 Global XGBoost</small></div></div>
      <div className="overview-status"><span><ShieldCheck size={17} /> Scientific artifacts verified</span><span><Database size={17} /> Two distinct historical GEFS lineages</span><span>Final tests completed · not live</span></div>
      <div className="phase5-benchmark-pair" aria-label="Separate historical benchmark results">
        <article><div className="phase5-benchmark-heading"><span>RETROSPECTIVE GEFSv12 REFORECAST</span><strong>2019 final historical test</strong></div><div className="phase5-benchmark-main"><strong>−{reduction}%</strong><span>RMSE vs Raw GEFS</span></div><dl><div><dt>Raw</dt><dd>{raw.toFixed(2)} mm</dd></div><div><dt>Global XGBoost</dt><dd>{corrected.toFixed(2)} mm</dd></div><div><dt>Cases</dt><dd>{status.case_count}</dd></div></dl><Link href={demo ? `/forecast?experiment=reforecast&year=2019&case=${encodeURIComponent(demo.case_id)}` : "/forecast?experiment=reforecast&year=2019"}>Open 2019 cases <ArrowRight size={14} /></Link></article>
        <article><div className="phase5-benchmark-heading"><span>HISTORICAL OPERATIONAL GEFS</span><strong>2025 final historical test — completed</strong></div><div className="phase5-benchmark-main"><strong>−{((operational2025.raw_rmse_mm - operational2025.selected_rmse_mm) / operational2025.raw_rmse_mm * 100).toFixed(2)}%</strong><span>RMSE vs Raw GEFS</span></div><dl><div><dt>Raw</dt><dd>{operational2025.raw_rmse_mm.toFixed(2)} mm</dd></div><div><dt>Preselected M1 Ridge</dt><dd>{operational2025.selected_rmse_mm.toFixed(2)} mm</dd></div><div><dt>Cases</dt><dd>{operational2025.case_count}</dd></div></dl><Link href="/forecast?experiment=operational&year=2025">Open 2025 cases <ArrowRight size={14} /></Link></article>
      </div>
      <p className="phase5-caveat">Different GEFS lineages, model selections and evaluation populations. The 2019 and 2025 results are not pooled. In 2025, Raw GEFS retained better selected-model extreme-rain FSS despite improved M1 RMSE.</p>
      <div className="phase5-status-grid"><span><strong>CONTINUOUS RAINFALL</strong>2025 M1 reduced RMSE</span><span><strong>EXTREME SPATIAL SKILL</strong>Raw better than M1</span><span><strong>HEAVY PROBABILITY</strong>BSS +{operational2025.heavy_bss.toFixed(4)}</span><span><strong>VERY-HEAVY PROBABILITY</strong>BSS +{operational2025.very_heavy_bss.toFixed(4)} · high FAR</span><span><strong>REGIME CONDITIONING</strong>2025 M4 &gt; M3, neither &gt; M2</span><span><strong>DATA PROVENANCE</strong>NOAA + IMD · frozen audit</span></div>
      <SectionHeading title="Explore the 2019 evidence" note="These interactive views serve frozen GEFSv12 reforecast artifacts, not 2025 maps." />
      <div className="capability-grid"><Link href="/forecast" className="capability-feature"><Compass size={19} /><div><strong>Forecast Explorer</strong><p>Inspect Raw GEFS, corrected rainfall, and IMD observations on a shared 0.25° grid.</p></div><ArrowRight size={16} /></Link><Link href="/extremes" className="capability-feature"><CloudRain size={19} /><div><strong>Extreme Rain</strong><p>Calibrated Heavy and Very Heavy probabilities, reliability, and threshold skill.</p></div><ArrowRight size={16} /></Link><Link href="/districts" className="capability-feature"><MapPinned size={19} /><div><strong>District Intelligence</strong><p>{status.district_count} intersecting districts with area-weighted rainfall and probability summaries.</p></div><ArrowRight size={16} /></Link></div>
      <div className="overview-evidence"><div><span className="small-label">2019 REFORECAST · SCIENTIFIC BOUNDARY</span><h2>Skill is metric-specific.</h2><p>The 2019 global correction improves overall rainfall RMSE. Regime-aware deterministic variants do not beat it, while Raw GEFS remains stronger on deterministic extreme-event CSI/ETS and the reported FSS scales.</p><Link href="/verification" className="text-link">Compare both historical benchmarks <ArrowRight size={14} /></Link></div><div className="evidence-metrics"><Metric label="Heavy probability · Brier" value={score(verification.metrics.targets.heavy.brier, 4)} detail="Held-out 2019" /><Metric label="Very Heavy · PR-AUC" value={score(verification.metrics.targets.very_heavy.pr_auc)} detail="Held-out 2019" /><Metric label="Official demo cases" value={String(demos.cases.length)} detail={demo ? `First case: ${utc(demo.initialization_utc)}` : "Historical catalogue"} /></div></div>
      <p className="overview-footnote">Historical scientific prototype only. Not live forecasting, operational readiness, or current-date GEFS ingestion.</p>
    </div>;
}
