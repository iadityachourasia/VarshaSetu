"""Forecast-time-only atmospheric regime features, pseudo-labels, and classifier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.linear_model import LogisticRegression


REGIME_NAMES = (
    "ACTIVE_MONSOON",
    "BREAK_WEAK_MONSOON",
    "LOW_DEPRESSION_INFLUENCED",
)
ATMOSPHERIC_VARIABLES = ("u850", "v850", "q700", "z500", "mslp", "pwat")
FEATURE_NAMES = (
    "pwat_area_mean",
    "q700_area_mean",
    "u850_area_mean",
    "v850_area_mean",
    "wind_speed_area_mean",
    "moisture_transport_area_mean",
    "mslp_area_mean",
    "mslp_minimum",
    "mslp_range",
    "z500_area_mean",
    "relative_vorticity_area_mean",
    "relative_vorticity_p90",
)
FORBIDDEN_TOKENS = ("rain", "precip", "observation", "target", "imd", "truth")
EARTH_RADIUS_M = 6_371_000.0
AVAILABILITY_CLASSES = (
    "STATIC",
    "FORECAST_TIME",
    "DERIVED_FORECAST_TIME",
    "OBSERVATION_TARGET",
    "FORBIDDEN_FOR_INFERENCE",
)


FEATURE_REGISTRY = (
    {"name": "u850", "availability": "FORECAST_TIME", "regime_allowed": True},
    {"name": "v850", "availability": "FORECAST_TIME", "regime_allowed": True},
    {"name": "q700", "availability": "FORECAST_TIME", "regime_allowed": True},
    {"name": "z500", "availability": "FORECAST_TIME", "regime_allowed": True},
    {"name": "mslp", "availability": "FORECAST_TIME", "regime_allowed": True},
    {"name": "pwat", "availability": "FORECAST_TIME", "regime_allowed": True},
    *(
        {"name": name, "availability": "DERIVED_FORECAST_TIME", "regime_allowed": True}
        for name in FEATURE_NAMES
    ),
    {"name": "latitude", "availability": "STATIC", "regime_allowed": False},
    {"name": "longitude", "availability": "STATIC", "regime_allowed": False},
    {"name": "elevation", "availability": "STATIC", "regime_allowed": False, "status": "future_source_required"},
    {"name": "terrain_gradient", "availability": "STATIC", "regime_allowed": False, "status": "future_source_required"},
    {"name": "distance_to_coast", "availability": "STATIC", "regime_allowed": False, "status": "future_source_required"},
    {"name": "district_membership", "availability": "STATIC", "regime_allowed": False, "status": "future_source_required"},
    {"name": "imd_observed_rainfall", "availability": "OBSERVATION_TARGET", "regime_allowed": False},
    {"name": "future_valid_observed_temperature", "availability": "FORBIDDEN_FOR_INFERENCE", "regime_allowed": False},
    {"name": "future_valid_observed_humidity", "availability": "FORBIDDEN_FOR_INFERENCE", "regime_allowed": False},
)


@dataclass(frozen=True)
class StaticGeographyInterface:
    """Typed placeholder; unavailable geography stays ``None``, never fabricated."""

    latitude: np.ndarray
    longitude: np.ndarray
    elevation_m: np.ndarray | None = None
    terrain_gradient: np.ndarray | None = None
    distance_to_coast_km: np.ndarray | None = None
    district_membership: np.ndarray | None = None

    def __post_init__(self) -> None:
        latitude = np.asarray(self.latitude, dtype=np.float64)
        longitude = np.asarray(self.longitude, dtype=np.float64)
        if latitude.ndim != 1 or longitude.ndim != 1:
            raise ValueError("static coordinate interfaces must be one-dimensional")
        if not np.isfinite(latitude).all() or not np.isfinite(longitude).all():
            raise ValueError("static coordinates must be finite")
        shape = (latitude.size, longitude.size)
        for name in (
            "elevation_m",
            "terrain_gradient",
            "distance_to_coast_km",
            "district_membership",
        ):
            value = getattr(self, name)
            if value is not None and np.asarray(value).shape != shape:
                raise ValueError(f"{name} does not align with the target grid")
        object.__setattr__(self, "latitude", latitude)
        object.__setattr__(self, "longitude", longitude)


def validate_feature_registry() -> None:
    if any(item["availability"] not in AVAILABILITY_CLASSES for item in FEATURE_REGISTRY):
        raise ValueError("feature registry contains an unknown availability class")
    allowed = [item for item in FEATURE_REGISTRY if item["regime_allowed"]]
    if any(item["availability"] not in {"FORECAST_TIME", "DERIVED_FORECAST_TIME"} for item in allowed):
        raise ValueError("regime classifier admits a non-forecast-time feature")


def validate_temporal_roles(train_year: int, validation_year: int, test_year: int) -> None:
    if (train_year, validation_year, test_year) != (2017, 2018, 2019):
        raise ValueError("Phase 2A temporal roles are frozen as 2017/2018/2019")
    if len({train_year, validation_year, test_year}) != 3:
        raise ValueError("temporal roles overlap")


def validate_forecast_feature_schema(names: Iterable[str]) -> None:
    names = tuple(names)
    if names != FEATURE_NAMES:
        raise ValueError("regime feature schema does not match the frozen Phase 2A schema")
    forbidden = [name for name in names if any(token in name.lower() for token in FORBIDDEN_TOKENS)]
    if forbidden:
        raise ValueError(f"future/target-like regime features are forbidden: {forbidden}")


def _area_mean(field: np.ndarray, latitude: np.ndarray) -> float:
    weights = np.cos(np.deg2rad(latitude))[:, None]
    return float(np.sum(field * weights) / (np.sum(weights) * field.shape[1]))


def relative_vorticity(
    u850: np.ndarray,
    v850: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
) -> np.ndarray:
    """Return spherical relative vorticity, dv/dx - du/dy, in s^-1."""

    u850 = np.asarray(u850, dtype=np.float64)
    v850 = np.asarray(v850, dtype=np.float64)
    latitude = np.asarray(latitude, dtype=np.float64)
    longitude = np.asarray(longitude, dtype=np.float64)
    if u850.shape != v850.shape or u850.shape != (latitude.size, longitude.size):
        raise ValueError("wind fields and context coordinates do not align")
    if not np.isfinite(u850).all() or not np.isfinite(v850).all():
        raise ValueError("wind fields contain non-finite values")
    phi = np.deg2rad(latitude)
    lam = np.deg2rad(longitude)
    dv_dlambda = np.gradient(v850, lam, axis=1, edge_order=2)
    du_dphi = np.gradient(u850, phi, axis=0, edge_order=2)
    return dv_dlambda / (EARTH_RADIUS_M * np.cos(phi)[:, None]) - du_dphi / EARTH_RADIUS_M


def extract_regime_features(
    atmosphere: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
) -> np.ndarray:
    """Extract one interpretable feature vector from one c00 forecast lead."""

    validate_forecast_feature_schema(FEATURE_NAMES)
    atmosphere = np.asarray(atmosphere, dtype=np.float64)
    if atmosphere.shape != (len(ATMOSPHERIC_VARIABLES), latitude.size, longitude.size):
        raise ValueError("expected atmosphere dimensions [variable, latitude, longitude]")
    if not np.isfinite(atmosphere).all() or (atmosphere <= -999).any():
        raise ValueError("atmospheric predictor bundle is incomplete")
    u850, v850, q700, z500, mslp, pwat = atmosphere
    speed = np.hypot(u850, v850)
    vorticity = relative_vorticity(u850, v850, latitude, longitude)
    values = np.asarray(
        [
            _area_mean(pwat, latitude),
            _area_mean(q700, latitude),
            _area_mean(u850, latitude),
            _area_mean(v850, latitude),
            _area_mean(speed, latitude),
            _area_mean(pwat * speed, latitude),
            _area_mean(mslp, latitude),
            float(np.min(mslp)),
            float(np.max(mslp) - np.min(mslp)),
            _area_mean(z500, latitude),
            _area_mean(vorticity, latitude),
            float(np.percentile(vorticity, 90)),
        ],
        dtype=np.float64,
    )
    if not np.isfinite(values).all():
        raise ValueError("derived regime features contain non-finite values")
    return values


@dataclass(frozen=True)
class TrainingOnlyPseudoLabeler:
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    low_score_threshold: float
    active_score_threshold: float
    fitted_year: int = 2017

    @classmethod
    def fit(cls, features: np.ndarray, *, fitted_year: int = 2017):
        if fitted_year != 2017:
            raise ValueError("Phase 2A pseudo-label thresholds must be fit on 2017 only")
        features = _validate_feature_matrix(features)
        mean = np.mean(features, axis=0)
        scale = np.std(features, axis=0)
        scale[scale == 0] = 1.0
        standardized = (features - mean) / scale
        low_score = _low_score(standardized)
        low_threshold = float(np.quantile(low_score, 0.75))
        not_low = low_score < low_threshold
        if not not_low.any():
            raise ValueError("pseudo-label fit produced no non-low cases")
        active_threshold = float(np.median(_active_score(standardized)[not_low]))
        return cls(mean, scale, low_threshold, active_threshold, fitted_year)

    def transform(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        features = _validate_feature_matrix(features)
        standardized = (features - self.feature_mean) / self.feature_scale
        low_score = _low_score(standardized)
        active_score = _active_score(standardized)
        labels = np.full(features.shape[0], 1, dtype=np.int64)
        low = low_score >= self.low_score_threshold
        labels[low] = 2
        labels[~low & (active_score >= self.active_score_threshold)] = 0
        return labels, low_score, active_score

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "fitted_year": self.fitted_year,
            "feature_names": list(FEATURE_NAMES),
            "feature_mean": self.feature_mean.tolist(),
            "feature_scale": self.feature_scale.tolist(),
            "low_score_threshold": self.low_score_threshold,
            "active_score_threshold": self.active_score_threshold,
            "regime_names": list(REGIME_NAMES),
        }

    @classmethod
    def from_dict(cls, value: dict):
        if value.get("feature_names") != list(FEATURE_NAMES) or value.get("fitted_year") != 2017:
            raise ValueError("pseudo-label artifact schema or training year is invalid")
        return cls(
            np.asarray(value["feature_mean"], dtype=np.float64),
            np.asarray(value["feature_scale"], dtype=np.float64),
            float(value["low_score_threshold"]),
            float(value["active_score_threshold"]),
            int(value["fitted_year"]),
        )


def _validate_feature_matrix(features: np.ndarray) -> np.ndarray:
    validate_forecast_feature_schema(FEATURE_NAMES)
    features = np.asarray(features, dtype=np.float64)
    if features.ndim != 2 or features.shape[1] != len(FEATURE_NAMES):
        raise ValueError("invalid regime feature matrix shape")
    if not np.isfinite(features).all():
        raise ValueError("regime feature matrix contains non-finite values")
    return features


def _low_score(z: np.ndarray) -> np.ndarray:
    index = {name: FEATURE_NAMES.index(name) for name in FEATURE_NAMES}
    return (
        -z[:, index["mslp_minimum"]]
        + z[:, index["mslp_range"]]
        + z[:, index["relative_vorticity_p90"]]
        + z[:, index["pwat_area_mean"]]
    ) / 4.0


def _active_score(z: np.ndarray) -> np.ndarray:
    index = {name: FEATURE_NAMES.index(name) for name in FEATURE_NAMES}
    return (
        z[:, index["pwat_area_mean"]]
        + z[:, index["q700_area_mean"]]
        + z[:, index["wind_speed_area_mean"]]
        + z[:, index["moisture_transport_area_mean"]]
    ) / 4.0


@dataclass(frozen=True)
class SafeLogisticRegimeClassifier:
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    coefficients: np.ndarray
    intercepts: np.ndarray
    classes: np.ndarray

    @classmethod
    def fit(cls, features: np.ndarray, labels: np.ndarray):
        features = _validate_feature_matrix(features)
        labels = np.asarray(labels, dtype=np.int64)
        if set(np.unique(labels)) != {0, 1, 2}:
            raise ValueError("classifier training requires all three frozen regimes")
        mean = np.mean(features, axis=0)
        scale = np.std(features, axis=0)
        scale[scale == 0] = 1.0
        normalized = (features - mean) / scale
        estimator = LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            random_state=26080,
            solver="lbfgs",
        ).fit(normalized, labels)
        return cls(
            mean,
            scale,
            np.asarray(estimator.coef_, dtype=np.float64),
            np.asarray(estimator.intercept_, dtype=np.float64),
            np.asarray(estimator.classes_, dtype=np.int64),
        )

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        features = _validate_feature_matrix(features)
        logits = ((features - self.feature_mean) / self.feature_scale) @ self.coefficients.T
        logits += self.intercepts
        logits -= np.max(logits, axis=1, keepdims=True)
        exponent = np.exp(logits)
        probability = exponent / np.sum(exponent, axis=1, keepdims=True)
        if not np.allclose(probability.sum(axis=1), 1.0, rtol=0, atol=1e-12):
            raise ValueError("regime probabilities do not sum to one")
        return probability

    def predict(self, features: np.ndarray) -> np.ndarray:
        probability = self.predict_proba(features)
        return self.classes[np.argmax(probability, axis=1)]

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "format": "safe-json-multinomial-logistic-regression",
            "feature_names": list(FEATURE_NAMES),
            "regime_names": list(REGIME_NAMES),
            "feature_mean": self.feature_mean.tolist(),
            "feature_scale": self.feature_scale.tolist(),
            "coefficients": self.coefficients.tolist(),
            "intercepts": self.intercepts.tolist(),
            "classes": self.classes.tolist(),
            "random_state": 26080,
            "unsafe_pickle_required": False,
        }

    @classmethod
    def from_dict(cls, value: dict):
        if value.get("format") != "safe-json-multinomial-logistic-regression":
            raise ValueError("unsupported safe regime artifact format")
        if value.get("feature_names") != list(FEATURE_NAMES):
            raise ValueError("regime model feature schema mismatch")
        model = cls(
            np.asarray(value["feature_mean"], dtype=np.float64),
            np.asarray(value["feature_scale"], dtype=np.float64),
            np.asarray(value["coefficients"], dtype=np.float64),
            np.asarray(value["intercepts"], dtype=np.float64),
            np.asarray(value["classes"], dtype=np.int64),
        )
        if model.coefficients.shape != (3, len(FEATURE_NAMES)):
            raise ValueError("regime model coefficient dimensions are invalid")
        if model.intercepts.shape != (3,) or model.classes.tolist() != [0, 1, 2]:
            raise ValueError("regime model class metadata is invalid")
        return model
