"""Pure decision logic of the one-shot 2022 test of the geography-aware follow-up (protocol v3, docs/132).

No data access and no model library: it turns zone statistic stacks and bootstrap results into the pre-registered P1 to P4 decisions for a candidate set,
the guardrails on the test year, and the multiplicity-labelled interval. Tested on synthetic data before 2022 is opened.
"""

from __future__ import annotations

import numpy as np

from backend.app.ml import zone_verification as zv
from backend.app.ml.geoaware import G2_MAX_ABS_BIAS_MM, G3_MIN_VERY_HEAVY_FREQUENCY_BIAS
from backend.app.ml.geoaware_followup import G4_MAX_ZONE_HEAVY_FREQUENCY_BIAS, ZONE

DECISION_LEVEL = 0.975                 # two candidate sets on one year: Bonferroni, two-sided alpha 0.025 each
RMSE_TOLERANCE_MM = 0.2
REPORT_ZONES = ("ALL", ZONE)
DIFF_METRICS = ("rmse", "bias", "heavy_csi", "heavy_fb", "very_heavy_csi")


def difference_statistic_factory(pairs: list[tuple[str, str]]):
    """A ``statistic`` for zv.paired_bootstrap: metric(zone, a) - metric(zone, b) for every (a, b) pair, zone in ALL and the Ghats-coast zone."""
    zone_index = {name: i for i, name in enumerate(zv.ZONES)}

    def statistic(totals: np.ndarray, models: list[str]) -> dict[tuple, float]:
        model_index = {name: i for i, name in enumerate(models)}
        out = {}
        for a, b in pairs:
            for zone in REPORT_ZONES:
                for metric in DIFF_METRICS:
                    out[("diff", zone, a, b, metric)] = zv._metric(totals[zone_index[zone], model_index[a]], metric) - zv._metric(totals[zone_index[zone], model_index[b]], metric)
        return out
    return statistic


def guardrails_on_test(pooled: dict, raw_pooled: dict) -> dict:
    """G1 to G4 on the test year from zv.metrics blocks. ``pooled`` is {zone: metrics} for the candidate, ``raw_pooled`` for Raw. Undefined never passes."""
    heavy_csi, raw_csi = pooled["ALL"]["categorical"]["heavy"]["CSI"], raw_pooled["ALL"]["categorical"]["heavy"]["CSI"]
    very_fb = pooled["ALL"]["categorical"]["very_heavy"]["frequency_bias"]
    zone_fb = pooled[ZONE]["categorical"]["heavy"]["frequency_bias"]
    bias = pooled["ALL"]["bias_mm"]
    return {"G1": bool(heavy_csi is not None and raw_csi is not None and heavy_csi >= raw_csi),
            "G2": bool(bias is not None and abs(bias) <= G2_MAX_ABS_BIAS_MM),
            "G3": bool(very_fb is not None and very_fb >= G3_MIN_VERY_HEAVY_FREQUENCY_BIAS),
            "G4": bool(zone_fb is not None and zone_fb <= G4_MAX_ZONE_HEAVY_FREQUENCY_BIAS)}


def decide(candidate: str, comparator: str, pooled: dict[str, dict], raw_pooled: dict, bootstrap: dict, support: dict) -> dict:
    """The pre-registered P1 to P4 for one candidate set (B1 against B0). P4 (comparator identity) is stated by the caller.

    P1 needs the zone heavy-rain CSI difference with its 97.5 percent interval excluding zero in the positive direction. If the zone fails the support gate for
    heavy rain the test is *unevaluable*: it is neither a pass nor a fail."""
    zone_support = support[ZONE]
    if not zone_support["heavy"]["supported"]:
        return {"status": "UNEVALUABLE", "reason": "the Ghats-coast zone fails the support gate for heavy rain on the test year", "support": zone_support, "adds_value": None}
    csi = bootstrap[("diff", ZONE, candidate, comparator, "heavy_csi")]
    rmse = bootstrap[("diff", "ALL", candidate, comparator, "rmse")]
    p1 = bool(csi["status"] == "ok" and csi["point"] > 0 and csi["interval"][0] > 0)
    p2 = bool(rmse["status"] == "ok" and rmse["point"] <= RMSE_TOLERANCE_MM)
    guard = guardrails_on_test(pooled, raw_pooled)
    p3 = bool(guard["G1"] and guard["G2"] and guard["G4"])
    return {"status": "EVALUATED", "P1_zone_heavy_csi_beats_comparator_975": p1, "P2_overall_rmse_within_tolerance": p2, "P3_gating_guardrails_G1_G2_G4": p3,
            "guardrails": guard, "g3_reported_only": guard["G3"], "zone_heavy_csi_difference": csi, "overall_rmse_difference": rmse,
            "adds_value": bool(p1 and p2 and p3), "level": DECISION_LEVEL, "support": zone_support}
