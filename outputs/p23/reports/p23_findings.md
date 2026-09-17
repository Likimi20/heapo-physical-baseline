# P23 — heat-pump efficiency by installation year, the archive, and "below physics"

2026-09-11. Script `p23_vintage.py`, transcript `outputs/p23/logs/p23_run.txt`.

## 1. The archive

Superseded scripts and outputs (P2–P9, P12, P14–P18, P20/P21 scenario scripts, P13 v1)
moved to `history/`, with `history/README.md` saying what superseded each. Only
`__pycache__` was deleted. Live code referenced none of the moved files, except P13's
comparison with v1, whose path was updated. `p_notebook.py` shows P5/P7/P8/P9 as missing
until the closing rebuild.

## 2. Vintage — implemented

**Sources, notebook-verified.** FAWA 2004 fleet means for 1996–2003 installations are air
2.7 and ground 3.5. The OST P+I 2020 table's totals for ~2015–19 installations are air 3.4
and ground 4.6. So a 1999 unit delivers **0.794 (air) / 0.761 (ground)** of a 2017 unit;
against OST 2021/22 WNG the band runs to 0.871 / 0.827. FAWA found **no ageing loss over
9 operating years**, so this is technology vintage, not wear.

**Model.** `vintage_factor` interpolates linearly from 1999 to 2017 and stays flat
outside (no extrapolation). It applies to the as-built JAZ only; the reference keeps a
current unit. New term: **`term_vintage`** = H_ref × (1/JAZ_as-built − 1/JAZ_table) ×
HDD — "replace the unit". The terms still sum exactly (tested). An unknown year (63 of
172) makes no claim on the point estimate, widens the Monte Carlo band and raises the
tier.

**Category B, 172 households:** fleet **268,271 → 288,788 kWh/yr (+7.6%)**, median 1,498.
term_vintage totals 13,938; the rest of the increase is the envelope term, which is
divided by a lower JAZ in an old unit.

| install year | n | factor | median term_vintage | median deficiency |
|---|---:|---:|---:|---:|
| < 2008 | 26 | 0.85 | 314 | 1,849 |
| 2008–2014 | 33 | 0.93 | 134 | 1,264 |
| ≥ 2015 | 50 | 1.00 | 0 | 1,048 |
| unknown | 63 | 1.00 | 0 | 1,677 |

**Validation against the meter** (P13 v2 slope, post-visit, free step; nothing tuned):

| install year | n | measured / physics, vintage OFF | ON |
|---|---:|---:|---:|
| < 2008 | 20 | **1.47** | **1.28** |
| 2008–2014 | 30 | 1.22 | 1.15 |
| ≥ 2015 | 42 | 1.05 | 1.03 |

**The meter shows a clean gradient by installation year that the model had ignored.**
Vintage closes part of it, and ρ per m² rises 0.593 → 0.618. The remaining old-unit gap
(1.28) is consistent with the interpolation being conservative: factors are flat before
1999, and FAWA's fleet mean includes the better ground-source share.

**Visit queue re-run with vintage:** SLOPE_EXCESS **51 → 40**, INCONCLUSIVE 82,
BELOW_PHYSICS 23. Physics/measured 0.832. The drop is correct attribution: an old unit's
extra consumption is now a building deficiency ("replace the unit"), not a setting to
adjust.

## 2b. Is it vintage, or heating-curve settings in disguise? (`p23_confound.py`)

Both an old unit and an over-high curve raise the measured slope, and the meter alone
cannot separate them. Tested on the 145 assessed households (92 with a known year and a
curve reading). The curve setting is an instrument reading; labels are description only.

| install year | curve @ 0 °C, median | curve too high | limit too high |
|---|---:|---:|---:|
| < 2008 | 33.5 °C | 57% | 15% |
| 2008–2014 | 35.0 °C | 48% | 14% |
| ≥ 2015 | 33.0 °C | 57% | **35%** |

**Old units do not carry higher curves or more curve faults** (corr(age, curve@0 °C)
= 0.016). Limit faults are more common in *new* units.

**The age gradient survives inside equal settings** — measured/physics, vintage off:
high curve 1.86 → 1.39 → 1.16, low curve 1.18 → 1.10 → 1.02. Regression, n=92: **age
+2.1% per year [+0.9, +3.4]**, the same with or without the curve setting in the model.
Curve +0.7% per K, interval crosses zero.

**Two consequences:**
1. **term_vintage is not taking a technician's kWh on average.** The model's own factor
   implies ~+1.4% per year; the meter shows +2.1%, so the term is if anything
   **understated**. The rest stays in the slope excess. Nothing tuned (calibration rule).
2. **One real tangle: an interaction.** The age effect is much larger where the curve is
   high (1.86 vs 1.16) than where it is low (1.18 vs 1.02). Old units lose more at high
   flow temperature. For an **old unit with a high curve**, the two causes overlap:
   lowering the curve helps an old unit more. The model splits them additively, so for
   those houses the right order is **curve first (free), then judge replacement**.
   Flagged for the dashboard wording; not modelled.

## 3. Why BELOW_PHYSICS exists

The whole 95% band of the measured slope sits below the physical one: the house heats
with clearly less electricity per cold degree than the model says it should.
**It is not a fault, and it is not PV** (1 of 23).

| | BELOW_PHYSICS (23) | all assessed (145) |
|---|---:|---:|
| ground-source | **15 (65%)** | 45% |
| floor heating | **17 (74%)** | |
| installed 2008 or later | **16 of 19 known** | |
| residents, median | **2** | |
| heated area, median | **235 m²** | 200 m² |
| heated basement | **52%** | 41% |
| measured / physics | **0.72** | 0.83 overall |

Three mechanisms fit, each sourced or measured; none is proven per house:
1. **The unit beats the table.** New ground-source units with floor heating can exceed
   the table's 5.7. OST reports JAZ "über 6" for the best new builds.
2. **The house is heated less than the standard assumes.** Two people in 235 m², often
   with a heated basement, rarely keep every room at 20 °C. This is the prebound effect
   (FHNW 2017: real conditions better than calculated; basements ~8 K warmer than normative).
3. **The building beats its era average.** Typology values are averages, so some houses
   sit below them, including unrecorded improvements.

Not testable here: wood stoves or fireplaces (HEAPO has no such field).
**BELOW_PHYSICS is where the typical-house assumptions are too pessimistic for that house.
No action follows from it; it is a check on the model.** If it grew large, the constants
would be too high.

## Closing-session items added

`p11_export.py` must carry `term_vintage` and `vintage_factor`, and the new visit-status
levels.
