"""Forecast-time western-disturbance indicator (docs/138): the vorticity maths against an analytic case, and the pure statistics."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml import wd_indicator as wd


def _grid(step=0.5):
    lat = np.arange(10.0, 60.0 + 1e-9, step)
    lon = np.arange(40.0, 100.0 + 1e-9, step)
    return lat, lon


def test_a_height_minimum_gives_cyclonic_vorticity_and_a_ridge_anticyclonic():
    lat, lon = _grid()
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    trough = 5600.0 - 150.0 * np.exp(-(((la - 32.0) / 6.0) ** 2 + ((lo - 70.0) / 8.0) ** 2))
    ridge = 5600.0 + 150.0 * np.exp(-(((la - 32.0) / 6.0) ** 2 + ((lo - 70.0) / 8.0) ** 2))
    assert wd.index_from_z500(trough, lat, lon) > 0 > wd.index_from_z500(ridge, lat, lon)
    assert wd.index_from_z500(trough, lat, lon) == pytest.approx(-wd.index_from_z500(ridge, lat, lon), rel=1e-9)     # the maths is linear and odd


def test_the_vorticity_matches_the_analytic_laplacian_of_a_smooth_field():
    lat, lon = _grid(0.25)
    la, lo = np.meshgrid(np.deg2rad(lat), np.deg2rad(lon), indexing="ij")
    amplitude, m, n = 100.0, 3.0, 2.0
    z = amplitude * np.sin(m * la) * np.cos(n * lo)                                    # zonal wavenumber n, meridional m
    zeta = wd.geostrophic_vorticity(z, lat, lon)
    a2 = wd.EARTH_RADIUS_M ** 2
    # analytic spherical Laplacian of sin(m phi) cos(n lambda)
    d_phi_term = (-m * m * np.sin(m * la) * np.cos(la) - m * np.cos(m * la) * np.sin(la)) / np.cos(la)          # (1/cos) d/dphi (cos dZ/dphi) per unit amplitude
    expected_laplacian = amplitude * (d_phi_term - (n * n) * np.sin(m * la) / np.cos(la) ** 2) * np.cos(n * lo) / a2
    expected = wd.GRAVITY / (2 * wd.OMEGA * np.sin(la)) * expected_laplacian
    inner = (slice(8, -8), slice(8, -8))
    assert np.nanmax(np.abs(zeta[inner] - expected[inner])) < 0.01 * np.nanmax(np.abs(expected[inner]))      # 1 percent of the amplitude at 0.25 degree
    assert np.isnan(zeta[0]).all() and np.isnan(zeta[-1]).all() and np.isnan(zeta[:, 0]).all() and np.isnan(zeta[:, -1]).all()


def test_input_validation_and_box_mean_never_patch_missing_values():
    lat, lon = np.array([10.0, 11.0, 12.0]), np.array([60.0, 61.0, 62.0])
    with pytest.raises(ValueError):
        wd.geostrophic_vorticity(np.zeros((2, 3)), lat, lon)
    with pytest.raises(ValueError):
        wd.geostrophic_vorticity(np.zeros((3, 3)), lat[::-1], lon)
    field = np.arange(9.0).reshape(3, 3)
    assert wd.box_mean(field, lat, lon, (10.0, 12.0, 60.0, 62.0)) == pytest.approx((field * np.cos(np.deg2rad(lat))[:, None]).sum() / (np.cos(np.deg2rad(lat))[:, None] * np.ones(3)).sum())
    field[1, 1] = np.nan
    assert np.isnan(wd.box_mean(field, lat, lon, (10.0, 12.0, 60.0, 62.0))) and np.isnan(wd.box_mean(field, lat, lon, (50.0, 51.0, 60.0, 62.0)))


def test_threshold_is_the_training_upper_tercile_and_flags_are_relative():
    values = np.arange(300, dtype=float)
    cut = wd.upper_tercile(values)
    assert cut["threshold"] == pytest.approx(np.quantile(values, 2 / 3)) and cut["training_cases"] == 300
    assert wd.flag(cut["threshold"], cut) is True and wd.flag(cut["threshold"] - 1e-9, cut) is False and wd.flag(float("nan"), cut) is None
    with pytest.raises(ValueError):
        wd.upper_tercile(np.arange(50, dtype=float))


def _data(n=600, strength=1.0, seed=4):
    rng = np.random.default_rng(seed)
    index = rng.normal(0, 1, n)
    rain = np.maximum(0, 2 + strength * index + rng.normal(0, 2, n))
    clusters = [i // 3 for i in range(n)]
    return index, rain, clusters


def test_group_statistics_gate_and_a_real_association_is_detected_while_noise_is_not():
    index, rain, clusters = _data(strength=1.5)
    cut = wd.upper_tercile(index)
    flagged = np.array([wd.flag(v, cut) for v in index])
    groups = wd.group_statistics(flagged, rain)
    assert groups["flagged"]["cases"] + groups["not_flagged"]["cases"] == len(index) and wd.supported(groups)
    assert groups["flagged"]["mean_rain_mm_per_day"] > groups["not_flagged"]["mean_rain_mm_per_day"]
    boot = wd.bootstrap(index, flagged, rain, clusters, repeats=300, seed=1)
    assert boot["flagged_minus_not_flagged_mean_rain"]["excludes_zero"] and boot["flagged_minus_not_flagged_mean_rain"]["point"] > 0 and boot["spearman"]["point"] > 0.3
    noise = np.random.default_rng(8).gamma(1.0, 2.0, len(index))
    null = wd.bootstrap(index, flagged, noise, clusters, repeats=300, seed=1)
    low, high = null["flagged_minus_not_flagged_mean_rain"]["interval95"]
    assert low <= 0 <= high
    assert not wd.supported(wd.group_statistics(np.array([True] * 10 + [False] * 100), rain[:110]))


def test_bootstrap_is_deterministic_and_undefined_without_variation():
    index, rain, clusters = _data()
    cut = wd.upper_tercile(index)
    flagged = np.array([wd.flag(v, cut) for v in index])
    assert wd.bootstrap(index, flagged, rain, clusters, repeats=100, seed=2) == wd.bootstrap(index, flagged, rain, clusters, repeats=100, seed=2)
    none = wd.bootstrap(index, flagged, np.ones(len(index)), clusters, repeats=100, seed=2)
    assert none["spearman"]["status"] == "undefined" and none["flagged_minus_not_flagged_mean_rain"]["point"] == 0.0
