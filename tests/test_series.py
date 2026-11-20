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
