# June 2024 no-refit probability transport check

Date: 2026-10-07. The [lead-aware recalibration study](152_LEAD_AWARE_PROBABILITY_DEVELOPMENT.md)
showed only a small, inconclusive development-block improvement. This
follow-up tested whether its **unchanged fitted coefficients** help on the
June partial-grid population that had shown severe very-heavy warning
overforecast. It is an explicitly consumed-data diagnostic: June 2024
includes dates in the early 2024 calibration block, June outcomes were
inspected in earlier studies, and the base models were selected using 2024.
No independent transfer or calibration claim is possible.

The `june_probability_transport_protocol_v1.json` was hash-sealed before
replay. All 30 June 2024 cycles and 90 Day 1–3 leads were decoded from
hash-verified stored GEFS messages with **no IMD read**. For each lead the
research worker rebuilt forecast-time features on valid masked cells,
recomputed the frozen 2023-trained base scores, and applied the sealed pooled
and lead-aware recalibrators without refitting or changing the 0.10/0.05
warning cutoffs. Both output pairs were projected to obey
`P(very heavy) ≤ P(heavy)`. Before retaining either candidate, the replay
required its mask, M0/M2/M4 rainfall and frozen projected probabilities to
match the [prior coherent replay](151_COHERENT_PARTIAL_GRID_REPLAY.md)
bitwise. It retained 55 originally ready and 35 newly ready leads. The
forecast-only arrays and 30 per-case/source receipts were hash-sealed before
observation pairing; the pooled and lead-aware arms required projection at
1,315 and 1,384 forecast cells, respectively. Invalid cells stayed NaN.

After the forecast seal, all arms were paired with the same 116,823
GEFS/IMD-valid cells, including 1,576 observed heavy and 206 very-heavy
cell events, using the 03–03 UTC 24-hour reference. The frozen
control reproduced the earlier coherent score exactly. BSS uses the same
2023 training climatology; warning frequency bias is at the unchanged
2024-selected very-heavy cutoff.

| All 90 June leads | Heavy BSS | Very-heavy BSS | Joint Brier | Very-heavy warning frequency bias |
|---|---:|---:|---:|---:|
| Frozen isotonic, projected | **+0.0783** | **−0.0302** | **0.0141130** | 9.24× |
| New pooled logistic, projected | +0.0647 | −0.0845 | 0.0143904 | 6.14× |
| New lead-aware logistic, projected | +0.0639 | −0.0835 | 0.0143997 | 6.18× |

The lead-aware minus frozen joint-Brier difference is about +0.000287.
A 1,000-repeat initialization-date bootstrap gives a descriptive 95%
interval of **+0.000093 to +0.000502**, entirely worse. Lead-aware minus
new pooled joint-Brier has interval −0.000101 to +0.000103, crossing zero.
The 55 previously ready and 35 newly ready strata, each lead, event counts,
fixed ten-bin reliability, CSI, POD, FAR, ETS, Brier/BSS and bootstrap
intervals are in the write-once
`june_probability_transport_score_v1.json` with its SHA-256 sidecar.
At the frozen cutoff the candidates forecast fewer very-heavy events, but
still about six times the observed frequency and with worse probabilistic
skill. Fewer warnings alone is not a calibration success.

**Decision:** reject the pooled and lead-aware candidates for the June
research product. Keep the unchanged strict live bundle and global rainfall
default. The coherent partial-grid path also remains research-only. A new
probability method needs a distinct development protocol and a genuinely
independent year with sufficient very-heavy support before any promotion.
The complete 2026 IMD reference is still unavailable, and NOAA model-version
comparability remains open.

Reproduce the forecast seal with
`python scripts/run_june_probability_transport.py --all-june-2024`, then
the descriptive score with `python scripts/score_june_probability_transport.py`.
Both commands refuse changed protocol, fit, source, prior forecast or result
hashes. No frontend, live API or scheduler path invokes these scripts.
The score reproduced its sealed result byte for byte. Eight focused tests
passed, and the full backend suite passed **767 tests** on 7 October 2026.
