"""Single-cycle inference pipeline for the experimental live view (docs/139, design docs/125).

One GEFS 00 UTC cycle, control member only: fetch the 34 selected messages, decode and apply the canonical rainfall quality control, build the frozen 22 features and the forecast-only regime
features, apply the **frozen** Track B models without retraining, and return arrays plus provenance. It reads no observation, never retrains or recalibrates, fails closed on any quality gate and
makes no skill claim. The message source is pluggable: ``HttpSource`` reads NOAA, ``stored.StoredSource`` replays an already-acquired historical cycle through exactly the same code, which is the
scientific gate for the whole path (the replay must reproduce the frozen outputs, see docs/139).

Heavy dependencies (GRIB decoding, model libraries, the frozen experiment tree) are imported lazily so that importing this module never changes the web API image.
"""

from __future__ import annotations

import hashlib
import http.client
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

import numpy as np

NOAA_HOST = "noaa-gefs-pds.s3.amazonaws.com"
PRODUCTS = ("day1_24h", "day2_24h", "day3_24h")
LEADS = {
    "day1_24h": {"window": (3, 27), "rain_hours": (3, 6, 12, 18, 24, 27), "atmosphere_hour": 24},
    "day2_24h": {"window": (27, 51), "rain_hours": (27, 30, 36, 42, 48, 51), "atmosphere_hour": 48},
    "day3_24h": {"window": (51, 75), "rain_hours": (51, 54, 60, 66, 72, 75), "atmosphere_hour": 72},
}
RAIN_HOURS = tuple(sorted({h for lead in LEADS.values() for h in lead["rain_hours"]}))
ATMOSPHERE_HOURS = tuple(lead["atmosphere_hour"] for lead in LEADS.values())
ATMOSPHERE = {
    "u850": ("pgrb2ap5", "UGRD", "850 mb"), "v850": ("pgrb2ap5", "VGRD", "850 mb"), "q700": ("pgrb2bp5", "SPFH", "700 mb"),
    "z500": ("pgrb2ap5", "HGT", "500 mb"), "mslp": ("pgrb2bp5", "PRES", "mean sea level"),
    "pwat": ("pgrb2ap5", "PWAT", "entire atmosphere (considered as a single layer)"),
}
FAMILY_FILE = {"pgrb2sp25": "pgrb2s.0p25", "pgrb2ap5": "pgrb2a.0p50", "pgrb2bp5": "pgrb2b.0p50"}
EXPECTED_UNITS = {"u850": ("m s**-1", "m/s"), "v850": ("m s**-1", "m/s"), "q700": ("kg kg**-1", "kg/kg"), "z500": ("gpm", "m"), "mslp": ("Pa",), "pwat": ("kg m**-2", "kg m-2")}
TARGET_LAT, TARGET_LON = np.linspace(10, 22, 49), np.linspace(68, 80, 49)
CONTEXT_LAT, CONTEXT_LON = np.linspace(5, 30, 51), np.linspace(55, 95, 81)
CONTROL_TAG = "ENS=low-res ctl"
STATIC_FEATURES = ("latitude_deg", "longitude_deg", "lead_hours")          # grid coordinates and the lead are fixed by construction, not forecast values
RESEARCH_LABEL = "EXPERIMENTAL FORECAST: frozen models, no verification yet, not an official warning"


class CycleRefused(RuntimeError):
    """A quality gate failed. Nothing is published for the cycle."""


@dataclass(frozen=True)
class Message:
    family: str
    hour: int
    variable: str            # "rain" or an ATMOSPHERE name
    key: str                 # NOAA object key
    description: str         # the index line
    byte_start: int
    byte_end: int
    payload: bytes
    sha256: str

    @property
    def length(self) -> int:
        return self.byte_end - self.byte_start + 1


class MessageSource(Protocol):
    def get(self, family: str, hour: int, variable: str) -> Message: ...


def object_key(date: str, family: str, hour: int) -> str:
    return f"gefs.{date}/00/atmos/{family}/gec00.t00z.{FAMILY_FILE[family]}.f{hour:03d}"


