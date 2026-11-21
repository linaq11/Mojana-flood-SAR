"""Monthly width of the Cara de Gato breach from Sentinel-2 (PREREGISTRATION_SIMULATION.md, clarification on the breach width).

1. Dike line: digitized by eye on the last scene with less than 20% cloud within 1 km of the breach before
   27 August 2021, one point every 10 m, kept within 1.5 km (along the line) of the point nearest to the mapped breach.
2. Width: on every Sentinel-2 L2A scene from August 2021 to December 2024 with less than 20% cloud within 1 km,
   the longest run of open water (MNDWI above 0) along that line, in metres. Monthly value: median of the scenes.
Writes data/breach/dike_line.csv, data/breach/breach_scenes.csv and data/breach/breach_monthly.csv.
USE: python scripts/breach_width.py --project my-ee-project
"""
import argparse
from pathlib import Path

import ee
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "breach"
BREACH = [-74.768, 8.212]            # gap seen on Sentinel-2 (open 25 Sep 2021, closed by 12 Apr 2024); PREREGISTRATION_SIMULATION.md, deviation
UTM = "EPSG:32618"
HALF = 1500                          # metres of dike to each side of the breach


def cloud_share(im, area):
    scl = im.select("SCL")
    bad = scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10))     # cloud shadow, cloud medium and high, cirrus
    return im.set("cloud", bad.reduceRegion(ee.Reducer.mean(), area, 20).get("SCL"))


def mndwi(im):
    return im.normalizedDifference(["B3", "B11"]).toFloat().rename("w")    # B11 is 20 m, resampled to the 10 m grid below; float so the -9 default fits


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    a = p.parse_args()
    ee.Initialize(project=a.project)
    OUT.mkdir(parents=True, exist_ok=True)
    pt = ee.Geometry.Point(BREACH)
    near = pt.buffer(1000)
    s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(pt)
          .map(lambda im: cloud_share(im, near)).filter(ee.Filter.lt("cloud", 0.2)))

    # 1. dike line, digitized by eye on the last clear scene before the break (the brown strip of the dike on a
    #    true-colour image, data/breach/pre_break_rgb.png). An automatic edge search was tried first and failed
    #    (it jumped to the right bank where the floodplain there was flooded), so it is not used.
    pre = s2.filterDate("2021-01-01", "2021-08-27").sort("system:time_start", False).first()
    pre_date = ee.Date(pre.get("system:time_start")).format("YYYY-MM-dd").getInfo()
    lon0, lat0, lon1, lat1, size = -74.79054505337515, 8.234497164878738, -74.74538308921272, 8.189511480115527, 900
    px = [(35, 890), (90, 790), (130, 700), (180, 610), (225, 545), (275, 490), (330, 462), (400, 455), (460, 458),
          (520, 478), (580, 500), (640, 440), (690, 320), (745, 220), (800, 120)]     # (column, row) on that image
    lonlat = [[lon0 + cx / size * (lon1 - lon0), lat0 - ry / size * (lat0 - lat1)] for cx, ry in px]
    xy = np.array(ee.Geometry.LineString(lonlat).transform(UTM, 1).coordinates().getInfo())
    seg = np.hypot(*np.diff(xy, axis=0).T)
    along = np.r_[0, np.cumsum(seg)]
    t = np.arange(0, along[-1], 10.0)                # one point every 10 m
    line = pd.DataFrame({"x": np.interp(t, along, xy[:, 0]), "y": np.interp(t, along, xy[:, 1]), "along": t})
    c = pt.transform(UTM, 1).coordinates().getInfo()
    k = int(np.argmin(np.hypot(line.x - c[0], line.y - c[1])))
    line = line[(line.along - line.along[k]).abs() <= HALF].reset_index(drop=True)
    line["along"] -= line.along.iloc[0]
    line.to_csv(OUT / "dike_line.csv", index=False)
    print("dike line from", pre_date, len(line), "points,", round(line.along.iloc[-1]), "m long; nearest point",
          round(float(np.hypot(line.x - c[0], line.y - c[1]).min())), "m from the mapped breach")

    # 2. longest run of water along the line on every clear scene
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([x, y], UTM), {"i": i}) for i, (x, y) in enumerate(zip(line.x, line.y))])
    step = float(np.median(np.diff(line.along)))
    post = s2.filterDate("2021-08-27", "2025-01-01")
    ids = post.aggregate_array("system:index").getInfo()
    rows = []
    for sid in ids:
        im = post.filter(ee.Filter.eq("system:index", sid)).first()
        v = mndwi(im).reduceRegions(fc, ee.Reducer.first(), 10, UTM).aggregate_array("first").getInfo()
        wet = np.array([x is not None and x > 0 for x in v])
        runs = np.diff(np.r_[0, wet.astype(int), 0])
        lengths = np.flatnonzero(runs == -1) - np.flatnonzero(runs == 1)
        rows.append({"scene": sid, "date": sid[:8], "width_m": float(lengths.max() * step) if len(lengths) else 0.0,
                     "points_valid": int(sum(x is not None for x in v))})
        print(rows[-1], flush=True)
    d = pd.DataFrame(rows)
    d["date"] = pd.to_datetime(d.date)
    d.to_csv(OUT / "breach_scenes.csv", index=False)
    m = d.groupby(d.date.dt.to_period("M")).width_m.median()
    full = pd.period_range("2021-08", "2024-12", freq="M")
    mm = pd.DataFrame({"month": full.astype(str), "width_m": m.reindex(full).values})
    mm["measured"] = mm.width_m.notna()
    mm["width_m"] = mm.width_m.ffill()               # months without a clear scene take the previous width
    mm.to_csv(OUT / "breach_monthly.csv", index=False)
    print(mm.to_string(index=False))


if __name__ == "__main__":
    main()
