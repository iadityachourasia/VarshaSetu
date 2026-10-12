"""Bounded unattended cycle selection never publishes twice or bypasses guards."""

from datetime import date
import json
import sys

from scripts.live import run_scheduled
from backend.app.live.pipeline import CycleRefused
from backend.app.live.season import jjas_scope


def test_jjas_scope_is_based_on_valid_initialization_date():
    assert jjas_scope("20260930") == "JJAS_RESEARCH_SCOPE"
    assert jjas_scope("20261001") == "OUTSIDE_JJAS_RESEARCH_SCOPE"
    assert jjas_scope("20260531") == "OUTSIDE_JJAS_RESEARCH_SCOPE"


class Source:
    def __init__(self, cycle):
        self.cycle = cycle

    def plan(self):
        if self.cycle == "20260606":
            raise CycleRefused("index incomplete")
        return [{"bytes": 1000}]


def test_scheduler_selects_latest_complete_index_and_logs_publication(tmp_path):
    called = []
    code = run_scheduled.run_once(today=date(2026, 6, 6), live_root=tmp_path / "live", log_root=tmp_path / "logs",
                                  source_factory=Source, runner=lambda cycle, confirmed: called.append((cycle, confirmed)) or 0,
                                  disk_free=run_scheduled.MIN_FREE_BYTES)
    assert code == 0 and called == [("20260605", True)]
    logs = [json.loads(p.read_text()) for p in (tmp_path / "logs").glob("*.json")]
    assert {row["cycle"]: row["outcome"] for row in logs} == {
        "20260606": "source_unavailable", "20260605": "published"
    }
    assert all(row["observation_read"] is False for row in logs)
    assert not (tmp_path / "live/.scheduled.lock").exists()


def test_scheduler_refuses_low_disk_and_does_not_run(tmp_path):
    code = run_scheduled.run_once(today=date(2026, 6, 6), live_root=tmp_path / "live", log_root=tmp_path / "logs",
                                  source_factory=lambda _: Source("20260605"), runner=lambda *_: 1, disk_free=100)
    assert code == 8
    assert json.loads(next((tmp_path / "logs").glob("*.json")).read_text())["outcome"] == "disk_guard"


def test_scheduler_skips_existing_bundle(tmp_path):
    (tmp_path / "live/live/20260606").mkdir(parents=True)
    code = run_scheduled.run_once(today=date(2026, 6, 6), live_root=tmp_path / "live", log_root=tmp_path / "logs",
                                  source_factory=lambda _: (_ for _ in ()).throw(AssertionError("no network")),
                                  runner=lambda *_: 1, disk_free=0)
    assert code == 0
    assert json.loads(next((tmp_path / "logs").glob("*.json")).read_text())["outcome"] == "already_published"


def test_scheduler_records_refusal_reason_without_retry(tmp_path):
    calls = []

    def refuse(cycle, confirmed):
        calls.append(cycle)
        print("CYCLE REFUSED: canonical rainfall accumulation failed", file=sys.stderr)
        return 4

    code = run_scheduled.run_once(today=date(2026, 6, 6), live_root=tmp_path / "live", log_root=tmp_path / "logs",
                                  source_factory=lambda _: Source("20260605"), runner=refuse,
                                  disk_free=run_scheduled.MIN_FREE_BYTES)
    receipt = json.loads(next((tmp_path / "logs").glob("*.json")).read_text())
    assert code == 4 and calls == ["20260606"]
    assert receipt["outcome"] == "cycle_refused" and "canonical rainfall" in receipt["detail"]


def test_scheduler_skips_outside_jjas_without_network(tmp_path):
    code = run_scheduled.run_once(today=date(2026, 10, 7), live_root=tmp_path / "live", log_root=tmp_path / "logs",
                                  source_factory=lambda _: (_ for _ in ()).throw(AssertionError("off-season network")),
                                  runner=lambda *_: 1, disk_free=run_scheduled.MIN_FREE_BYTES)
    receipt = json.loads(next((tmp_path / "logs").glob("*.json")).read_text())
    assert code == 0 and receipt["outcome"] == "outside_jjas_scope"
