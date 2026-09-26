import { PageHeading, PrototypeNote } from "@/components/science/common";
import { final2025, presentationManifest } from "@/science/frozen/results";

const limitations = [
  "Historical research prototype; not a live forecast system or an official warning service.",
  "Raw GEFS retained better selected-model extreme-rain FSS at the tested Heavy and Very Heavy neighborhood sizes.",
  "Very-heavy calibrated probability had a high false-alarm ratio on the 2025 final test.",
  "Regime classes are forecast-derived pseudo-regimes, not independently observed meteorological truth.",
  "Source-QC attrition reduced the operational rainfall-eligible population.",
  "IMD annual daily date labels do not explicitly encode accumulation bounds.",
  "2019 reforecast and 2025 operational-era benchmarks have different GEFS lineages and cannot be pooled.",
  "Six evaluated monsoon seasons do not support climatological trend inference.",
];

export default function AuditPage() {
  return <div className="page-content"><PageHeading title="Scientific Audit" subtitle="Internal independent reproducibility audit · historical prototype evidence" action={<PrototypeNote />} />
    <div className="phase5-context-strip"><strong>{final2025.status}</strong><span>2025 holdout consumed</span><span>Not third-party certification</span></div>
    <section className="phase5-analysis-block"><h2>One-time final-test governance</h2><div className="phase5-holdout-flow"><span>SEALED</span><span>AUTHORIZED</span><span>UNSEALED ONCE</span><strong>FINAL TEST COMPLETED</strong></div><p>2025 has been consumed and is no longer an untouched holdout. The preselected M1 Ridge comparison remains primary even though secondary M2 had lower final-test RMSE.</p></section>
    <section className="phase5-analysis-block"><h2>Frozen scientific claim boundary</h2><div className="phase5-metric-strip"><span><small>2025 primary population</small><strong>{final2025.case_count} cases</strong></span><span><small>Paired valid cells</small><strong>{final2025.cell_count.toLocaleString()}</strong></span><span><small>Primary decision</small><strong>{final2025.primary.classification.replaceAll("_", " ")}</strong></span></div><p className="phase5-caveat">The internal independent Phase 4K audit verified reproducibility and claims against frozen evidence. It is not an external certification of operational readiness.</p></section>
    <section className="phase5-analysis-block"><h2>Known limitations</h2><ul className="phase5-limitations">{limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
    <section className="phase5-analysis-block"><h2>Artifact lineage</h2><dl className="phase5-hash-list"><dt>Phase 4J final result</dt><dd><code>{presentationManifest.source_hashes.phase4j_final_test_result}</code></dd><dt>Phase 4K independent audit</dt><dd><code>{presentationManifest.source_hashes.phase4k_audit}</code></dd><dt>Phase 4L communication evidence</dt><dd><code>{presentationManifest.source_hashes.phase4l_communication}</code></dd><dt>Phase 5A presentation manifest</dt><dd><code>{/* The published manifest is fetched as an artifact, not invented in this component. */}Read-only export manifest in /science/operational-v1/</code></dd></dl></section>
  </div>;
}
