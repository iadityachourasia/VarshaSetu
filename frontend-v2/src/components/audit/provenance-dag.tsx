"use client";

import { useMemo, useState } from "react";
import { PROVENANCE_NODES, type ProvenanceNode } from "@/lib/provenance-dag";

/** Track-B model/data lineage graph. Rows are pipeline depth; two nodes
 * sharing a row (M1/M2, then M3/M4) render side by side, visually showing
 * the fork after Rainfall/Atmosphere Features and the second fork/merge
 * around the regime classifier -- without drawing literal connector lines
 * (kept deliberately simple/robust rather than a fragile pixel-positioned
 * SVG graph). Clicking a node shows its full lineage detail; no absolute
 * local path is ever shown (lib/provenance-dag.ts never records one). */
export function ProvenanceDag() {
  const [selectedId, setSelectedId] = useState(PROVENANCE_NODES[0].id);
  const rows = useMemo(() => {
    const byRow = new Map<number, ProvenanceNode[]>();
    for (const node of PROVENANCE_NODES) byRow.set(node.row, [...(byRow.get(node.row) ?? []), node]);
    return [...byRow.entries()].sort(([a], [b]) => a - b);
  }, []);
  const selected = PROVENANCE_NODES.find((node) => node.id === selectedId) ?? PROVENANCE_NODES[0];
  const parents = selected.dependsOn.map((id) => PROVENANCE_NODES.find((node) => node.id === id)?.label).filter(Boolean);

  return <div className="phase5-provenance-dag">
    <div className="phase5-provenance-rows" role="group" aria-label="Track-B model and data lineage">
      {rows.map(([row, nodes]) => <div className="phase5-provenance-row" key={row}>{nodes.map((node) => <button
        key={node.id} type="button" aria-pressed={node.id === selectedId} onClick={() => setSelectedId(node.id)}
      >{node.label}</button>)}</div>)}
    </div>
    <aside aria-live="polite">
      <span className="small-label">{selected.stage}</span>
      <h3>{selected.label}</h3>
      {parents.length ? <p className="micro-note">Depends on: {parents.join(", ")}</p> : <p className="micro-note">Pipeline entry point.</p>}
      <dl className="phase5-hash-list">
        <dt>Input source</dt><dd>{selected.inputSource}</dd>
        <dt>Output artifact type</dt><dd>{selected.outputArtifactType}</dd>
        {selected.yearRole ? <><dt>Year role</dt><dd>{selected.yearRole}</dd></> : null}
        {selected.featureCount ? <><dt>Feature count</dt><dd>{selected.featureCount}</dd></> : null}
        {selected.modelFamily ? <><dt>Model family</dt><dd>{selected.modelFamily}</dd></> : null}
        <dt>Scientific status</dt><dd>{selected.scientificStatus}</dd>
        <dt>Integrity status</dt><dd>{selected.integrityStatus}</dd>
        <dt>Documentation</dt><dd><code>{selected.docReference}</code></dd>
      </dl>
    </aside>
  </div>;
}
