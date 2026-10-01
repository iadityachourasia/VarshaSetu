"""QA maps of the static_geography_v1 artifact (elevation, local relief, distance to coast, zones). Reads the committed JSON only."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[1]
ART = json.loads((ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs/artifacts/static_geography_v1_qa.png"


def grid(key):
    return np.array([[np.nan if v is None else v for v in row] for row in ART["fields"][key]], float)


lat = np.array(ART["grid"]["latitude_centers"])
lon = np.array(ART["grid"]["longitude_centers"])
extent = [lon[0] - 0.125, lon[-1] + 0.125, lat[0] - 0.125, lat[-1] + 0.125]
foot = np.array(ART["fields"]["footprint"])
labels = ["COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER"]
zone = np.full(foot.shape, np.nan)
for k, label in enumerate(labels):
    zone[np.array([[v == label for v in row] for row in ART["fields"]["zone"]])] = k

fig, axes = plt.subplots(2, 2, figsize=(11, 10), constrained_layout=True)
panels = [("Mean elevation (m)", np.where(foot, grid("mean_elevation_m"), np.nan), "terrain"),
          ("Local relief, 3x3 (m)", np.where(foot, grid("local_relief_m"), np.nan), "magma_r"),
          ("Distance to coast (km)", np.where(foot, grid("distance_to_coast_km"), np.nan), "viridis_r")]
for ax, (title, data, cmap) in zip(axes.flat, panels):
    image = ax.imshow(data, origin="lower", extent=extent, cmap=cmap)
    fig.colorbar(image, ax=ax, shrink=0.8)
    ax.set_title(title)
ax = axes.flat[3]
cmap = ListedColormap(["#1b7f8c", "#b5651d", "#7b3f9e", "#d9d9d9"])
ax.imshow(zone, origin="lower", extent=extent, cmap=cmap, vmin=-0.5, vmax=3.5)
counts = ART["zone_cell_counts"]
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in cmap.colors], labels=[f"{l} ({counts[l]})" for l in labels], loc="lower left", fontsize=8)
ax.set_title("Rule-based geographic-forcing zones (protocol v3)")
for ax in axes.flat:
    ax.set_xlabel("Longitude (E)")
    ax.set_ylabel("Latitude (N)")
fig.suptitle("static_geography_v1 QA - GMTED2010 mean 30 arc-second aggregated to 0.25 degrees; IMD land footprint only", fontsize=11)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=110)
print(OUT)