def rain_interval(hour: int) -> tuple[int, int]:
    """The interval of the APCP message selected for a forecast hour (the corpus rule: 3-hourly to 6, then 6-hourly sums with the 3-hour edges)."""
    return (hour - 3 if hour % 6 == 3 else hour - 6), hour


def required_messages() -> list[tuple[str, int, str]]:
    out = [("pgrb2sp25", hour, "rain") for hour in RAIN_HOURS]
    out += [(ATMOSPHERE[name][0], hour, name) for hour in ATMOSPHERE_HOURS for name in ATMOSPHERE]
    return out


def select_entry(lines: list[tuple[int, int, str]], family: str, hour: int, variable: str) -> tuple[int, int, str]:
    """Pick the one control-member index line for a message. ``lines`` are (number, byte_start, text) in file order; the end byte is the next line's start minus one."""
    if variable == "rain":
        start, end = rain_interval(hour)
        marker = f":APCP:surface:{start}-{end} hour acc fcst:{CONTROL_TAG}"
    else:
        _, parameter, level = ATMOSPHERE[variable]
        marker = f":{parameter}:{level}:{hour} hour fcst:{CONTROL_TAG}"
    matches = [i for i, (_, _, text) in enumerate(lines) if text.endswith(marker) or marker in text]
    if len(matches) != 1:
        raise CycleRefused(f"expected one index line for {family} {variable} f{hour:03d}; found {len(matches)}")
    i = matches[0]
    if i + 1 >= len(lines):
        raise CycleRefused(f"{family} {variable} f{hour:03d} is the last index line; its byte range is not determinable from the index")
    number, start, text = lines[i]
    return start, lines[i + 1][1] - 1, text


def parse_index(text: str) -> list[tuple[int, int, str]]:
    rows = []
    for row in (r for r in text.splitlines() if r.strip()):
        parts = row.split(":", 2)
        if len(parts) != 3 or not parts[0].isdigit() or not parts[1].isdigit():
            raise CycleRefused(f"unrecognized GEFS index row: {row[:80]}")
        rows.append((int(parts[0]), int(parts[1]), row))
    return rows


class HttpSource:
    """NOAA GEFS public bucket, byte ranges only. ``plan()`` reads the small index files and reports exactly what a run would transfer."""

    def __init__(self, date: str, *, timeout: int = 60):
        if not re.fullmatch(r"\d{8}", date):
            raise ValueError("date must be YYYYMMDD")
        self.date, self.timeout = date, timeout
        self._index: dict[tuple[str, int], list[tuple[int, int, str]]] = {}
        self._conn: http.client.HTTPSConnection | None = None

    def _request(self, path: str, headers: dict | None = None) -> tuple[int, dict, bytes]:
        for attempt in range(3):
            try:
                if self._conn is None:
                    self._conn = http.client.HTTPSConnection(NOAA_HOST, timeout=self.timeout)
                self._conn.request("GET", "/" + path, headers=headers or {})
                response = self._conn.getresponse()
                return response.status, dict(response.getheaders()), response.read()
            except (OSError, http.client.HTTPException):
                self._conn = None
                if attempt == 2:
                    raise
        raise AssertionError("unreachable")

    def index(self, family: str, hour: int) -> list[tuple[int, int, str]]:
        if (family, hour) not in self._index:
            status, _, body = self._request(object_key(self.date, family, hour) + ".idx")
            if status != 200:
                raise CycleRefused(f"index not available (HTTP {status}): {object_key(self.date, family, hour)}.idx")
            self._index[(family, hour)] = parse_index(body.decode("ascii"))
        return self._index[(family, hour)]

    def plan(self) -> list[dict]:
        rows = []
        for family, hour, variable in required_messages():
            start, end, text = select_entry(self.index(family, hour), family, hour, variable)
            rows.append({"family": family, "hour": hour, "variable": variable, "key": object_key(self.date, family, hour), "byte_start": start, "byte_end": end, "bytes": end - start + 1, "index_line": text})
        return rows

    def get(self, family: str, hour: int, variable: str) -> Message:
        start, end, text = select_entry(self.index(family, hour), family, hour, variable)
        key = object_key(self.date, family, hour)
        status, headers, body = self._request(key, {"Range": f"bytes={start}-{end}"})
        content_range = {k.lower(): v for k, v in headers.items()}.get("content-range", "")
        if status != 206 or not content_range.startswith(f"bytes {start}-{end}/") or len(body) != end - start + 1:
            raise CycleRefused(f"range request refused or short for {key}: HTTP {status}, {len(body)} bytes")
        return Message(family, hour, variable, key, text, start, end, body, hashlib.sha256(body).hexdigest())


