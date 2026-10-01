"""Regenerate the PS-requirement table in docs/22 from the machine-readable coverage manifest (no hand-typed status).

    python scripts/build_ps_traceability_doc.py

The generated block sits between the GENERATED markers at the top of docs/22_REQUIREMENTS_TRACEABILITY.md; everything below the
block is the historical Phase 0-1 audit and is preserved. A backend test fails if the block drifts from the manifest.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "backend/app/evidence_data/phase6/ps_coverage.json"
DOC = ROOT / "docs/22_REQUIREMENTS_TRACEABILITY.md"
START, END = "<!-- GENERATED:PS-COVERAGE:START -->", "<!-- GENERATED:PS-COVERAGE:END -->"
OFFICIAL = {
    "PS-R01": "Ingest / use raw NWP rainfall", "PS-R02": "AI/ML post-processing", "PS-R03": "Weather-regime classification",
    "PS-R04": "Regime-conditioned correction", "PS-R05": "Demonstrate improvement vs raw NWP", "PS-R06": "Grid-level rainfall output",
    "PS-R07": "Heavy-rain exceedance probability", "PS-R08": "District-level rainfall table/map", "PS-R09": "RMSE", "PS-R10": "ETS",
    "PS-R11": "CSI", "PS-R12": "POD", "PS-R13": "FAR", "PS-R14": "FSS",
}


def aggregate(statuses: list[str]) -> str:
    """IMPLEMENTED if every mandatory row is IMPLEMENTED, PLANNED if every one is PLANNED, otherwise PARTIAL."""
    if all(s == "IMPLEMENTED" for s in statuses):
        return "IMPLEMENTED"
    if all(s == "PLANNED" for s in statuses):
        return "PLANNED"
    return "PARTIAL"


def ps_table(rows: list[dict]) -> list[tuple[str, str, str, list[str]]]:
    out = []
    for pid, label in OFFICIAL.items():
        covering = [r for r in rows if pid in r["ps_ids"] and r["ps_mandatory"]]
        out.append((pid, label, aggregate([r["status"] for r in covering]), [r["id"] for r in covering]))
    return out


def render(rows: list[dict]) -> str:
    lines = [START, "## Current status (generated from `backend/app/evidence_data/phase6/ps_coverage.json`)", "",
             "Status of each official requirement = IMPLEMENTED if every mandatory coverage row for it is IMPLEMENTED, PLANNED if every one is PLANNED, otherwise PARTIAL.",
             "Live view with evidence-resolved figures: the app's `/compliance` page. Do not edit this block by hand; run `python scripts/build_ps_traceability_doc.py`.", "",
             "| PS ID | Official requirement | Status | Coverage rows (mandatory) |", "|---|---|---|---|"]
    for pid, label, status, ids in ps_table(rows):
        lines.append(f"| {pid} | {label} | {status} | {', '.join(ids)} |")
    extras = [r for r in rows if not r["ps_mandatory"]]
    lines += ["", "Additional (non-mandatory) rows:", "", "| Row | Requirement | Status |", "|---|---|---|"]
    lines += [f"| {r['id']} | {r['requirement']} | {r['status']} |" for r in extras]
    lines += ["", END]
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))["rows"]
    block = render(rows)
    text = DOC.read_text(encoding="utf-8").replace("\r\n", "\n")
    if START in text:
        head, rest = text.split(START, 1)
        _, tail = rest.split(END, 1)
        new = head + block.rstrip("\n") + tail
    else:
        title, _, body = text.partition("\n")
        new = (f"{title}\n\n{block}\n## Historical audit (Phase 0-1, superseded by the table above)\n\n"
               "The table and evidence list below record the state at the Phase 0-1 audit (September 2026) and are kept for provenance only.\n"
               f"{body}")
    DOC.write_text(new, encoding="utf-8", newline="\n")
    print(f"wrote {DOC.relative_to(ROOT)} ({len(rows)} coverage rows)")


if __name__ == "__main__":
    main()
