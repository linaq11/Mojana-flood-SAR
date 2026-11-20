"""Compare Sentinel-1 water with Sentinel-2 open water on clear dates (PREREGISTRATION.md).

For every day with Sentinel-2 cloud below 20% over the area, the nearest Sentinel-1 scene within 6 days
is thresholded at -18 dB and compared with MNDWI > 0 on a regular grid of about 1.2 km, thinned to 5,000 cloud-free cells.
Writes data/s2_check.csv (one row per date) and prints the pooled agreement.

USE: python scripts/check_s2.py --project my-ee-project
"""
import argparse
from pathlib import Path

import ee
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BOX = [-75.3, 7.9, -74.3, 9.0]
CLOUD = [3, 8, 9, 10, 11]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    a = p.parse_args()
    ee.Initialize(project=a.project)
    box = ee.Geometry.Rectangle(BOX)
    global GRID
    step = 0.011                                    # about 1.2 km: 91 x 100 grid points over the area
    GRID = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([lon, lat]))
                                 for lon in np.arange(BOX[0] + step / 2, BOX[2], step)
                                 for lat in np.arange(BOX[1] + step / 2, BOX[3], step)])
    flat = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003")).lte(5)
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(box).filterDate("2020-01-01", "2026-01-01")
    s1 = (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(box).filter(ee.Filter.eq("instrumentMode", "IW"))
          .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV")).select("VV"))
    days = sorted(set(s2.aggregate_array("system:time_start").map(lambda t: ee.Date(t).format("YYYY-MM-dd")).getInfo()))
    rows = []
    for i, d in enumerate(days):
        day = ee.Date(d)
        img = s2.filterDate(day, day.advance(1, "day")).mosaic()
        scl = img.select("SCL")
        cover = scl.mask().reduceRegion(ee.Reducer.mean(), box, 500, maxPixels=1e9).get("SCL")
        cloudy = scl.remap(CLOUD, [1] * len(CLOUD), 0).unmask(1)
        frac = ee.Dictionary({"c": cloudy.reduceRegion(ee.Reducer.mean(), box, 500, maxPixels=1e9).get("remapped"),
                              "v": cover}).getInfo()
        if frac["c"] is None or frac["v"] is None or frac["v"] < 0.8 or frac["c"] >= 0.2:
            continue
        near = s1.filterDate(day.advance(-6, "day"), day.advance(7, "day")).map(
            lambda im: im.set("gap", ee.Number(im.date().difference(day, "day")).abs())).sort("gap")
        if near.size().getInfo() == 0:
            continue
        sar = near.first()
        gap = sar.get("gap").getInfo()
        sar_date = sar.date().format("YYYY-MM-dd").getInfo()
        sar_day = near.filterDate(sar.date().advance(-12, "hour"), sar.date().advance(12, "hour")).mosaic()
        mndwi = img.normalizedDifference(["B3", "B11"])
        clear = cloudy.Not().And(flat).And(sar_day.mask())
        stack = ee.Image.cat(sar_day.lt(-18).rename("sar"), mndwi.gt(0).rename("opt")).updateMask(clear)
        # regular grid, then keep every k-th cloud-free cell so that at most 5,000 remain
        v = stack.sampleRegions(GRID, scale=30, tileScale=8).reduceColumns(ee.Reducer.toList(2), ["sar", "opt"]).get("list").getInfo()
        if not v:
            continue
        arr = np.array(v, dtype=int)
        if len(arr) > 5000:
            arr = arr[np.linspace(0, len(arr) - 1, 5000).round().astype(int)]
        s, o = arr[:, 0], arr[:, 1]
        tp, fp, fn = int(((s == 1) & (o == 1)).sum()), int(((s == 1) & (o == 0)).sum()), int(((s == 0) & (o == 1)).sum())
        rows.append({"s2_date": d, "s1_date": sar_date, "gap_days": gap, "cloud": round(frac["c"], 3), "n": len(arr),
                     "tp": tp, "fp": fp, "fn": fn, "tn": int(len(arr) - tp - fp - fn),
                     "agreement": round(float((s == o).mean()), 4),
                     "f1_water": round(2 * tp / (2 * tp + fp + fn), 4) if tp + fp + fn else None})
        print(rows[-1], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data" / "s2_check.csv", index=False)
    if len(df):
        tp, fp, fn = df.tp.sum(), df.fp.sum(), df.fn.sum()
        print(f"dates {len(df)}, pooled F1 water {2 * tp / (2 * tp + fp + fn):.3f}, "
              f"median F1 by date {df.f1_water.median():.3f}, pooled agreement {(df.tp.sum() + df.tn.sum()) / df.n.sum():.3f}")


if __name__ == "__main__":
    main()