def _grib_extra(payload: bytes) -> dict:
    from eccodes import codes_get, codes_new_from_message, codes_release
    handle = codes_new_from_message(payload)
    try:
        out = {}
        for key in ("edition", "totalLength", "gridDefinitionTemplateNumber", "typeOfStatisticalProcessing", "indicatorOfUnitForTimeRange", "lengthOfTimeRange"):
            try:
                value = codes_get(handle, key)
                out[key] = value.item() if hasattr(value, "item") else value
            except Exception:
                out[key] = None
        return out
    finally:
        codes_release(handle)


def validate_message(message: Message, date: str, metadata: dict, extra: dict) -> None:
    """Fail closed on decoded identity, timing, units and the native grid (the corpus checks, with the index line instead of a manifest row)."""
    hour = message.hour
    if extra["edition"] != 2 or extra["totalLength"] != message.length:
        raise CycleRefused(f"{message.variable} f{hour:03d}: GRIB edition or self-reported length differs from the index range")
    if metadata["forecast_init"] != f"{date}T0000Z":
        raise CycleRefused(f"{message.variable} f{hour:03d}: decoded initialization differs from the requested cycle")
    valid = datetime.strptime(date, "%Y%m%d") + timedelta(hours=hour)
    if (metadata["valid_date"], metadata["valid_time"]) != (int(valid.strftime("%Y%m%d")), int(valid.strftime("%H%M"))):
        raise CycleRefused(f"{message.variable} f{hour:03d}: decoded valid time differs from the forecast hour")
    if metadata["requested_member"] != "c00":
        raise CycleRefused(f"{message.variable} f{hour:03d}: decoded member is not the control")
    grid = metadata["grid"]
    shape, spacing = ((1440, 721), 0.25) if message.family == "pgrb2sp25" else ((720, 361), 0.5)
    if (grid["ni"], grid["nj"]) != shape or grid["grid_type"] != "regular_ll" or extra["gridDefinitionTemplateNumber"] != 0:
        raise CycleRefused(f"{message.variable} f{hour:03d}: unexpected native grid")
    if not (np.isclose(grid["latitude_first"], -90.0) and np.isclose(grid["latitude_last"], 90.0) and np.isclose(grid["longitude_first"], 0.0) and np.isclose(grid["longitude_last"], 360.0 - spacing)):
        raise CycleRefused(f"{message.variable} f{hour:03d}: unexpected native grid coordinates")
    if message.variable == "rain":
        start, end = rain_interval(hour)
        if metadata["short_name"] != "tp" or metadata["units"] not in ("kg m**-2", "kg m-2"):
            raise CycleRefused(f"rain f{hour:03d}: parameter or units mismatch")
        if (metadata["start_step"], metadata["end_step"]) != (start, end) or metadata["end_step"] != hour or metadata["step_type"] != "accum":
            raise CycleRefused(f"rain f{hour:03d}: accumulation interval differs from the index")
        if extra["typeOfStatisticalProcessing"] != 1 or extra["indicatorOfUnitForTimeRange"] != 1 or extra["lengthOfTimeRange"] != end - start:
            raise CycleRefused(f"rain f{hour:03d}: accumulation time-range semantics mismatch")
    else:
        if metadata["units"] not in EXPECTED_UNITS[message.variable]:
            raise CycleRefused(f"{message.variable} f{hour:03d}: units mismatch ({metadata['units']})")
        if metadata["forecast_step"] != hour or metadata["step_type"] != "instant":
            raise CycleRefused(f"{message.variable} f{hour:03d}: forecast timing mismatch")


