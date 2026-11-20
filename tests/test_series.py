import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_every_month_is_present():
    d = pd.read_csv(ROOT / "data" / "mojana_monthly.csv")
    months = pd.period_range("2020-01", "2025-12", freq="M").astype(str).tolist()
    assert d.month.tolist() == months


def test_flood_never_exceeds_water():
    d = pd.read_csv(ROOT / "data" / "mojana_monthly.csv").dropna()
    for t in (16, 18, 20):
        assert (d[f"flood_{t}"] <= d[f"water_{t}"] + 1e-6).all()


def test_events_fall_inside_the_series_and_have_maps_nearby():
    s = json.loads((ROOT / "docs" / "data" / "series.json").read_text())
    months = [r["m"] for r in s["series"]]
    maps = json.loads((ROOT / "docs" / "data" / "maps.json").read_text())["months"]
    for e in s["events"]:
        assert e["m"] in months and e["m"] in maps


def _grid(name="grid.json"):
    return json.loads((ROOT / "docs" / "sandbox" / name).read_text())


def _breach_to_river_cells(g):
    import numpy as np
    upa = np.array(g["upa"]).reshape(g["ny"], g["nx"])
    x = (g["breach"][0] - g["box"][0]) / g["step"]
    y = (g["box"][3] - g["breach"][1]) / g["step"]
    ry, rx = np.nonzero(upa >= 40000)          # the river threshold used by docs/sandbox/index.html
    return float(np.hypot(rx + 0.5 - x, ry + 0.5 - y).min())


def test_sandbox_grids_are_complete_and_the_breach_sits_on_the_cauca():
    for name in ("grid.json", "grid_breach.json"):
        g = _grid(name)
        n = g["nx"] * g["ny"]
        assert len(g["z"]) == len(g["occ"]) == len(g["upa"]) == n, name
        assert min(g["z"]) > -100, name        # no -9999 holes in the terrain
        cell_m = g["step"] * 111_000
        assert _breach_to_river_cells(g) * cell_m <= 2200, name   # within about 2 km of the river channel
