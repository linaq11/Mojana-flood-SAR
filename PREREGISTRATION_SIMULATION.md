# Preregistration: simulating the La Mojana flood after the Cara de Gato breach

Written on 2026-11-20, before any simulation was run and before the gauge series were compared with the radar maps. Only the four gauge files and their completeness (below) had been looked at.

## Question

Can a two-dimensional flood model driven by the observed level of the Cauca River reproduce the monthly flood extent that Sentinel-1 mapped in La Mojana after the dike broke on 27 August 2021, and does the breach explain that flood?

## Data, fixed in advance

* **River level.** IDEAM, daily mean level (DHIME, "Nivel medio diario"), 1 January 2021 to 31 December 2024, stations Las Flores (25027270, upstream of the breach), La Raya (25027910), Achí (25027160) and Tres Cruces (25027640) downstream. Days available: 1,461, 1,460, 1,459 and 1,345 of 1,461. The gap at Tres Cruces (2 January to 27 April 2022) is filled by linear regression on Achí fitted on the other days, and the fit is reported. The files are not redistributed (IDEAM terms); the code that reads them is.
* **Terrain.** FABDEM, the same as the sandbox, at the 275 m regional grid. The dike crest is the highest FABDEM value at 30 m within each grid cell along the left bank, so the embankment is not averaged away.
* **Breach.** Location: the OpenStreetMap feature "Caregato" (8.1553° N, 74.7903° W), moved to the nearest dike cell. Dates: open from 27 August 2021, closed in February 2024, open again from 6 May 2024 (press reports cited in the README). Width: measured once a month on cloud-free Sentinel-2 or Planet images; months without a clear image take the previous width.
* **Rain and evaporation.** ERA5-Land daily totals over the grid. No infiltration (soils of the floodplain taken as saturated), stated as a limitation.
* **Observed flood.** The monthly Sentinel-1 flood maps of this repository (−18 dB), aggregated to the 275 m grid (a cell is flooded if at least half of its 30 m cells are).

## Converting gauge readings to metres above sea level

Gauge readings are centimetres on each station's staff, not elevations. Two routes, in this order:

1. **Official datum.** The elevation of each gauge's zero is requested from IDEAM. If it arrives before the calibration is run, it is used.
2. **SWOT altimetry.** Water surface elevations from SWOT river nodes within 2 km of each gauge, 2023 to 2024, are matched to the gauge reading of the same day. The datum is the median of (SWOT elevation minus gauge reading). It is accepted if the standard deviation of those differences is 0.30 m or less with at least 8 matched days; otherwise the station is not converted.
3. **Fallback.** Without a datum, the river is driven by its level relative to normal: the gauge reading minus its median over 2021, added to the normal river level of the sandbox (running median of FABDEM along the channel). This is declared as a deviation if used.

## Model

The local inertial equations (Bates et al., 2010), run with LISFLOOD-FP if it can be built on this machine, otherwise with this repository's own implementation of the same equations (the one in the sandbox), declared as a deviation. The river cells take a water level interpolated along the channel between the stations on each day; the edges of the grid drain freely.

**One parameter is calibrated:** Manning's n of the floodplain, among 0.03, 0.05, 0.08 and 0.12, chosen by the highest median monthly Critical Success Index (CSI) from August 2021 to December 2022. Everything else stays as stated here.

## Tests

* **H1, the model reproduces the flood.** In the test period, January 2023 to December 2024, the median monthly CSI between simulated and observed flood is 0.5 or more, and the Spearman correlation between simulated and observed monthly flooded area is 0.7 or more. Both are needed.
* **H2, the breach matters.** A run with the dike closed for the whole period gives a lower median monthly CSI than the run with the breach, from September 2021 to January 2024. The difference is reported with a 95% interval from resampling months.

Simulated flood: water deeper than 0.1 m outside permanent water (JRC occurrence of 90% or more), at the end of each month and as the share of days flooded in the month; both are reported, the end-of-month map is the one tested. CSI = hits / (hits + misses + false alarms).

## Known limits, stated before seeing results

* FABDEM's vertical error in flat terrain is of the order of a metre, the same order as flood depths.
* Radar misses water under vegetation, so misses near forest and floating vegetation are expected and are not corrected.
* No infiltration, no San Jorge River inflow, no bathymetry of the channel.

## What is reported

Both hypotheses, all months, the calibrated n, the gauge conversion that was used and any deviation from this document, including failure.

## Clarification, 2026-11-20, before any SWOT value was read

SWOT nodes are taken from the SWOT River Database (SWORD) version 16 and read through the Hydrocron API, collection `SWOT_L2_HR_RiverSP_2.0`, whose node identifiers follow SWORD v16. Only observations with `node_q` of 0 or 1 (good or suspect) and a real `wse` value (not the fill value) are used. Each gauge is matched to the nodes within 2 km, all of them, on the same calendar day; the datum is the median over all matched node-days of that gauge.

## Clarification, 2026-11-20, before measuring the breach width

The breach width is measured along a line digitized on the dike crest on the last cloud-free Sentinel-2 image before 27 August 2021, 1.5 km to each side of the dike cell nearest to the mapped breach. On every Sentinel-2 L2A scene with less than 20% cloud within 1 km of the breach (scene classification), the width is the length of the longest run of open water (MNDWI above 0) along that line. The monthly width is the median of the month's scenes. Months without such a scene take the previous width, as stated above. Planet images are used only if a month from August 2021 to December 2024 has no Sentinel-2 value.

## Deviation, 2026-11-20, before any simulation was run: breach location

The OpenStreetMap feature "Caregato" (8.1553° N, 74.7903° W) is not where the dike broke. Sentinel-2 images show the dike intact on 21 August 2021, river water pouring north through it on 25 September 2021, most of the river flowing through the gap on 12 February 2022 and a new embankment across it on 12 April 2024, at the apex of the Cauca bend about 6.4 km north-north-east of that point, near 8.212° N, 74.768° W (images in `data/breach/`). The simulation and the breach-width measurement use this location; the dike line for the width is digitized at it on the 21 August 2021 image. A first width run along the wrong stretch of dike gave widths of 0 to 30 m on almost every scene and is discarded.

## Deviation, 2026-11-20, before any simulation was run: breach width

The width measured as stated (longest run of open water along the pre-break dike line, `scripts/breach_width.py`, results in `data/breach/breach_scenes.csv`) does not measure the gap: once the dike broke, the river cut into the bank and took over the old dike line, so the run of water is 550 to 1,460 m on every scene and stays at about 640 m after the closure. The width is therefore not measured. The simulation opens the breach as one cell of the 275 m grid while it was open, which is the order of the 20 to 300 m reported by the press, and states that the real width is not resolved.
