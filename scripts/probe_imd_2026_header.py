"""Probe IMD 2026 annual RF25 availability without reading rainfall values.

Requires the sealed 2026 forecast-only year, frozen probe protocol and the
team's prior-use audit. A valid complete file stays local and is hash recorded;
the response is never used for training or forecast verification here.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from scipy.io import netcdf_file  # noqa: E402

from scripts import summarize_gefs_2026_forecast_year as yearly  # noqa: E402

PROTOCOL = ROOT / "data/manifests/research_pilot/2026_imd_header_probe_protocol_v1.json"
AUDIT = ROOT / "data/manifests/research_pilot/2026_prior_observation_use_audit_v2.json"
OUT = ROOT / "data/manifests/research_pilot/2026_imd_header_probe_result_v1.json"
RETRY_PROTOCOL = ROOT / "data/manifests/research_pilot/2026_imd_header_probe_retry_protocol_v2.json"
RETRY_OUT = ROOT / "data/manifests/research_pilot/2026_imd_header_probe_result_v2.json"
LOCAL = ROOT / "experiments/recent_historical/imd_2026_candidate/RF25_ind2026_rfp25.nc"


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def checked(path: Path) -> tuple[dict, str]:
    digest = sha(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError(f"frozen record hash mismatch: {path.name}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def header_only(path: Path, year: int) -> dict:
    """Only coordinate arrays and RAINFALL metadata are accessed."""
    with netcdf_file(path, "r", mmap=True) as dataset:
        times = np.asarray(dataset.variables["TIME"].data, dtype=np.float64).copy()
        lat = np.asarray(dataset.variables["LATITUDE"].data, dtype=np.float64).copy()
        lon = np.asarray(dataset.variables["LONGITUDE"].data, dtype=np.float64).copy()
        rainfall = dataset.variables["RAINFALL"]
        shape = list(rainfall.shape)
        units = rainfall.units.decode() if isinstance(rainfall.units, bytes) else str(rainfall.units)
        del rainfall
        time_units = dataset.variables["TIME"].units
        time_units = time_units.decode() if isinstance(time_units, bytes) else str(time_units)
    first = (date(year, 6, 1) - date(1900, 12, 31)).days
    last = (date(year, 10, 3) - date(1900, 12, 31)).days
    selected = times[(times >= first) & (times <= last)]
    complete = bool(np.array_equal(selected, np.arange(first, last + 1)))
    return {"year": year, "annual_record_count": int(times.size), "variable_shape": shape,
            "rainfall_units": units, "time_units": time_units,
            "grid_points": [int(lat.size), int(lon.size)],
            "coordinate_bounds": {"latitude": [float(lat[0]), float(lat[-1])], "longitude": [float(lon[0]), float(lon[-1])]},
            "required_period": f"{year}-06-01/{year}-10-03", "required_record_count": int(selected.size),
            "required_dates_complete": complete, "rainfall_values_read": False}


def prerequisites(protocol: Path = PROTOCOL) -> tuple[dict, str, str, str]:
    rule, protocol_hash = checked(protocol)
    audit, audit_hash = checked(AUDIT)
    if audit["prior_use_gate"] != "PROVISIONALLY_CLEARED_BY_TEAM_ATTESTATION_AND_LOCAL_AUDIT" or audit["observation_values_read_for_this_audit"] is not False:
        raise ValueError("2026 prior-use audit did not clear the header probe")
    year, year_hash = checked(yearly.OUT)
    if year != yearly.summary() or year["cycle_count"] != 122 or year["observation_read"] is not False:
        raise ValueError("2026 forecast-only JJAS seal is not verified")
    if rule["request"] != {"method": "POST", "form": {"RF25": 2026}} or rule["maximum_response_bytes"] != 60000000:
        raise ValueError("IMD header probe protocol differs")
    return rule, protocol_hash, audit_hash, year_hash


def probe(*, protocol: Path = PROTOCOL, output: Path = OUT, previous_result: Path | None = None) -> dict:
    rule, protocol_hash, audit_hash, year_hash = prerequisites(protocol)
    if previous_result is not None:
        previous, previous_hash = checked(previous_result)
        if previous.get("error_type") != "URLError" or previous.get("response_bytes", 0):
            raise ValueError("retry requires a prior transport failure with no response bytes")
        if rule.get("previous_result_sha256") != previous_hash:
            raise ValueError("retry protocol does not link prior failed probe")
    if output.exists() or LOCAL.exists():
        raise FileExistsError("2026 IMD header probe is write-once")
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(LOCAL.parent).free < rule["minimum_free_disk_bytes"]:
        raise ValueError("50 GiB free-space guard failed")
    stage = LOCAL.with_name(LOCAL.name + ".part")
    if stage.exists():
        raise FileExistsError("prior IMD partial download requires investigation")
    record = {"schema": "varshasetu-2026-imd-header-probe-result-v2" if previous_result is not None else "varshasetu-2026-imd-header-probe-result-v1",
              "protocol_sha256": protocol_hash, "prior_use_audit_sha256": audit_hash,
              "forecast_year_sha256": year_hash, "source_endpoint": rule["source_endpoint"],
              "request": rule["request"], "observation_rainfall_values_read": False,
              "forecast_observation_pairing": False,
              "probed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if previous_result is not None:
        record["previous_result_sha256"] = previous_hash
    request = Request(rule["source_endpoint"], data=urlencode({"RF25": 2026}).encode("ascii"), method="POST",
                      headers={"User-Agent": "VarshaSetu-research/1.0 (local academic use)"})
    try:
        with urlopen(request, timeout=300) as response, stage.open("xb") as stream:
            record["http_status"] = response.status
            record["content_type"] = response.headers.get("Content-Type")
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > rule["maximum_response_bytes"]:
                raise ValueError("IMD response exceeds 60 MB cap")
            digest = hashlib.sha256()
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > rule["maximum_response_bytes"]:
                    raise ValueError("IMD response exceeds 60 MB cap")
                stream.write(block)
                digest.update(block)
        record["response_bytes"] = total
        record["response_sha256"] = digest.hexdigest()
        with stage.open("rb") as stream:
            signature = stream.read(4)
        if total < 1_000_000 or signature not in (b"CDF\x01", b"CDF\x02"):
            record["status"] = "UNAVAILABLE_OR_NON_NETCDF_RESPONSE"
        else:
            header = header_only(stage, 2026)
            record["header"] = header
            expected_grid = header["grid_points"] == [129, 135] and header["coordinate_bounds"] == {"latitude": [6.5, 38.5], "longitude": [66.5, 100.0]}
            if not header["required_dates_complete"] or not expected_grid or header["rainfall_units"] != "mm":
                record["status"] = "REFERENCE_HEADER_INCOMPLETE_OR_UNEXPECTED"
            else:
                stage.replace(LOCAL)
                record["status"] = "LOCAL_REFERENCE_HEADER_READY_UNSCORED"
                record["local_path"] = LOCAL.relative_to(ROOT).as_posix()
    except (HTTPError, URLError, OSError) as error:
        record["status"] = "SOURCE_HTTP_ERROR" if isinstance(error, HTTPError) else "NETWORK_REACHABILITY_UNRESOLVED"
        record["error_type"] = type(error).__name__
        if isinstance(error, HTTPError):
            record["http_status"] = error.code
    finally:
        if stage.exists():
            stage.unlink()
    record["independent_test_status"] = "CANDIDATE_NOT_SCORED"
    return record


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-after-transport-error", action="store_true")
    args = parser.parse_args()
    output = RETRY_OUT if args.retry_after_transport_error else OUT
    result = probe(protocol=RETRY_PROTOCOL, output=output, previous_result=OUT) if args.retry_after_transport_error else probe()
    value = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    output.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + output.name + "\n", encoding="ascii")
    print(json.dumps({"status": result["status"], "http_status": result.get("http_status"),
                      "response_bytes": result.get("response_bytes"), "header": result.get("header")}, sort_keys=True))


if __name__ == "__main__":
    main()
