import { ArrowDown, BookOpen, Database, FlaskConical, ShieldCheck } from "lucide-react";
import { ErrorState, PageHeading, PrototypeNote, SectionHeading } from "@/components/science/common";
import { getScience, statusSchema } from "@/lib/api/science";

const pipeline = [
  ["01", "NOAA GEFSv12 Reforecast", "Historical numerical weather prediction input; not live ingestion."],
  ["02", "Canonical 24-hour rainfall", "Forecast-accumulation reconstruction on the validated target grid."],
  ["03", "Parallel forecast-only models", "In the 2019 reforecast track, primary M2 Global XGBoost correction uses no regime inputs. A separate classifier estimates pseudo-regime probabilities; hard/soft routing are comparators."],
  ["04", "Extreme-event probabilities", "Separate calibrated Heavy and Very Heavy event models may use corrected rainfall and forecast-only regime probabilities."],
  ["05", "District aggregation", "Grid-cell polygon overlap weights for intersecting districts."],
  ["06", "Verification", "The completed 2019 final test reports error, event, reliability, and 2-D spatial skill; 2025 is a separate experiment."],
] as const;

// Phase 5B, section 30: this page is almost entirely static prose (the
// pipeline, track timelines, and method-grid never call an API). Only the
// small "method-status" strip and the "provenance-band" footer need the
// live Track A /status call. Previously the whole page was gated behind
// that one call and blanked entirely if it failed; now the static content
// always renders and only those two small live-data strips degrade.
export default async function MethodologyPage() {
  const status = await getScience("/status", statusSchema, true).catch(() => null);
  return <div className="page-content methodology-page"><PageHeading title="Methodology" subtitle="From historical NWP forecast to verifiable rainfall intelligence." action={<PrototypeNote />} />
      <div className="method-intro"><div><span className="small-label">SCIENTIFIC CHAIN</span><h2>Every output has a documented lineage.</h2><p>VarshaSetu separates forecast-time inputs from observation-based verification. The interface reads frozen artifacts; it never trains a model or decodes GRIB during a request.</p></div>{status ? <div className="method-status"><ShieldCheck size={19} /><span>Historical prototype artifacts verified</span><strong>{status.case_count} forecast cases · {status.district_count} intersecting districts</strong><small>Readiness: {status.readiness_state.replaceAll("_", " ")}; not operational.</small></div> : <div className="method-status"><ErrorState message="Live case/district counts are unavailable; the pipeline and benchmark descriptions below are static and unaffected." /></div>}</div>
      <SectionHeading title="2019 reforecast pipeline" note="The displayed map cases and primary M2 correction belong to the 2017–2019 retrospective track" /><ol className="pipeline-list">{pipeline.map(([number, title, description], index) => <li key={number}><span className="pipeline-number">{number}</span><div><strong>{title}</strong><p>{description}</p></div>{index < pipeline.length - 1 ? <ArrowDown size={15} aria-hidden="true" /> : null}</li>)}</ol>
      <SectionHeading title="Track A · 2019 retrospective benchmark" note="NOAA GEFSv12 reforecast + IMD · completed held-out evaluation; no 2019-derived model selection" /><div className="split-grid"><div><span>2017</span><strong>TRAIN</strong><p>Fit deterministic, forecast-only pseudo-regime and probability models.</p></div><div><span>2018</span><strong>VALIDATE / CALIBRATE</strong><p>Freeze model choice, probability calibration and decision thresholds.</p></div><div><span>2019</span><strong>FINAL TEST COMPLETED</strong><p>Historical reforecast evaluation; no retuning afterward.</p></div></div>
      <SectionHeading title="Track B · 2025 operational-era benchmark" note="Historical NOAA operational GEFS + IMD · separate experiment, not pooled with the 2019 maps" /><div className="split-grid"><div><span>2023</span><strong>TRAIN / CROSS-FIT</strong><p>Fit operational-era models and forecast-only pseudo-regime classifier.</p></div><div><span>2024</span><strong>VALIDATE / CALIBRATE</strong><p>Select M1 Ridge and freeze probability calibration and thresholds.</p></div><div><span>2025</span><strong>FINAL TEST COMPLETED</strong><p>One-time historical holdout consumed; no post-test reselection.</p></div></div>
      <div className="method-grid"><section><Database size={19} /><h3>Data and provenance</h3><p>The interactive cases use NOAA GEFSv12 reforecast fields and IMD gridded rainfall on a 49×49, 0.25° target grid. The separate 2025 study uses historical operational GEFS. District geometry is the documented geoBoundaries IND ADM2 2021 source for the 2019 prototype.</p></section><section><FlaskConical size={19} /><h3>What the evidence says</h3><p>In 2019, Global XGBoost had the lowest deterministic RMSE. In the separate 2025 final test, preselected Ridge improved RMSE versus Raw, while Raw retained stronger heavy and very-heavy spatial FSS. Forecast-only pseudo-regime routing did not beat Global ML overall.</p></section><section><BookOpen size={19} /><h3>Limits of readiness</h3><p>This is a historical scientific prototype, not live forecasting. Regime classes are forecast-only pseudo-labels, not independently observed weather truth. Very-heavy probability false alarms and sparse high-probability bins limit the 2025 claim. District outputs cover the validated 2019 domain only.</p></section></div>
      {status ? <div className="provenance-band"><div><span>Corpus</span><strong>{status.provenance.corpus_version}</strong></div><div><span>Deterministic model</span><strong>{status.provenance.deterministic_model}</strong></div><div><span>Artifact manifest SHA-256</span><code>{status.provenance.artifact_manifest_sha256}</code></div></div> : null}
    </div>;
}
