"""Monthly flood maps of La Mojana as transparent PNG overlays for the dashboard (threshold -18 dB).

Each PNG paints permanent water, water already present before the break, and new flood water, over a
transparent background, for the box in PREREGISTRATION.md. Writes docs/data/maps/YYYY-MM.png and docs/data/maps.json.
USE: python scripts/monthly_maps.py --project my-ee-project
"""
import argparse
import json
import sys
from pathlib import Path

import ee
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mojana_series import BOX, months, s1  # noqa: E402

T = -18


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--width", type=int, default=1100)
    a = p.parse_args()
    ee.Initialize(project=a.project)
    box = ee.Geometry.Rectangle(BOX)
    col = s1(box)
    flat = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003")).lte(5)
    permanent = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").gte(90).unmask(0)
    ref = ee.ImageCollection([col.filterDate(ee.Date(m), ee.Date(m).advance(1, "month")).median().lt(T)
                              for m in months("2020-01", "2021-07")]).mean().gte(0.5).unmask(0)
    out = ROOT / "docs" / "data" / "maps"
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for m in months():
        c = col.filterDate(ee.Date(m), ee.Date(m).advance(1, "month"))
        if c.size().getInfo() == 0:
            continue
        water = c.median().lt(T).And(flat)
        # 1 = permanent water, 2 = water already present before the break, 3 = new flood
        cls = ee.Image(0).where(water.And(ref), 2).where(water.And(ref.Not()).And(permanent.Not()), 3).where(permanent, 1).selfMask()
        url = cls.visualize(min=1, max=3, palette=["2b6f9e", "7fb6d6", "e0a23a"]).getThumbURL(
            {"region": box, "dimensions": a.width, "format": "png"})
        dst = out / f"{m[:7]}.png"
        dst.write_bytes(requests.get(url, timeout=300).content)
        index.append(m[:7])
        print(m[:7], round(dst.stat().st_size / 1024), "KB", flush=True)
    (ROOT / "docs" / "data" / "maps.json").write_text(json.dumps({"box": BOX, "months": index}), encoding="utf-8")


if __name__ == "__main__":
    main()
