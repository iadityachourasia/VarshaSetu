"""HEAD-only availability probe of NOAA GEFS objects for 2021 and 2022 (no body is downloaded).

Run from any directory; writes probe_gefs_result.json beside the current directory. Evidence of the recorded run: docs/artifacts/gefs_2021_2022_head_probe.json (docs/127).
"""
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://noaa-gefs-pds.s3.amazonaws.com"
DATES = ["20210601", "20210615", "20210701", "20210715", "20210801", "20210815", "20210901", "20210915", "20211001",
         "20220601", "20220615", "20220701", "20220715", "20220801", "20220815", "20220901", "20220915", "20221001",
         "20230601"]  # 2023 is a positive control: known complete
# the same key forms the 2023-2025 corpus used
FAMILIES = [
    ("pgrb2sp25", "c00", 27), ("pgrb2sp25", "p01", 27), ("pgrb2sp25", "p04", 27), ("pgrb2sp25", "c00", 75),
    ("pgrb2ap5", "c00", 24), ("pgrb2ap5", "c00", 72), ("pgrb2bp5", "c00", 24), ("pgrb2bp5", "c00", 72),
]


def key(date, family, member, fhr, suffix=""):
    return f"gefs.{date}/00/atmos/{family}/ge{member}.t00z.{family}.f{fhr:03d}{suffix}"


def head(path):
    request = urllib.request.Request(f"{BASE}/{path}", method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, int(response.headers.get("Content-Length", -1)), response.headers.get("Last-Modified")
    except urllib.error.HTTPError as error:
        return error.code, None, None
    except Exception as error:  # network failure is reported, not hidden
        return f"ERR {type(error).__name__}", None, None


def task(args):
    date, family, member, fhr = args
        grid = {"pgrb2sp25": "pgrb2s.0p25", "pgrb2ap5": "pgrb2a.0p50", "pgrb2bp5": "pgrb2b.0p50"}[family]
    k = f"gefs.{date}/00/atmos/{family}/ge{member}.t00z.{grid}.f{fhr:03d}"
    return {"date": date, "family": family, "member": member, "fhr": fhr, "key": k,
            "grib": head(k), "idx": head(k + ".idx")}


jobs = [(d, f, m, h) for d in DATES for (f, m, h) in FAMILIES]
with ThreadPoolExecutor(6) as pool:
    results = list(pool.map(task, jobs))
json.dump(results, open("probe_gefs_result.json", "w"), indent=1)
by_date = {}
for r in results:
    by_date.setdefault(r["date"], []).append(r)
for date, rows in by_date.items():
    ok = sum(1 for r in rows if r["grib"][0] == 200 and r["idx"][0] == 200)
    codes = sorted({str(r["grib"][0]) for r in rows} | {str(r["idx"][0]) for r in rows})
    size = sum(r["grib"][1] or 0 for r in rows if r["grib"][0] == 200)
    print(date, f"{ok}/{len(rows)} complete", codes, f"{size/1e6:.0f} MB (listed objects)")
