"""The IMD 2026 availability probe must stay metadata-only and gated."""

import hashlib
from pathlib import Path

import pytest
from urllib.error import URLError

from scripts import probe_imd_2026_header as probe


def test_header_probe_protocol_is_frozen_and_requires_2026(tmp_path):
    rule, digest = probe.checked(probe.PROTOCOL)
    assert digest == hashlib.sha256(probe.PROTOCOL.read_bytes()).hexdigest()
    assert rule["request"] == {"method": "POST", "form": {"RF25": 2026}}
    assert "RAINFALL variable values" in rule["prohibited_reads"]


def test_header_check_uses_only_axes_and_rainfall_metadata_on_known_file():
    path = Path(__file__).resolve().parents[2] / "experiments/recent_historical/imd/RF25_ind2025_rfp25.nc"
    if not path.is_file():
        pytest.skip("local IMD 2025 reference is unavailable")
    header = probe.header_only(path, 2025)
    assert header["required_dates_complete"] is True
    assert header["grid_points"] == [129, 135]
    assert header["rainfall_values_read"] is False
    assert header["rainfall_units"] == "mm"


def test_probe_will_not_request_imd_without_annual_forecast_seal(monkeypatch, tmp_path):
    monkeypatch.setattr(probe.yearly, "OUT", tmp_path / "missing-year.json")
    monkeypatch.setattr(probe, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network was opened")))
    with pytest.raises(FileNotFoundError):
        probe.probe()


def test_transport_failure_is_not_treated_as_evidence_of_unpublished_reference(monkeypatch, tmp_path):
    rule = {"minimum_free_disk_bytes": 0, "source_endpoint": "https://example.test/RF25.php",
            "request": {"method": "POST", "form": {"RF25": 2026}},
            "maximum_response_bytes": 60_000_000}
    monkeypatch.setattr(probe, "prerequisites", lambda _protocol: (rule, "p", "a", "y"))
    monkeypatch.setattr(probe, "OUT", tmp_path / "result.json")
    monkeypatch.setattr(probe, "LOCAL", tmp_path / "imd.nc")
    monkeypatch.setattr(probe, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")))
    result = probe.probe(output=tmp_path / "result.json")
    assert result["status"] == "NETWORK_REACHABILITY_UNRESOLVED"
    assert result["observation_rainfall_values_read"] is False
    assert not probe.LOCAL.exists()
