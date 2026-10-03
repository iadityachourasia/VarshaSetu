import Link from "next/link";
import { Activity, ArrowRight, ChevronRight, CircleAlert, Cloud, CloudRain, Database, Grid2X2, MapPin, Settings2, Zap } from "lucide-react";
import { BenchmarkChart } from "@/components/overview/benchmark-chart";
import { ErrorState, Metric, SectionHeading } from "@/components/science/common";
import { casesSchema, demoCasesSchema, getScience, modelComparisonSchema, statusSchema, verificationSchema } from "@/lib/api/science";
import { getOperationalCases } from "@/lib/api/operational";
import { overview2025, resolve2019Overview, type Overview2019Source, type OverviewBenchmark } from "@/lib/overview-data";
import { score, utc } from "@/lib/format";
import { CountUp } from "@/components/ui/count-up";
import { defaultDemoCase } from "@/lib/demo";
import operational2025 from "@/lib/benchmarks/operational-2025.json";

function BenchmarkPanel({ benchmark, year, href, source }: { benchmark: OverviewBenchmark | null; year: 2019 | 2025; href: string; source?: Overview2019Source }) {
  const is2025 = year === 2025;
  return <article className={(is2025 ? "overview-benchmark-2025" : "overview-benchmark-2019") + (benchmark ? "" : " overview-benchmark-unavailable")}>
    <div className="phase5-benchmark-heading">
      <span>{is2025 ? "2025 · HISTORICAL OPERATIONAL GEFS" : "2019 · GEFSv12 REFORECAST"}</span>
      <strong><Database size={16} aria-hidden="true" /> {benchmark ? benchmark.caseCount + " cases" : "Data unavailable"}</strong>
    </div>
    {benchmark ? <>
      <div className="phase5-benchmark-summary">
        <p className="overview-benchmark-context">{is2025 ? "Completed final test · preselected M1 Ridge MOS" : "Held-out test · M2 Global XGBoost"}</p>
        {source === "verified_snapshot" ? <p className="overview-source-note">API unreachable · verified frozen 2019 snapshot</p> : null}
        <p className="overview-benchmark-improvement"><strong><CountUp value={benchmark.reductionPercent} /><span>%</span></strong><span>lower aggregate RMSE<br />than Raw GEFS</span></p>
        <div className="overview-benchmark-values"><span><small>Raw GEFS</small><b><CountUp value={benchmark.raw.toFixed(2)} /> mm</b></span><ArrowRight size={18} aria-hidden="true" /><span><small>Corrected</small><b><CountUp value={benchmark.corrected.toFixed(2)} /> mm</b></span></div>
      </div>
      <BenchmarkChart points={benchmark.series} year={year} raw={benchmark.raw} corrected={benchmark.corrected} correctedLabel={is2025 ? "M1 Ridge MOS" : "M2 Global XGBoost"} />
      <Link className="overview-benchmark-link" href={href}>Open {year} cases <ArrowRight size={16} aria-hidden="true" /></Link>
    </> : <ErrorState message={is2025 ? "The pinned 2025 final-test result could not be validated." : "The 2019 comparison could not be verified from the read-only scientific API."} />}
  </article>;
}

