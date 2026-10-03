"""Experimental live-cycle worker (docs/139): selection and range rules, refusal of broken inputs, the immutable bundle, and the replay gate against the frozen 2025 artifacts.

The replay and broken-input tests need the local acquisition tree and frozen artifacts (gitignored) and are skipped, not passed, when it is absent.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from backend.app.live import bundle, pipeline

LOCAL = pytest.mark.skipif(not (Path(__file__).resolve().parents[2] / "experiments/recent_historical/phase4j_operational_final_test_v1/predictions/M1.npy").exists(), reason="local frozen artifacts not present")


def test_the_required_message_set_is_the_corpus_set_for_the_control_member():
    required = pipeline.required_messages()
    assert len(required) == 34 and sum(1 for f, _, v in required if v == "rain") == 16 and sum(1 for _, _, v in required if v != "rain") == 18
    assert pipeline.RAIN_HOURS == (3, 6, 12, 18, 24, 27, 30, 36, 42, 48, 51, 54, 60, 66, 72, 75)
    assert {pipeline.rain_interval(h) for h in (3, 6, 12, 27, 30, 51, 54, 75)} == {(0, 3), (0, 6), (6, 12), (24, 27), (24, 30), (48, 51), (48, 54), (72, 75)}
    assert pipeline.object_key("20250926", "pgrb2sp25", 3) == "gefs.20250926/00/atmos/pgrb2sp25/gec00.t00z.pgrb2s.0p25.f003"
    assert pipeline.object_key("20250926", "pgrb2bp5", 72) == "gefs.20250926/00/atmos/pgrb2bp5/gec00.t00z.pgrb2b.0p50.f072"


INDEX = "\n".join([
    "1:0:d=2025092600:PRES:mean sea level:24 hour fcst:ENS=low-res ctl",
    "2:1000:d=2025092600:APCP:surface:0-3 hour acc fcst:ENS=low-res ctl",
    "3:2500:d=2025092600:APCP:surface:0-3 hour acc fcst:ENS=+1",
    "4:4200:d=2025092600:UGRD:850 mb:24 hour fcst:ENS=low-res ctl",
    "5:9000:d=2025092600:UGRD:850 mb:24 hour fcst:ENS=+1",
])


def test_selection_takes_the_one_control_line_and_derives_the_byte_range_from_the_next_line():
    lines = pipeline.parse_index(INDEX)
    assert pipeline.select_entry(lines, "pgrb2sp25", 3, "rain")[:2] == (1000, 2499)
    assert pipeline.select_entry(lines, "pgrb2ap5", 24, "u850")[:2] == (4200, 8999)
    with pytest.raises(pipeline.CycleRefused):
        pipeline.select_entry(lines, "pgrb2ap5", 24, "v850")                       # absent
    with pytest.raises(pipeline.CycleRefused):
        pipeline.select_entry(lines, "pgrb2ap5", 24, "z500")
    ambiguous = pipeline.parse_index(INDEX + "\n6:9500:d=2025092600:UGRD:850 mb:24 hour fcst:ENS=low-res ctl\n7:9900:x:y:z")
    with pytest.raises(pipeline.CycleRefused):
        pipeline.select_entry(ambiguous, "pgrb2ap5", 24, "u850")                   # two control lines
    with pytest.raises(pipeline.CycleRefused):
        pipeline.parse_index("not an index")
    last = pipeline.parse_index("1:0:d=2025092600:APCP:surface:0-3 hour acc fcst:ENS=low-res ctl")
    with pytest.raises(pipeline.CycleRefused):
        pipeline.select_entry(last, "pgrb2sp25", 3, "rain")                        # the last line has no determinable end byte


class FakeHttp(pipeline.HttpSource):
    def __init__(self, date, responses):
        super().__init__(date)
        self.responses = responses

    def _request(self, path, headers=None):
        return self.responses(path, headers or {})


def test_range_requests_are_checked_for_status_content_range_and_length():
    key = pipeline.object_key("20250926", "pgrb2sp25", 3)
    index = pipeline.parse_index(INDEX)

    def make(status, content_range, body):
        def respond(path, headers):
            if path.endswith(".idx"):
                return 200, {}, INDEX.encode("ascii")
            assert headers == {"Range": "bytes=1000-2499"}
            return status, {"Content-Range": content_range} if content_range else {}, body
        return FakeHttp("20250926", respond)
    good = make(206, "bytes 1000-2499/9999", b"x" * 1500).get("pgrb2sp25", 3, "rain")
    assert good.length == 1500 and good.sha256 == hashlib.sha256(b"x" * 1500).hexdigest() and good.key == key and index
    for source in (make(200, None, b"x" * 1500), make(206, "bytes 0-1499/9999", b"x" * 1500), make(206, "bytes 1000-2499/9999", b"x" * 10)):
        with pytest.raises(pipeline.CycleRefused):
            source.get("pgrb2sp25", 3, "rain")
    missing = FakeHttp("20250926", lambda path, headers: (404, {}, b""))
    with pytest.raises(pipeline.CycleRefused):
        missing.index("pgrb2sp25", 3)
    with pytest.raises(ValueError):
        pipeline.HttpSource("2025-09-26")


def test_plan_reports_ranges_and_bytes_without_fetching_any_body():
    calls = []

    def respond(path, headers):
        calls.append((path, headers))
        assert path.endswith(".idx") and not headers                      # only index files, never a ranged body
        family = path.split("/")[3]
        hour = int(path.split(".f")[1][:3])
        lines = []
        if family == "pgrb2sp25":
            start = pipeline.rain_interval(hour)
            lines += [f"1:0:d=2025092600:APCP:surface:{start[0]}-{start[1]} hour acc fcst:ENS=low-res ctl", "2:500:d=2025092600:END:x:y:z"]
        else:
            for name, (fam, parameter, level) in pipeline.ATMOSPHERE.items():
                if fam == family:
                    lines.append(f"{len(lines) + 1}:{len(lines) * 700}:d=2025092600:{parameter}:{level}:{hour} hour fcst:ENS=low-res ctl")
            lines.append(f"{len(lines) + 1}:{len(lines) * 700}:d=2025092600:END:x:y:z")
        return 200, {}, "\n".join(lines).encode("ascii")
    rows = FakeHttp("20250926", respond).plan()
    assert len(rows) == 34 and sum(r["bytes"] for r in rows) > 0 and all(r["bytes"] > 0 for r in rows)


def _synthetic_arrays():
    rng = np.random.default_rng(3)
    arrays = {}
    for name in ("M0", "M1", "M2", "M3", "M4"):
        arrays[f"{name}_day1_24h"] = rng.gamma(1.0, 3.0, (49, 49)).astype(np.float32)
    for name in ("heavy_probability", "very_heavy_probability"):
        arrays[f"{name}_day1_24h"] = rng.uniform(0, 0.2, (49, 49))
    arrays["regime_probability_day1_24h"] = np.array([0.2, 0.3, 0.5])
    return arrays


def _write(root, kind="replay", date="20250926", arrays=None):
    return bundle.write_bundle(root, kind, date, arrays or _synthetic_arrays(), ["day1_24h"], {"sources": [{"bytes": 10}], "withheld_products": {}, "frozen_models": {"M1": "a" * 64}})


def test_a_bundle_is_written_once_and_verifies(tmp_path):
    directory = _write(tmp_path)
    manifest = bundle.verify_bundle(directory)
    assert manifest["observation_read"] is False and manifest["retrained_or_recalibrated"] is False and manifest["label"] == bundle.LABELS["replay"] and "not a forecast" in manifest["label"]
    assert (directory / "manifest.sha256").read_text(encoding="ascii").split()[0] == hashlib.sha256((directory / "manifest.json").read_bytes()).hexdigest()
    with pytest.raises(bundle.BundleError):
        _write(tmp_path)                                                  # immutable
    assert "no verification yet" in bundle.LABELS["live"] and "not an official warning" in bundle.LABELS["live"]
    assert bundle.list_bundles(tmp_path) == [("replay", "20250926")]


def test_non_finite_or_wrongly_typed_arrays_are_never_written(tmp_path):
    bad = _synthetic_arrays()
    bad["M1_day1_24h"][0, 0] = np.nan
    with pytest.raises(bundle.BundleError):
        _write(tmp_path, arrays=bad)
    ints = _synthetic_arrays()
    ints["M1_day1_24h"] = ints["M1_day1_24h"].astype(np.int32)
    with pytest.raises(bundle.BundleError):
        _write(tmp_path, date="20250927", arrays=ints)


@pytest.mark.parametrize("victim", ["array", "manifest", "sidecar", "flag", "kind-directory"])
def test_every_kind_of_tampering_is_caught(tmp_path, victim):
    directory = _write(tmp_path)
    if victim == "array":
        array = np.load(directory / "M1_day1_24h.npy")
        array[3, 3] += 1.0
        np.save(directory / "M1_day1_24h.npy", array)
    elif victim == "manifest":
        (directory / "manifest.json").write_text((directory / "manifest.json").read_text(encoding="utf-8").replace("replay", "replaz", 1), encoding="utf-8")
    elif victim == "sidecar":
        (directory / "manifest.sha256").write_text("0" * 64 + "\n", encoding="ascii")
    elif victim == "flag":
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        manifest["observation_read"] = True
        text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        (directory / "manifest.json").write_text(text, encoding="utf-8")
        (directory / "manifest.sha256").write_text(hashlib.sha256(text.encode("utf-8")).hexdigest() + "\n", encoding="ascii")
    else:
        (tmp_path / "live").mkdir()
        directory.rename(tmp_path / "live" / "20250926")
        directory = tmp_path / "live" / "20250926"
    with pytest.raises(bundle.BundleError):
        bundle.verify_bundle(directory)


def test_the_worker_has_no_access_path_to_observations_or_to_training():
    root = Path(__file__).resolve().parents[1] / "app/live"
    forbidden = ("imd_rainfall", "load_imd", "RF25", "rfp25", "netCDF4", ".fit(", "fit_m2", "fit_calibrator", "fit_logistic", "fit_classifier")
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} mentions {token}"
    script = (Path(__file__).resolve().parents[2] / "scripts/live/run_live_cycle.py").read_text(encoding="utf-8")
    assert "--confirm-download" in script and "refusing to download without" in script


@LOCAL
def test_replay_gate_reproduces_the_frozen_outputs_exactly_and_refuses_what_the_corpus_refused():
    from backend.app.live import replay
    if not replay.available():
        pytest.skip("local acquisition tree not present")
    models = pipeline.FrozenModels.load()
    full = replay.replay("20250926", models)
    assert set(full["products"]) == set(pipeline.PRODUCTS) and full["withheld_products"] == {}
    differences = [v for p in full["products"].values() for k, v in p.items() if k.endswith("difference")]
    assert len(differences) == 3 * 10 and max(differences) <= 1e-9 and all(p["paired_cells"] == 1301 for p in full["products"].values())
    partial = replay.replay("20250715", models)
    assert set(partial["products"]) == {"day3_24h"} and set(partial["withheld_products"]) == {"day1_24h", "day2_24h"}      # the corpus withheld the same two leads
    assert max(v for p in partial["products"].values() for k, v in p.items() if k.endswith("difference")) <= 1e-9


@LOCAL
@pytest.mark.parametrize("breakage", ["missing", "truncated", "wrong_cycle", "no_control_tag", "wrong_hash"])
def test_every_deliberately_broken_input_is_refused_and_nothing_is_decoded_past_it(breakage):
    from backend.app.live.stored import StoredSource
    inner = StoredSource("20250926")

    class Broken:
        def get(self, family, hour, variable):
            message = inner.get(family, hour, variable)
            if (family, hour, variable) != ("pgrb2ap5", 24, "u850"):
                return message
            if breakage == "missing":
                raise pipeline.CycleRefused("stored cycle lacks the message")
            if breakage == "truncated":
                payload = message.payload[:-200]
                return pipeline.Message(family, hour, variable, message.key, message.description, message.byte_start, message.byte_end, payload, hashlib.sha256(payload).hexdigest())
            if breakage == "no_control_tag":
                return pipeline.Message(family, hour, variable, message.key, message.description.replace("ENS=low-res ctl", "ENS=+1"), message.byte_start, message.byte_end, message.payload, message.sha256)
            if breakage == "wrong_hash":
                return pipeline.Message(family, hour, variable, message.key, message.description, message.byte_start, message.byte_end, message.payload, "0" * 64)
            return message

    date = "20250927" if breakage == "wrong_cycle" else "20250926"
    with pytest.raises(pipeline.CycleRefused):
        pipeline.decode_cycle(Broken(), date)
