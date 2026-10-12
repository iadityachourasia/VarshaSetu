"""Development-only nested 24-hour rainfall exceedance model.

The conditional construction makes the very-heavy event a subset of heavy
without a post-hoc projection. It does not itself establish reliability.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

CLIP = 1e-6
FORMAT = "varshasetu-extreme-ordinal-logistic-v1"


def _scores(heavy: np.ndarray, very_heavy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h = np.asarray(heavy, dtype=np.float64)
    v = np.asarray(very_heavy, dtype=np.float64)
    if (h.ndim != 1 or v.shape != h.shape or not np.isfinite(h).all()
            or not np.isfinite(v).all() or np.any((h < 0) | (h > 1))
            or np.any((v < 0) | (v > 1))):
        raise ValueError("base scores must be matching finite probability vectors")
    return _logit(h), _logit(v)


def _logit(p: np.ndarray) -> np.ndarray:
    clipped = np.clip(p, CLIP, 1 - CLIP)
    return np.log(clipped / (1 - clipped))


def _binary(y: np.ndarray, size: int) -> np.ndarray:
    values = np.asarray(y)
    if values.shape != (size,) or not np.isin(values, (0, 1)).all():
        raise ValueError("labels must be aligned binary vectors")
    return values.astype(np.uint8)


def fit_ordinal(base_heavy: np.ndarray, base_very_heavy: np.ndarray,
                label_heavy: np.ndarray, label_very_heavy: np.ndarray) -> dict:
    """Fit two fixed, unweighted logistic heads on a calibration block only."""
    xh, xv = _scores(base_heavy, base_very_heavy)
    yh, yv = _binary(label_heavy, len(xh)), _binary(label_very_heavy, len(xh))
    if np.any(yv > yh):
        raise ValueError("very-heavy labels must be nested within heavy labels")
    if set(np.unique(yh)) != {0, 1} or set(np.unique(yv[yh == 1])) != {0, 1}:
        raise ValueError("both logistic heads require positive and negative labels")
    heavy = LogisticRegression(C=0.1, solver="lbfgs", max_iter=500,
                               random_state=26080).fit(xh[:, None], yh)
    conditional = LogisticRegression(C=0.1, solver="lbfgs", max_iter=500,
                                     random_state=26080).fit(xv[yh == 1, None], yv[yh == 1])
    if heavy.n_iter_[0] >= 500 or conditional.n_iter_[0] >= 500:
        raise RuntimeError("ordinal logistic fit did not converge")
    return {
        "format": FORMAT, "base_score_clip": CLIP, "C": 0.1,
        "solver": "lbfgs", "max_iter": 500, "random_state": 26080,
        "heavy": {"coefficient": float(heavy.coef_[0, 0]),
                  "intercept": float(heavy.intercept_[0]), "fit_rows": int(len(yh)),
                  "fit_events": int(yh.sum()), "iterations": int(heavy.n_iter_[0])},
        "very_heavy_given_heavy": {"coefficient": float(conditional.coef_[0, 0]),
                                   "intercept": float(conditional.intercept_[0]),
                                   "fit_rows": int(yh.sum()), "fit_events": int(yv.sum()),
                                   "iterations": int(conditional.n_iter_[0])},
    }


def predict_ordinal(base_heavy: np.ndarray, base_very_heavy: np.ndarray,
                    artifact: dict) -> tuple[np.ndarray, np.ndarray]:
    if (artifact.get("format") != FORMAT or artifact.get("base_score_clip") != CLIP
            or artifact.get("C") != 0.1):
        raise ValueError("unknown ordinal probability artifact")
    xh, xv = _scores(base_heavy, base_very_heavy)
    h, c = artifact["heavy"], artifact["very_heavy_given_heavy"]
    for part in (h, c):
        if not np.isfinite([part["coefficient"], part["intercept"]]).all():
            raise ValueError("ordinal coefficients must be finite")
    heavy = np.exp(-np.logaddexp(0, -(xh * h["coefficient"] + h["intercept"])))
    conditional = np.exp(-np.logaddexp(0, -(xv * c["coefficient"] + c["intercept"])))
    very_heavy = heavy * conditional
    if not np.isfinite(very_heavy).all() or np.any(very_heavy > heavy):
        raise ValueError("ordinal prediction violated nesting")
    return heavy, very_heavy