def decode_cycle(source: MessageSource, date: str) -> dict:
    """Decode every selected message once and apply the canonical rainfall reconstruction. Returns rainfall (49x49 per product), atmosphere (51x81 per hour and name) and provenance."""
    from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_minimal_accumulation_window
    from backend.app.data_sources.noaa_gefs_monthly import ATMOSPHERIC_SPECS, crop_grid, decode_atmospheric_message, decode_precipitation_message

    sources, rain_messages, atmosphere = [], {}, {}
    for family, hour, variable in required_messages():
        message = source.get(family, hour, variable)
        if message.sha256 != hashlib.sha256(message.payload).hexdigest() or CONTROL_TAG not in message.description:
            raise CycleRefused(f"{variable} f{hour:03d}: payload hash or control-member tag does not match the index line")
        extra = _grib_extra(message.payload)
        try:
            if variable == "rain":
                accumulation, grid = decode_precipitation_message(message.payload, member="c00", description=message.description, source_id=message.sha256)
                region = crop_grid(grid, south=10, north=22, west=68, east=80)
                if region.values.shape != (49, 49) or not np.isfinite(region.values).all():
                    raise CycleRefused(f"rain f{hour:03d}: rainfall target crop invalid")
                validate_message(message, date, grid.metadata, extra)
                rain_messages[hour] = GriddedAccumulationMessage(accumulation.start_hour, accumulation.end_hour, region.values, accumulation.source_id, accumulation.packing_quantum_mm)
            else:
                grid = decode_atmospheric_message(message.payload, member="c00", description=message.description, spec=ATMOSPHERIC_SPECS[variable], lead_hour=hour)
                region = crop_grid(grid, south=5, north=30, west=55, east=95)
                if region.values.shape != (51, 81) or not np.isfinite(region.values).all():
                    raise CycleRefused(f"{variable} f{hour:03d}: atmospheric context crop invalid")
                validate_message(message, date, grid.metadata, extra)
                atmosphere.setdefault(hour, {})[variable] = region.values
        except CycleRefused:
            raise
        except Exception as error:
            raise CycleRefused(f"{variable} f{hour:03d}: decode failed ({type(error).__name__}: {error})") from error
        sources.append({"family": family, "hour": hour, "variable": variable, "key": message.key, "byte_start": message.byte_start, "byte_end": message.byte_end, "bytes": message.length, "sha256": message.sha256, "index_line": message.description})
    rainfall, segments, failed = {}, {}, {}
    for product, lead in LEADS.items():
        try:
            result = reconstruct_minimal_accumulation_window([rain_messages[h] for h in lead["rain_hours"]], window_start_hour=lead["window"][0], window_end_hour=lead["window"][1])
            if result.rainfall_mm.shape != (49, 49) or not np.isfinite(result.rainfall_mm).all() or np.any(result.rainfall_mm < 0):
                raise ValueError("reconstructed rainfall is not a finite non-negative 49x49 field")
        except Exception as error:
            # the corpus treats each (cycle, lead) as its own case: a lead whose canonical reconstruction fails is withheld with its reason, the others stand
            failed[product] = f"canonical rainfall reconstruction failed ({type(error).__name__}: {error})"
            continue
        rainfall[product] = np.asarray(result.rainfall_mm, dtype=np.float64)
        segments[product] = {"segments": [segment.__dict__ for segment in result.segments], "subtraction_count": result.subtraction_count, "normalized_negative_cells": result.normalized_negative_count}
    if not rainfall:
        raise CycleRefused("no lead passed the canonical rainfall reconstruction: " + "; ".join(f"{k}: {v}" for k, v in failed.items()))
    return {"rainfall": rainfall, "atmosphere": atmosphere, "sources": sources, "reconstruction": segments, "failed_products": failed}


