# P17 — limitation 4, the ~22% slope baseline

Script `p17_slope_step.py`, transcript `outputs/p17/logs/p17_run.txt`, data
`outputs/p17/data/p17_slope_step.*`. 2026-09-11. **172 households**, the same days and
sufficiency rule as P9/P13 (all usable days, ≥180/60/60).

## Spec v3's fix is rejected

"Subtract the fleet-median slope excess" is the fleet-median correction CLAUDE.md
already rejects. It is also wrong on substance: **78.5% of the cohort carries a recorded
fault**, so the fleet median is not a fault-free reference. Subtracting it could erase
the signal the visit queue exists to find.

## Step 1 — the measurement was biased, not the physics

`beta_meas` was a plain OLS of daily kWh on HDD_12. P0 had already measured a real
heating-season step at HDD_12 = 0. A straight line through a step absorbs it as extra
slope. Refit with the step as a **free** parameter, which CLAUDE.md already permits. No
physics constant moves.

| | line (P9/P13) | line + free step |
|---|---:|---:|
| median R² | 0.7248 | **0.7545** |
| P0 cohort, for reference | 0.7299 | 0.7587 |

* **The step is real:** median 5.70 kWh/day (IQR 3.33–9.20), and **134 of 172** have the
  whole month-block-bootstrap band above zero.
* In degree-days the step is **2.49 K**, an implied balance point of about 14.5 °C. That
  is consistent with the fitted changepoints next door (15.2–15.5 °C), which were measured
  independently. SIA welds this step at 8 K; the fleet shows about 2.5.
* The step-model slope is **0.835×** the line slope (IQR 0.76–0.91).

## The ~22% — mostly a fitting artefact

| | physics / measured | measured above physics |
|---|---:|---:|
| line | **0.778** | +29% |
| line + free step | **0.946** | **+6%** |

The remaining +6% sits well inside the physics band (median relative width 38%). **Step 2
of the plan, distribution and emission losses, is therefore not needed for the level and
was not sourced. It is not added.**

Era ratios, measured/physics: line 0.97 / 1.26 / 1.24 / 1.53 / 1.31. Step **0.80 / 1.00 /
1.07 / 1.32 / 1.01**. Rank per m² is unchanged: ρ +0.536 → **+0.534**.

## Step 3 — a band on the slope excess

The meter side uses a month-block bootstrap, because the data are autocorrelated. The
physics side uses the Monte Carlo over the published spreads. Status comes from the whole
95% band.

| slope | point > 0 | **SLOPE_EXCESS** (band > 0) | INCONCLUSIVE | BELOW_PHYSICS | median excess |
|---|---:|---:|---:|---:|---:|
| line | 125 | 77 | 75 | 20 | 719 kWh/yr |
| **step** | 95 | **40** | **91** | **41** | **107 kWh/yr** |

**Of P13's 125 `SLOPE_EXCESS` households, 40 survive on the step slope with a band. 82
become inconclusive and 3 fall below physics.** The median band is about 1,500 kWh/yr, far
wider than the median excess.

## What the step absorbs — read before deciding

The step is where two things land: the building's real balance point above 12 °C, and a
heating curve's **parallel offset**, which is a controller setting. So the step-model slope
measures curve **steepness** only. An offset fault moves out of "slope excess" and into the
step. **The step has no physical prediction** (the balance-temperature route is dead, P3),
so it cannot be judged against physics. It can ship as a measured column, never as a
finding.

## Limitation 3 re-read on the step slope (section 5)

| ΔU_tb | pre-1975 | 1976–90 | 1991–2000 | 2001–10 | post-2010 | range | phys/meas |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 0.80 | 1.00 | 1.07 | 1.32 | 1.01 | 0.52 | 0.946 |
| 0.05 | 0.77 | 0.94 | 1.01 | 1.22 | 0.92 | 0.45 | **1.009** |
| 0.10 | 0.74 | 0.90 | 0.95 | 1.14 | 0.84 | 0.40 | 1.062 |

**0.05 lands on 1.009. That is trap 4, not a result.** A constant that reproduces the data
is a red flag, and 0.05 was not the declared value (0.10 is the stock default). On the
corrected slope, pre-1975 is **over**-predicted, consistent with the prebound effect TABULA
itself cites (Sunikka-Blank & Galvin 2012). 2001–2010 stays under-predicted whatever is
added. **The era gradient survives every sourced term. Rank within era stays mandatory.**

## Verdict — LARGELY SOLVED, and it changes the visit queue

1. The ~22% baseline was mostly a biased measurement. On a correctly specified fit, the
   physics predicts the fleet heating slope to within 6%, **without tuning anything.**
2. **P13's queue is inflated by the step.** Open decision (Miguel): should the visit axis
   rank on the step-model slope, with status taken from the band? That would take
   `SLOPE_EXCESS` from 125 to 40.
3. Unchanged and still open: P13 fits on **all** days, contrary to the post-visit rule for
   the meter axis.
