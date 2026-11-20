"""Monthly water and flood extent over La Mojana from Sentinel-1 (PREREGISTRATION.md).

Writes data/mojana_monthly.csv with, for each month from January 2020 to December 2025, the number
of Sentinel-1 scenes and the water and flood areas (km2) for VV thresholds of -16, -18 and -20 dB.

USE: python scripts/mojana_series.py --project my-ee-project
"""
import argparse
from pathlib import Path

import ee
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BOX = [-75.3, 7.9, -74.3, 9.0]
THRESHOLDS = (-16, -18, -20)
REF_START, REF_END = "2020-01-01", "2021-08-01"     # before the break of 27 August 2021


def s1(box):
    return (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(box)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV")).select("VV"))


def months(start="2020-01", end="2025-12"):
    return [p.strftime("%Y-%m-01") for p in pd.period_range(start, end, freq="M").to_timestamp()]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    a = p.parse_args()
    ee.Initialize(project=a.project)
    box = ee.Geometry.Rectangle(BOX)
    col = s1(box)
    flat = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003")).lte(5)
    permanent = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").gte(90).unmask(0)
    area = ee.Image.pixelArea().divide(1e6)

    def monthly(m):
        start = ee.Date(m)
        return col.filterDate(start, start.advance(1, "month"))

    # reference water before the break: water in at least half of the reference months, per threshold
    ref_months = [m for m in months("2020-01", "2021-07")]
    ref = {}
    for t in THRESHOLDS:
        maps = [monthly(m).median().lt(t) for m in ref_months]
        ref[t] = ee.ImageCollection(maps).mean().gte(0.5).unmask(0)

    rows = []
    for m in months():
        c = monthly(m)
        n = c.size().getInfo()
        row = {"month": m[:7], "scenes": n}
        if n:
            vv = c.median()
            bands = []
            for t in THRESHOLDS:
                water = vv.lt(t).And(flat).And(permanent.Not())
                flood = water.And(ref[t].Not())
                bands += [area.updateMask(water).rename(f"water_{-t}"), area.updateMask(flood).rename(f"flood_{-t}")]
            s = ee.Image.cat(bands).reduceRegion(ee.Reducer.sum(), box, 30, maxPixels=1e10, tileScale=8).getInfo()
            row.update({k: round(v, 2) for k, v in s.items()})
        rows.append(row)
        print(row, flush=True)
    out = ROOT / "data"
    out.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "mojana_monthly.csv", index=False)


if __name__ == "__main__":
    main()