export default async function OverviewPage() {
  const [statusResult, comparisonResult, verificationResult, demosResult, casesResult, operationalResult] = await Promise.allSettled([
    getScience("/status", statusSchema, true),
    getScience("/model-comparison", modelComparisonSchema, true),
    getScience("/verification", verificationSchema, true),
    getScience("/demo-cases", demoCasesSchema, true),
    getScience("/cases", casesSchema, true),
    getOperationalCases(2025, { pageSize: 400 }, true),
  ]);
  const { benchmark: benchmark2019, source: source2019, status } = resolve2019Overview(statusResult, comparisonResult, casesResult);
  const verification = verificationResult.status === "fulfilled" ? verificationResult.value : null;
  const demos = demosResult.status === "fulfilled" ? demosResult.value : null;
  const operationalCases = operationalResult.status === "fulfilled" ? operationalResult.value : null;
  const benchmark2025 = overview2025(operationalCases);
  const demos2019 = status && demos?.provenance.artifact_manifest_sha256 === status.provenance.artifact_manifest_sha256 ? demos : null;
  const verification2019 = benchmark2019 && status && verification?.provenance.artifact_manifest_sha256 === status.provenance.artifact_manifest_sha256 ? verification : null;
  const demoId = demos2019 ? defaultDemoCase(demos2019.cases, demos2019.cases) : null;
  const demo = demos2019?.cases.find((item) => item.case_id === demoId);
  const forecast2019Href = demo
    ? "/forecast?experiment=reforecast&year=2019&case=" + encodeURIComponent(demo.case_id)
    : "/forecast?experiment=reforecast&year=2019";

  return <div className="page-content overview-page">
    <section className="overview-hero" aria-labelledby="overview-title">
      <div className="overview-main">
        <h1 id="overview-title">Varsha<span>Setu</span></h1>
        <p className="overview-subtitle">Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts</p>
        <p className="overview-deck">Explore historical GEFS rainfall, post-processing, and held-out verification against IMD reference data.</p>
        <div className="overview-actions">
          <Link className="primary-link" href={forecast2019Href} aria-label="Explore 2019 forecast intelligence">Explore forecast intelligence <ArrowRight size={20} aria-hidden="true" /></Link>
          <Link className="secondary-link" href="/verification">View scientific validation</Link>
        </div>
      </div>
      <aside className="overview-result" aria-label="2019 retrospective benchmark">
        {benchmark2019 ? <>
          <span className="small-label">2019 GEFSv12 REFORECAST · {benchmark2019.caseCount} HELD-OUT CASES</span>
          {source2019 === "verified_snapshot" ? <span className="overview-source-note">API unreachable · verified frozen 2019 snapshot</span> : null}
          <strong><CountUp value={benchmark2019.reductionPercent} /><span>%</span></strong>
          <p>lower aggregate RMSE than Raw GEFS</p>
          <div className="result-pair">
            <span>Raw GEFS <b><CountUp value={benchmark2019.raw.toFixed(2)} /> mm</b></span>
            <span>M2 Global XGBoost <b><CountUp value={benchmark2019.corrected.toFixed(2)} /> mm</b></span>
          </div>
          <small>Frozen 2019 final test · 24-hour rainfall</small>
        </> : <ErrorState message="The 2019 scientific API result is unavailable. Its values are hidden until the historical artifacts can be verified." />}
      </aside>
    </section>

    <div className="phase5-benchmark-pair" aria-label="Separate historical benchmark results">
      <BenchmarkPanel benchmark={benchmark2019} year={2019} href={forecast2019Href} source={source2019} />
      <BenchmarkPanel benchmark={benchmark2025} year={2025} href="/forecast?experiment=operational&year=2025" />
    </div>
    <Link className="phase5-caveat" href="/verification">
      <CircleAlert size={17} aria-hidden="true" />
      <span>Different GEFS lineages, models, and evaluation populations. The 2019 and 2025 results are not pooled. In 2025, Raw GEFS retained better Heavy and Very Heavy spatial FSS than selected M1 despite M1’s lower RMSE.</span>
      <ChevronRight size={17} aria-hidden="true" />
    </Link>

    {benchmark2025 ? <>
      <ul className="overview-evidence-row" aria-label="2025 source-scoped scientific evidence">
        <li className="overview-evidence-item"><Cloud size={27} aria-hidden="true" /><span><strong>CONTINUOUS RAINFALL</strong><small>2025 M1 · {benchmark2025.reductionPercent}% lower RMSE</small></span></li>
        <li className="overview-evidence-item"><Grid2X2 size={27} aria-hidden="true" /><span><strong>EXTREME SPATIAL SKILL</strong><small>Raw better than M1 on FSS</small></span></li>
        <li className="overview-evidence-item"><CloudRain size={27} aria-hidden="true" /><span><strong>HEAVY PROBABILITY</strong><small>BSS +{operational2025.heavy_bss.toFixed(4)} · FAR {(operational2025.heavy_far * 100).toFixed(1)}%</small></span></li>
        <li className="overview-evidence-item"><Zap size={27} aria-hidden="true" /><span><strong>VERY-HEAVY PROBABILITY</strong><small>BSS +{operational2025.very_heavy_bss.toFixed(4)} · FAR {(operational2025.very_heavy_far * 100).toFixed(1)}%</small></span></li>
        <li className="overview-evidence-item"><Settings2 size={27} aria-hidden="true" /><span><strong>REGIME CONDITIONING</strong><small>2025 M4 beat M3; neither beat M2</small></span></li>
        <li className="overview-evidence-item"><Database size={27} aria-hidden="true" /><span><strong>DATA PROVENANCE</strong><small>NOAA GEFS · IMD · frozen test</small></span></li>
      </ul>
    </> : null}

    <SectionHeading title="Explore the 2019 evidence" />
    <div className="capability-grid">
      <Link href={forecast2019Href} className="capability-feature capability-forecast">
        <span className="capability-icon" aria-hidden="true"><Activity size={25} strokeWidth={1.7} /></span>
        <span className="capability-copy"><strong>Forecast Explorer</strong><span>Inspect Raw GEFS, corrected rainfall, and IMD observations on a shared 0.25° grid.</span></span>
        <span className="capability-arrow" aria-hidden="true"><ArrowRight size={19} /></span>
      </Link>
      <Link href="/extremes?experiment=reforecast&year=2019" className="capability-feature capability-extremes">
        <span className="capability-icon" aria-hidden="true"><CloudRain size={25} strokeWidth={1.7} /></span>
        <span className="capability-copy"><strong>Extreme Rain</strong><span>Inspect Heavy and Very Heavy probabilities, reliability, and threshold skill.</span></span>
        <span className="capability-arrow" aria-hidden="true"><ArrowRight size={19} /></span>
      </Link>
      <Link href="/districts?experiment=reforecast&year=2019" className="capability-feature capability-districts">
        <span className="capability-icon" aria-hidden="true"><MapPin size={25} strokeWidth={1.7} /></span>
        <span className="capability-copy"><strong>District Intelligence</strong><span>{status ? status.district_count + " intersecting districts" : "Historical district summaries"} with area-weighted rainfall and probability summaries.</span></span>
        <span className="capability-arrow" aria-hidden="true"><ArrowRight size={19} /></span>
      </Link>
    </div>

    {benchmark2019 ? <div className="overview-evidence"><div><span className="small-label">2019 REFORECAST · SCIENTIFIC BOUNDARY</span><h2>Skill is metric-specific.</h2><p>The global correction improved overall rainfall RMSE. Regime-aware deterministic variants did not beat it, while Raw GEFS remained stronger on deterministic extreme-event CSI/ETS and reported FSS scales.</p><Link href="/verification" className="text-link">Compare both historical benchmarks <ArrowRight size={16} aria-hidden="true" /></Link></div><div className="evidence-metrics">{verification2019 ? <><Metric label="Heavy probability · Brier" value={score(verification2019.metrics.targets.heavy.brier, 4)} detail="Held-out 2019" /><Metric label="Very Heavy · PR-AUC" value={score(verification2019.metrics.targets.very_heavy.pr_auc)} detail="Held-out 2019" /></> : <p className="overview-unavailable">2019 verification metrics unavailable from the scientific API.</p>}{demos2019 ? <Metric label="Official demo cases" value={String(demos2019.cases.length)} detail={demo ? "First case: " + utc(demo.initialization_utc) : "Historical catalogue"} /> : null}</div></div>
      : <div className="overview-evidence overview-evidence-unavailable"><ErrorState message="2019 scientific evidence is unavailable until the read-only API returns verified artifacts." /></div>}
  </div>;
}
