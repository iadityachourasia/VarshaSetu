"""Local evidence check (needs the gitignored experiment and processed data; results recorded in docs/121).

Does the Track B 51x81 atmosphere grid share Track A's georeferencing (5-30N, 55-95E, 0.5 deg, row 0 = 5N)?

Track A coordinates are stored in its NetCDF files. Track B has no sidecar, so compare seasonal-mean fields: if the grids are
georeferenced identically the pattern correlation is ~1 for the identity alignment and clearly lower for flipped or shifted ones.
"""
import glob
import os
import numpy as np
import scipy.io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "experiments", "recent_historical", "phase4f_payload_acquisition_v1", "atmospheric_qc")
A = os.path.join(ROOT, "data", "processed", "phase2a")


def mean_b(year, field, hour="024"):
    arrays = [np.load(p) for p in glob.glob(os.path.join(B, str(year), "*", f"{field}_f{hour}.npy"))]
    return np.nanmean(np.stack(arrays), axis=0), len(arrays)


def mean_a(year, field, lead_index=0):
    arrays = []
    for path in glob.glob(os.path.join(A, f"{year}-0*", "daily", "atmosphere_context_*.nc")):
        with scipy.io.netcdf_file(path, mmap=False) as handle:
            arrays.append(np.array(handle.variables[field].data[lead_index], dtype=float))
            lat = np.array(handle.variables["latitude"][:])
            lon = np.array(handle.variables["longitude"][:])
    return np.nanmean(np.stack(arrays), axis=0), len(arrays), lat, lon


def corr(x, y):
    x, y = x - x.mean(), y - y.mean()
    return float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum()))


for field in ("pwat", "z500", "mslp", "u850"):
    a, na, lat, lon = mean_a(2018, field)
    b, nb = mean_b(2024, field)
    assert a.shape == b.shape == (51, 81), (a.shape, b.shape)
    results = {"identity (row0 = 5N, col0 = 55E)": corr(a, b), "latitude flipped": corr(a, b[::-1]), "longitude flipped": corr(a, b[:, ::-1]), "both flipped": corr(a, b[::-1, ::-1])}
    for dy in (-2, -1, 1, 2):
        results[f"shifted {dy:+d} rows (0.5 deg each)"] = corr(a[max(dy, 0): 51 + min(dy, 0)], np.roll(b, 0, 0)[max(-dy, 0): 51 - max(dy, 0)])
    for dx in (-2, -1, 1, 2):
        results[f"shifted {dx:+d} cols"] = corr(a[:, max(dx, 0): 81 + min(dx, 0)], b[:, max(-dx, 0): 81 - max(dx, 0)])
    best = max(results, key=results.get)
    print(f"{field}: Track A 2018 mean of {na} files, Track B 2024 mean of {nb} files, A lat {lat[0]}..{lat[-1]} lon {lon[0]}..{lon[-1]}")
    for k, v in results.items():
        print(f"    {v:7.4f}  {k}")
    print("    best:", best)