def build_features(rainfall: dict, atmosphere: dict) -> dict:
    """The 22-column deterministic matrix and the regime feature vector for each product, exactly as the corpus builder forms them from its cached arrays."""
    from backend.app.ml.forecast_regimes import ATMOSPHERIC_VARIABLES, extract_regime_features
    from backend.app.ml.phase2b import bilinear_to_target

    out = {}
    lat_grid, lon_grid = np.meshgrid(TARGET_LAT, TARGET_LON, indexing="ij")
    for product in rainfall:
        lead = LEADS[product]
        hour = lead["atmosphere_hour"]
        stack = np.stack([atmosphere[hour][name] for name in ATMOSPHERIC_VARIABLES])
        regime = extract_regime_features(stack, CONTEXT_LAT, CONTEXT_LON)
        aligned = np.stack([bilinear_to_target(field, CONTEXT_LAT, CONTEXT_LON, TARGET_LAT, TARGET_LON) for field in stack])
        matrix = np.column_stack((rainfall[product].ravel(), aligned.reshape(6, -1).T, np.broadcast_to(regime, (2401, len(regime))), lat_grid.ravel(), lon_grid.ravel(),
                                  np.full(2401, hour, dtype=np.float64))).astype(np.float32)
        if matrix.shape != (2401, 22) or not np.isfinite(matrix).all():
            raise CycleRefused(f"{product}: the 22-feature matrix is invalid")
        out[product] = {"regime": regime, "X": matrix}
    return out


class FrozenModels:
    """The frozen Track B artifacts, every file hash-checked against the final-freeze readiness record before use. Nothing is fitted here."""

    def __init__(self, parts: dict):
        self.__dict__.update(parts)

    @classmethod
    def load(cls) -> "FrozenModels":
        from xgboost import XGBRegressor
        from experiments.recent_historical.phase4i_operational_model_development_v1.regime import predict_proba
        from experiments.recent_historical.phase4j_operational_final_test_v1.governance import I, READY_SHA, read, sha

        ready_path = I / "final_freeze/FINAL_TEST_READY.json"
        if sha(ready_path) != READY_SHA:
            raise CycleRefused("frozen readiness record hash mismatch")
        ready, selection = read(ready_path), read(I / "final_freeze/model_selection_freeze.json")

        def verified(path, expected):
            if sha(path) != expected:
                raise CycleRefused(f"frozen model hash mismatch: {path.name}")
            return path

        def xgb(path, expected):
            model = XGBRegressor()
            model.load_model(verified(path, expected))
            return model

        models = ready["final_deterministic_models"]
        parts = {"ready_sha256": READY_SHA, "predict_proba": predict_proba,
                 "regime": read(verified(I / "regime_models/full_2023_classifier.json", ready["regime_classifier_sha256"])),
                 "ridge": read(verified(I / models["M1"]["path"], models["M1"]["sha256"])), "m2": xgb(I / models["M2"]["path"], models["M2"]["sha256"]), "experts": {}, "probability": {},
                 "hashes": {"readiness_record": READY_SHA, "regime_classifier": ready["regime_classifier_sha256"], "M1": models["M1"]["sha256"], "M2": models["M2"]["sha256"]}}
        for r in (0, 1, 2):
            info = models["M3_M4_shared_experts"][f"regime_{r}"]
            parts["experts"][r] = None if info["fallback"] else xgb(I / f"deterministic_models/expert_regime_{r}.json", info["sha256"])
            parts["hashes"][f"expert_regime_{r}"] = info["sha256"]
        for name in ("heavy", "very_heavy"):
            choice = selection[name]
            parts["probability"][name] = {
                "base": read(verified(I / f"probability_models/{name}/{choice['base']}.json", choice["base_sha256"])),
                "calibrator": read(verified(I / f"calibration/{name}/{choice['base']}_{choice['calibration']}.json", choice["calibrator_sha256"])),
                "threshold": choice["threshold"]}
            parts["hashes"][f"{name}_base"], parts["hashes"][f"{name}_calibrator"] = choice["base_sha256"], choice["calibrator_sha256"]
        return cls(parts)

    def apply(self, X: np.ndarray, regime_vector: np.ndarray) -> dict:
        from backend.app.ml.phase2b import safe_ridge_predict
        from backend.app.ml.phase2c import probability_features
        from experiments.recent_historical.phase4i_operational_model_development_v1.deterministic import predict_m2
        from experiments.recent_historical.phase4i_operational_model_development_v1.probability import apply_calibrator, predict_logistic

        p = self.predict_proba(regime_vector.reshape(1, -1), self.regime)[0]
        m2 = predict_m2(self.m2, X)
        experts = {r: (m2 if model is None else predict_m2(model, X)) for r, model in self.experts.items()}
        out = {"M0": X[:, 0].astype(np.float32), "M1": safe_ridge_predict(self.ridge, X).astype(np.float32), "M2": m2,
               "M3": experts[int(np.argmax(p))], "M4": np.maximum(0, sum(float(p[r]) * experts[r] for r in (0, 1, 2))).astype(np.float32), "regime_probability": p.astype(np.float64)}
        row_regime = np.repeat(p.reshape(1, 3), len(X), axis=0)
        X26 = probability_features(X, m2, row_regime)
        for name, block in self.probability.items():
            probability = apply_calibrator(predict_logistic(X26, block["base"]), block["calibrator"]).astype(np.float64)
            if not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1)):
                raise CycleRefused(f"{name} probability left [0, 1]")
            out[f"{name}_probability"] = probability
        for name in ("M0", "M1", "M2", "M3", "M4"):
            if not np.isfinite(out[name]).all() or np.any(out[name] < 0):
                raise CycleRefused(f"{name} produced a negative or non-finite rainfall")
        return out


