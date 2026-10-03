import { PageHeading, PrototypeNote } from "@/components/science/common";
import { LimitationsPanel } from "@/components/science/limitations-panel";
import { ProvenanceDag } from "@/components/audit/provenance-dag";
import { HoldoutGovernanceTimeline } from "@/components/audit/holdout-governance";
import { final2025, presentationManifest } from "@/science/frozen/results";

export default function AuditPage() {
  return <div className="page-content"><PageHeading title="Scientific Audit" subtitle="Internal Independent Reproducibility Audit · historical prototype evidence" action={<PrototypeNote />} />
    <div className="phase5-context-strip"><strong>{final2025.status}</strong><span>2025 holdout consumed</span><span>Not third-party certification</span></div>

    <section className="phase5-analysis-block"><h2>Holdout governance lifecycle</h2><HoldoutGovernanceTimeline /><p>The full Track-B (2023-2025) holdout chain: fit and select before the 2025 test was ever opened, then a single unsealing.</p></section>

    <section className="phase5-analysis-block"><h2>One-time final-test governance</h2><div className="phase5-holdout-flow"><span>SEALED</span><span>AUTHORIZED</span><span>UNSEALED ONCE</span><strong>FINAL TEST COMPLETED</strong></div><p>2025 has been consumed and is no longer an untouched holdout. The preselected M1 Ridge comparison remains primary even though secondary M2 had lower final-test RMSE.</p></section>

    <section className="phase5-analysis-block"><h2>Experiment lineage (Track B)</h2><p>Click a stage to see its input source, output artifact type, model family, scientific and integrity status, and documentation reference. No absolute local path is ever shown.</p><ProvenanceDag /></section>

    <section className="phase5-analysis-block"><h2>Frozen scientific claim boundary</h2><div className="phase5-metric-strip"><span><small>2025 primary population</small><strong>{final2025.case_count} cases</strong></span><span><small>Paired valid cells</small><strong>{final2025.cell_count.toLocaleString("en-GB")}</strong></span><span><small>Primary decision</small><strong>{final2025.primary.classification.replaceAll("_", " ")}</strong></span></div><p className="phase5-caveat">The internal independent Phase 4K audit verified reproducibility and claims against frozen evidence. It is not an external certification of operational readiness -- no certification seal is claimed anywhere in this product.</p></section>

    <section className="phase5-analysis-block"><h2>Known limitations</h2><LimitationsPanel /></section>

    <section className="phase5-analysis-block"><h2>Protected-artifact integrity</h2><dl className="phase5-hash-list"><dt>Phase 4J final result</dt><dd><code>{presentationManifest.source_hashes.phase4j_final_test_result}</code></dd><dt>Phase 4K independent audit</dt><dd><code>{presentationManifest.source_hashes.phase4k_audit}</code></dd><dt>Phase 4L communication evidence</dt><dd><code>{presentationManifest.source_hashes.phase4l_communication}</code></dd><dt>Phase 5A presentation manifest</dt><dd>Read-only export manifest, fetched as a published artifact, not invented in this component: <code>/science/operational-v1/</code></dd></dl></section>
  </div>;
}
