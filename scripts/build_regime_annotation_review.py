"""Validate a completed blinded regime review; never create labels or scores.

The input forms and source ledger are supplied by authorized human reviewers.
This command emits a local JSON audit only after all 72 cases are reviewed and
all disagreements are adjudicated. It does not read rainfall or model outputs.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.regime_annotation_review import (  # noqa: E402
    validate_adjudications,
    validate_reviews,
    validate_source_ledger,
    verify_frozen_material,
    verify_packet,
)


def _csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=ROOT / "data/manifests/research_pilot/expert_regime_review_packet_v1.json")
    parser.add_argument("--map-root", type=Path, help="Optional existing local packet directory; hashes all maps")
    parser.add_argument("--source-ledger", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True, help="Existing local source files; every source SHA-256 is checked")
    parser.add_argument("--roster", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New local audit JSON path")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; review audits are write-once")
    packet = verify_packet(args.packet, map_root=args.map_root)
    sources = validate_source_ledger(json.loads(args.source_ledger.read_text(encoding="utf-8"))["sources"],
                                     source_root=args.source_root)
    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    verify_frozen_material(roster, rubric_path=ROOT / "docs/147_INDEPENDENT_REGIME_REVIEW_PROTOCOL.md",
                           analysis_path=ROOT / "backend/app/ml/regime_annotation_review.py")
    reviews = _csv(args.reviews)
    adjudications = _csv(args.adjudications)
    review_summary = validate_reviews(packet, reviews, roster, sources)
    adjudication_summary = validate_adjudications(packet, reviews, adjudications, roster, sources)
    result = {"schema": "regime-annotation-audit-v1", "review": review_summary,
              "adjudication": adjudication_summary,
              "warning": "Construct review only; no independent rainfall skill or model score"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