def applicability(features: dict, training_matrix: np.ndarray, names: tuple[str, ...]) -> dict:
    """A heuristic range warning, never a skill statement: the share of cells of each feature outside the 0.1 to 99.9 percentile range of the 2023 training matrix."""
    low, high = np.quantile(training_matrix, [0.001, 0.999], axis=0)
    report = {}
    for product, block in features.items():
        outside = ((block["X"] < low) | (block["X"] > high)).mean(axis=0)
        report[product] = {name: float(outside[i]) for i, name in enumerate(names)}
    worst = max((value, product, name) for product, d in report.items() for name, value in d.items() if name not in STATIC_FEATURES)
    return {"status": "WARNING" if worst[0] > 0.05 else "WITHIN_TRAINING_RANGE", "share_outside_training_range_by_feature": report,
            "largest_share": {"share": worst[0], "product": worst[1], "feature": worst[2]},
            "method": "per-feature 0.1 to 99.9 percentile range of the 2023 training matrix; a warning above 5 percent of cells; heuristic, not a validity test"}


def run_cycle(source: MessageSource, date: str, models: FrozenModels, *, training_matrix: np.ndarray | None = None, feature_names: tuple[str, ...] | None = None) -> dict:
    """The whole path for one cycle. Returns {"arrays": ..., "provenance": ...}; raises CycleRefused on any failed gate and then nothing is to be published."""
    decoded = decode_cycle(source, date)
    features = build_features(decoded["rainfall"], decoded["atmosphere"])
    arrays, regimes = {}, {}
    for product in features:
        applied = models.apply(features[product]["X"], features[product]["regime"])
        regimes[product] = applied.pop("regime_probability")
        for name, values in applied.items():
            arrays[f"{name}_{product}"] = values.reshape(49, 49)
        arrays[f"regime_probability_{product}"] = regimes[product]
    provenance = {"sources": decoded["sources"], "reconstruction": decoded["reconstruction"], "withheld_products": decoded["failed_products"], "frozen_models": models.hashes}
    if training_matrix is not None and feature_names is not None:
        provenance["applicability"] = applicability(features, training_matrix, feature_names)
    return {"arrays": arrays, "features": features, "provenance": provenance}
