# Preregistration: flood extent from Sentinel-1 for La Mojana (Colombia) and Hurricane Ian (Florida)

Written on 2026-11-19, before any radar image was processed.

## Events

1. **La Mojana, Colombia.** The Cara de Gato dike on the left bank of the Cauca River (San Jacinto del Cauca, Bolívar) broke on 27 August 2021, was closed in February 2024 and broke again on 6 May 2024 (dates from press reports listed in the README). Area: 75.3° W to 74.3° W, 7.9° N to 9.0° N. Period: January 2020 to December 2025, one map per month.
2. **Hurricane Ian, Florida.** Inland flooding of the Peace and Myakka river basins after landfall in late September 2022. Area and dates are fixed, from official sources, before the first image of this event is processed and are added here as a dated note.

## Method, fixed in advance

* **Radar.** Sentinel-1 GRD, IW mode, VV polarization, from the Earth Engine collection `COPERNICUS/S1_GRD` (terrain-corrected, in dB). For La Mojana, the monthly median of all scenes in the month; for Ian, each scene on its own.
* **Water.** VV below −18 dB. The same rule with −16 and −20 dB is run as a sensitivity check.
* **Flood.** Water that is not permanent water. Permanent water is JRC Global Surface Water occurrence of 90% or more. For La Mojana, the reference before the break is the median of the monthly water maps from January 2020 to July 2021, and "flood relative to before the break" is water in a month that was not water in at least half of those reference months.
* **Masks.** Cells with a slope above 5° (SRTM) are left out, because radar shadow on slopes can look like water.

## Check against an independent sensor

On every date with a Sentinel-2 scene that has less than 20% cloud over the area, open water is mapped with MNDWI above 0 on cloud-free cells (scene classification). The radar water map nearest in time, within 6 days, is compared cell by cell on a regular sample of 5,000 cloud-free cells per date. Reported: overall agreement, F1 of the water class and the number of dates. Expectation, stated before computing: an F1 of 0.7 or more for open water. Flooded vegetation, which radar can see as very bright and optical sensors cannot see at all, is a known source of disagreement and is not corrected.

## What is reported

The monthly flooded area of La Mojana in square kilometres, with the dates of the break, the closure and the second break marked on the series; the flood maps; and the agreement with Sentinel-2. All results are reported, including disagreement with the expectation.
