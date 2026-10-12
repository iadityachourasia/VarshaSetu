"""Same-cell June 2024 development validation of sealed partial-grid fields."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.data.monthly_qc import product_valid_date  # noqa: E402
from backend.app.data_sources.imd_rainfall import load_imd_day  # noqa: E402
from scripts import run_partial_grid_candidate as forecast  # noqa: E402
from scripts import run_partial_cell_development as prior  # noqa: E402

OUT = ROOT / "data/manifests/research_pilot/partial_grid_inference_score_v1.json"
PRIOR = ROOT / "data/manifests/research_pilot/partial_cell_development_result_v1.json"
IMD = ROOT / "experiments/recent_historical/imd/RF25_ind2024_rfp25.nc"
MODELS = ("M0", "M2", "M4")
THRESHOLDS = (64.5, 115.6)


def checked(path: Path) -> tuple[dict, str]:
    digest = forecast.sha(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError(f"evidence hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def metrics(field: np.ndarray, observed: np.ndarray, mask: np.ndarray) -> dict:
    if field.shape != (49, 49) or observed.shape != field.shape or mask.shape != field.shape:
        raise ValueError("paired field geometry differs")
    if not np.isfinite(field[mask]).all() or not np.isfinite(observed[mask]).all():
        raise ValueError("paired cells contain a non-finite value")
    error = field[mask] - observed[mask]
    events = {}
    for threshold in THRESHOLDS:
        predicted, truth = field[mask] >= threshold, observed[mask] >= threshold
        events[str(threshold)] = {"hits": int(np.sum(predicted & truth)), "misses": int(np.sum(~predicted & truth)),
                                  "false_alarms": int(np.sum(predicted & ~truth)), "correct_negatives": int(np.sum(~predicted & ~truth))}
    return {"paired_cells": int(mask.sum()), "squared_error_sum": float(error @ error),
            "error_sum": float(error.sum()), "events": events}


def aggregate(rows: list[dict]) -> dict:
    if not rows:
        return {"case_count": 0, "reason": "no ready paired cases"}
    result = {"case_count": len(rows), "initialization_count": len({row["cycle"] for row in rows}),
              "paired_cells": sum(row["models"]["M0"]["paired_cells"] for row in rows), "models": {}}
    for name in MODELS:
        cases = [row["models"][name] for row in rows]
        n = sum(case["paired_cells"] for case in cases)
        if n != result["paired_cells"]:
            raise ValueError("model comparators use different paired cells")
        model = {"rmse_mm": float(np.sqrt(sum(case["squared_error_sum"] for case in cases) / n)),
                 "mean_bias_mm": float(sum(case["error_sum"] for case in cases) / n), "events": {}}
        for threshold in THRESHOLDS:
            counts = {key: sum(case["events"][str(threshold)][key] for case in cases)
                      for key in ("hits", "misses", "false_alarms", "correct_negatives")}
            h, m, f = counts["hits"], counts["misses"], counts["false_alarms"]
            counts.update({"csi": h / (h + m + f) if h + m + f else None,
                           "pod": h / (h + m) if h + m else None,
                           "far": f / (h + f) if h + f else None})
            model["events"][str(threshold)] = counts
        result["models"][name] = model
    return result


def date_bootstrap(rows: list[dict], *, repeats: int = 1000) -> dict:
    dates = sorted({row["cycle"] for row in rows})
    if len(dates) < 2:
        return {"reason": "fewer than two initialization dates"}
    by_date = {date: [row for row in rows if row["cycle"] == date] for date in dates}
    rng = np.random.default_rng(26080)
    rmse, csi = [], []
    for _ in range(repeats):
        sampled = [row for idx in rng.integers(0, len(dates), len(dates)) for row in by_date[dates[idx]]]
        grouped = aggregate(sampled)
        rmse.append(grouped["models"]["M4"]["rmse_mm"] - grouped["models"]["M2"]["rmse_mm"])
        m4 = grouped["models"]["M4"]["events"]["64.5"]["csi"]
        m2 = grouped["models"]["M2"]["events"]["64.5"]["csi"]
        if m4 is not None and m2 is not None:
            csi.append(m4 - m2)
    return {"unit": "initialization_date", "repeats": repeats, "seed": 26080,
            "rmse_m4_minus_m2_95pct_interval_mm": np.quantile(rmse, [.025, .975]).tolist(),
            "heavy_csi_m4_minus_m2_95pct_interval": np.quantile(csi, [.025, .975]).tolist() if csi else None,
            "heavy_csi_defined_repeats": len(csi),
            "interpretation": "Descriptive development-validation interval; serial and spatial dependence remain, not an independent-test promotion gate"}


def score() -> dict:
    rule, protocol_hash = forecast.protocol()
    forecast_year, forecast_hash = checked(forecast.OUT)
    if forecast_year["protocol_sha256"] != protocol_hash or forecast_year != forecast.seal_year(protocol_hash):
        raise ValueError("forecast-only candidate seal does not reproduce")
    previous, previous_hash = checked(PRIOR)
    imd_hash = forecast.sha(IMD)
    if imd_hash != previous["year_results"][1]["imd_reference_sha256"]:
        raise ValueError("2024 IMD reference differs from prior development study")
    rows, refusals = [], []
    for case in forecast_year["cases"]:
        cycle = case["cycle"]
        case_path = forecast.CACHE / cycle
        manifest = forecast.verify_case(case_path, protocol_hash)
        if forecast.sha(case_path / "manifest.json") != case["manifest_sha256"]:
            raise ValueError("case manifest differs from year seal")
        initialization = datetime.strptime(cycle, "%Y%m%d").replace(tzinfo=timezone.utc)
        with np.load(case_path / "fields.npz", allow_pickle=False) as fields:
            for product, info in manifest["products"].items():
                if info["status"] != "READY":
                    refusals.append({"cycle": cycle, "product": product, "strict_passed": info["strict_passed"], "reason": info["reason"]})
                    continue
                valid_date = product_valid_date(initialization, product)
                reference = load_imd_day(IMD, valid_date, south=10, north=22, west=68, east=80)
                if (reference.rainfall_mm.shape != (49, 49)
                        or not np.array_equal(reference.latitude, np.linspace(10, 22, 49))
                        or not np.array_equal(reference.longitude, np.linspace(68, 80, 49))):
                    raise ValueError("2024 forecast and IMD coordinates differ")
                mask = fields[f"valid_{product}"].astype(bool) & reference.valid_mask
                if not mask.any():
                    raise ValueError("ready lead has no IMD-paired cells")
                case_metrics = {name: metrics(fields[f"{name}_{product}"], reference.rainfall_mm, mask) for name in MODELS}
                rows.append({"cycle": cycle, "product": product, "valid_date": valid_date.isoformat(),
                             "strict_passed": info["strict_passed"], "forecast_valid_cells": info["valid_cells"],
                             "paired_cells": int(mask.sum()), "case_manifest_sha256": case["manifest_sha256"],
                             "models": case_metrics})
    if len(rows) + len(refusals) != 90 or len(rows) != forecast_year["model_ready_leads"]:
        raise ValueError("paired case population differs from sealed forecast population")
    groups = {"all_ready": rows, "strict_pass_ready": [r for r in rows if r["strict_passed"]],
              "strict_withheld_ready": [r for r in rows if not r["strict_passed"]]}
    for product in rule["lead_windows_hours"]:
        groups[product] = [r for r in rows if r["product"] == product]
    summary = {name: aggregate(group) for name, group in groups.items()}
    return {"schema": "varshasetu-partial-grid-inference-score-v1", "protocol_sha256": protocol_hash,
            "forecast_year_sha256": forecast_hash, "prior_development_result_sha256": previous_hash,
            "imd_reference_sha256": imd_hash, "source_track": rule["track"], "role": "2024_DEVELOPMENT_VALIDATION_ONLY",
            "common_cell_comparison": True, "reference_used_only_after_forecast_seal": True,
            "ready_case_count": len(rows), "refused_case_count": len(refusals), "refusals": refusals,
            "summary": summary, "date_bootstrap_all_ready": date_bootstrap(rows), "cases": rows,
            "interpretation": "Development validation of a partial-grid candidate; no independent-year skill, calibration promotion or live product claim"}


def main() -> None:
    if OUT.exists():
        raise FileExistsError("partial-grid score is write-once")
    result = score()
    value = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(json.dumps({"ready_case_count": result["ready_case_count"], "refused_case_count": result["refused_case_count"],
                      "all_ready": result["summary"]["all_ready"], "strict_withheld_ready": result["summary"]["strict_withheld_ready"]}, sort_keys=True))


if __name__ == "__main__":
    main()
