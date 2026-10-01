"""static_geography_v1 (Stage 0): hash chain of the three frozen protocols, artifact integrity and independent recomputation of the zones."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PHASE6 = ROOT / "backend/app/evidence_data/phase6"
PHASE7 = ROOT / "backend/app/evidence_data/phase7"
ARTIFACT_FILE = PHASE7 / "static_geography_v1.json"
ART = json.loads(ARTIFACT_FILE.read_text(encoding="utf-8"))
V1, V2, V3 = (json.loads((PHASE6 / f"coastal_orographic_protocol_v{n}.json").read_text(encoding="utf-8")) for n in (1, 2, 3))
V1_SHA = "76dbf44eddee318cef5975a46b1f8046434f1a61e1e738d91fbc12909de80714"
V2_SHA = "650e5c75d1d07b286a08c27d32596d189cdae7ae04e03398f5ac05e65fae8204"
V3_SHA = "a9ff78173ddb6026e6b297c2da2128dde2fdcf825ae8b0c368c5f5fa79d199fd"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _grid(key: str) -> np.ndarray:
    return np.array([[np.nan if v is None else v for v in row] for row in ART["fields"][key]], float)


def test_protocol_versions_form_an_unbroken_hash_chain_and_earlier_versions_are_untouched():
    assert _sha(PHASE6 / "coastal_orographic_protocol_v1.json") == V1_SHA
    assert _sha(PHASE6 / "coastal_orographic_protocol_v2.json") == V2_SHA
    assert _sha(PHASE6 / "coastal_orographic_protocol_v3.json") == V3_SHA
    assert V2["supersedes"]["sha256"] == V1_SHA and V3["supersedes"]["sha256"] == V2_SHA
    for n, sha in ((2, V2_SHA), (3, V3_SHA)):
        assert (PHASE6 / f"coastal_orographic_protocol_v{n}.sha256").read_text(encoding="utf-8").split()[0] == sha
    assert V3["zones"]["labels"]["OROGRAPHIC"] == {"local_relief_m_min": 300.0}
    assert V3["zones"]["labels"]["COASTAL"] == {"distance_to_coast_km_max": 100.0}
    assert "land_mask_rule" in V3["static_geography"] and V3["stages"]["3"]["authorised"] is False


def test_artifact_bytes_match_sidecar_and_cite_the_pinned_protocol_and_source():
    digest = _sha(ARTIFACT_FILE)
    assert (PHASE7 / "static_geography_v1.sha256").read_text(encoding="utf-8").split()[0] == digest
    assert b"\r\n" not in ARTIFACT_FILE.read_bytes()
    assert ART["protocol"]["sha256"] == V3_SHA
    src = ART["source"]
    assert src["size_bytes"] == 249_216_253 and src["md5"] == "5b6c47502ae8d03b8718349655d5cd95" and len(src["sha256"]) == 64
    assert "CC BY 4.0" in src["distribution"] and src["attribution"]


def test_footprint_and_qa_criteria_hold():
    foot = np.array(ART["fields"]["footprint"])
    assert foot.shape == (49, 49) and int(foot.sum()) == 1301
    qa = ART["qa"]
    assert qa["criteria_met"] is True and qa["footprint_cells"] == 1301
    assert qa["footprint_terrain_land_majority_share"] >= 0.90 and qa["terrain_land_cells_outside_footprint"] <= 5
    assert qa["all_footprint_cells_have_finite_distance_to_coast"] is True
    assert qa["footprint_cells_without_a_land_pixel_elevation_undefined"] == int(np.isnan(np.where(foot, _grid("mean_elevation_m"), 0.0)).sum())
    assert np.isfinite(np.where(foot, _grid("distance_to_coast_km"), 0.0)).all()
    assert (np.where(foot, _grid("distance_to_coast_km"), 99.0) > 0).all()


def test_zones_equal_an_independent_recomputation_from_the_stored_fields():
    foot = np.array(ART["fields"]["footprint"])
    dist, relief = _grid("distance_to_coast_km"), _grid("local_relief_m")
    coastal = foot & (dist <= 100.0)
    oro = foot & (relief >= 300.0)          # NaN compares False, so an undefined relief never satisfies the test
    expected = np.full(foot.shape, None, dtype=object)
    expected[foot] = "OTHER"
    expected[coastal & ~oro] = "COASTAL"
    expected[oro & ~coastal] = "OROGRAPHIC"
    expected[coastal & oro] = "COASTAL_AND_OROGRAPHIC"
    assert expected.tolist() == ART["fields"]["zone"]
    counts = ART["zone_cell_counts"]
    assert sum(counts.values()) == 1301 and all(v >= 20 for v in counts.values())
    assert counts == {k: int((expected == k).sum()) for k in ("COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER")}
    assert ART["sensitivity_only_counts"]["coastal_cells_by_km"]["100"] == int(coastal.sum())
    assert ART["sensitivity_only_counts"]["orographic_cells_by_relief_m"]["300"] == int(oro.sum())


def test_fields_are_physically_sane_and_contain_no_rainfall_or_target_content():
    foot = np.array(ART["fields"]["footprint"])
    elev, slope = _grid("mean_elevation_m"), _grid("slope_m_per_km")
    assert np.nanmax(np.where(foot, elev, np.nan)) < 3000 and np.nanmin(np.where(foot, elev, np.nan)) >= 0
    assert (np.nan_to_num(slope) >= 0).all()
    for east, north in (("terrain_uphill_east", "terrain_uphill_north"), ("coast_landward_east", "coast_landward_north")):
        norm = np.hypot(np.nan_to_num(_grid(east)), np.nan_to_num(_grid(north)))
        assert ((np.abs(norm - 1) < 1e-2) | (norm == 0)).all()
    words = {word for name in ART["fields"] for word in name.split("_")}
    assert not words & {"rain", "rainfall", "precip", "imd", "target", "observation"}
    assert ART["grid"]["row_order"] == "south_to_north"


def test_known_geography_is_in_the_right_zone():
    lat, lon = ART["grid"]["latitude_centers"], ART["grid"]["longitude_centers"]
    zone = ART["fields"]["zone"]

    def at(la, lo):
        return zone[min(range(len(lat)), key=lambda i: abs(lat[i] - la))][min(range(len(lon)), key=lambda j: abs(lon[j] - lo))]

    assert at(19.0, 72.75) in ("COASTAL", "COASTAL_AND_OROGRAPHIC")      # Mumbai coast
    assert at(17.5, 77.5) == "OTHER"                                       # interior Deccan plateau (Hyderabad area)
    assert at(11.25, 76.5) == "COASTAL_AND_OROGRAPHIC" or at(11.25, 76.5) == "OROGRAPHIC"   # Nilgiris
