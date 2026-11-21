"""Terrain and water grids for the digital flood sandbox (docs/sandbox).

FABDEM (Copernicus GLO-30 with forests and buildings removed) averaged to a regular grid, and JRC Global Surface Water occurrence on the same grid.
Writes docs/sandbox/grid.json (--zone region) or docs/sandbox/grid_breach.json (--zone breach).
USE: python scripts/sandbox_grid.py --project my-ee-project [--zone breach]
"""
import argparse
import json
from pathlib import Path

import ee
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# region: the whole monitor box at about 275 m (map view); breach: a close-up around Cara de Gato at about 110 m (3D view)
ZONES = {"region": ([-75.3, 7.9, -74.3, 9.0], 0.0025, "grid.json"),
         "breach": ([-75.03, 8.08, -74.68, 8.43], 0.001, "grid_breach.json")}
BREACH = [-74.768, 8.212]            # the gap seen on Sentinel-2 (open 25 Sep 2021, new embankment by 12 Apr 2024)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--zone", choices=ZONES, default="region")
    a = p.parse_args()
    BOX, STEP, name = ZONES[a.zone]
    ee.Initialize(project=a.project)
    box = ee.Geometry.Rectangle(BOX, proj="EPSG:4326", geodesic=False)
    tr = [STEP, 0, BOX[0], 0, -STEP, BOX[3]]
    fab = ee.ImageCollection("projects/sat-io/open-datasets/FABDEM").filterBounds(box)
    dem = (fab.mosaic().select(0).rename("z").setDefaultProjection(fab.first().projection())   # a mosaic has no projection of its own
           .reduceResolution(ee.Reducer.mean(), maxPixels=128).reproject("EPSG:4326", tr))
    occ = (ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").unmask(0).toFloat().rename("occ")   # float so the -9999 default fits
           .reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject("EPSG:4326", tr))
    # MERIT Hydro upstream area (km2), the largest value in each grid cell, to find the river channels
    upa = (ee.Image("MERIT/Hydro/v1_0_1").select("upa").toFloat()
           .reduceResolution(ee.Reducer.max(), maxPixels=1024).reproject("EPSG:4326", tr))
    nx, ny = round((BOX[2] - BOX[0]) / STEP), round((BOX[3] - BOX[1]) / STEP)
    rows = []
    # sampleRectangle is limited to 262,144 cells, so read in horizontal strips
    for k in range(0, ny, 110):
        y1 = BOX[3] - k * STEP
        y0 = max(BOX[1], y1 - 110 * STEP)
        strip = ee.Geometry.Rectangle([BOX[0], y0, BOX[2], y1], proj="EPSG:4326", geodesic=False)
        d = dem.addBands(occ).addBands(upa).sampleRectangle(strip, defaultValue=-9999).getInfo()["properties"]
        rows.append((np.array(d["z"], float), np.array(d["occ"], float), np.array(d["upa"], float)))
        print("strip", k, np.array(d["z"]).shape, flush=True)
    z = np.vstack([r[0] for r in rows])[:ny, :nx]
    occ = np.vstack([r[1] for r in rows])[:ny, :nx]
    upa = np.vstack([r[2] for r in rows])[:ny, :nx]
    out = ROOT / "docs" / "sandbox"
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(json.dumps({
        "box": BOX, "step": STEP, "nx": int(z.shape[1]), "ny": int(z.shape[0]), "breach": BREACH,
        "z": np.round(z, 2).ravel().tolist(), "occ": np.round(occ).astype(int).ravel().tolist(),
        "upa": np.round(np.clip(upa, 0, None)).astype(int).ravel().tolist()},
        separators=(",", ":")), encoding="utf-8")
    print("grid", z.shape, "z p2/p50/p98", np.percentile(z[z > -9999], [2, 50, 98]).round(1), "missing", int((z <= -9999).sum()))


if __name__ == "__main__":
    main()
