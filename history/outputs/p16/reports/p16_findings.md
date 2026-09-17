# P16 — limitation 3, the era gradient is too steep

Script `p16_thermal_bridges.py`, transcript `outputs/p16/logs/p16_run.txt`, data
`outputs/p16/data/`. 2026-09-11. **172 households, P9's own `beta_meas`.** Nothing in
`p_physics` changed.

## Spec v3's fix is rejected

γ(>2000) = 1.30 sits inside the P9 ratios (1.24–1.53) that we had already seen, so it
would be calibration with a citation attached. Setpoint rebound (22–24 °C) cannot enter
the formula either: the degree-day base is fixed at 12 °C (trap 13), and setpoint only
appears in the design load.

## The mechanism tested: thermal bridges

**TABULA Common Calculation Method, eq. 4 and Table 3:**
H_tr = Σ b·A·U + **ΔU_tb · A_env**. Thermal bridging is a **separate surcharge on all
U-values**, so element U-values exclude it, and `p_physics` has never carried it.
Categories are low / medium / high. The worked example uses **0.10**, which is also the
DIN 4108 Bbl 2 flat default for existing stock. The low and high values (0.05, 0.15) come
from hex-encoded text that could not be read. They are **PENDING VERIFICATION**, as is the
assumption that the Swiss "overall mean U" values are element values. The CH brochure has
not been read.

An **additive** term matters proportionally more for U = 0.24 than for 1.35, which is the
shape of the P9 error. Every category is reported, and none is chosen by fit.

**Reproduction first:** live model vs P9 file, H_as_built max |diff| 0.0, and all five era
ratios identical.

| ΔU_tb | pre-1975 | 1976–90 | 1991–2000 | 2001–10 | post-2010 | range | pre/post physics | phys/meas | ρ per m² |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.00 | 0.97 | 1.26 | 1.24 | 1.53 | 1.31 | 0.56 | 3.38 | 0.78 | +0.536 [0.409, 0.640] |
| 0.05 | 0.93 | 1.19 | 1.17 | 1.42 | 1.19 | 0.49 | 3.20 | 0.82 | +0.541 |
| **0.10** | **0.89** | **1.13** | **1.10** | **1.33** | **1.09** | **0.43** | **3.04** | **0.87** | **+0.544 [0.422, 0.649]** |
| 0.15 | 0.86 | 1.08 | 1.04 | 1.24 | 1.01 | 0.38 | 2.92 | 0.93 | +0.546 |

The meter's pre-1975/post-2010 ratio is **2.50 [1.68, 3.45]** (P9).

## What it means

1. **Thermal bridges explain part of the gradient, not all of it.** At the medium
   category the era range shrinks by a quarter (0.56 → 0.43). The rank does not
   degrade (ρ 0.536 → 0.544). The physics/meter ratio moves from 0.78 to 0.87.
2. **The shape does not fully fit.** Pre-1975 tips to 0.89, an 11% over-prediction,
   while 2001–2010 stays the outlier at 1.33. A uniform surcharge cannot do both. In
   reality the category varies by construction type: masonry with timber floors is
   "minimal", modern insulation with uninsulated balconies is "high". HEAPO records no
   construction type, so that variation cannot be modelled. **What remains is
   unexplained and not tuned.**
3. **Coupling with limitation 2, measured.** On the P15 design load (EN 12831
   conventions), ΔU_tb 0.10 makes the offset **more uniform** across eras (range
   0.23 → 0.17) but raises its level (1.12 → 1.26). **Both independent checks improve
   in SHAPE.** The levels move in opposite directions, and each level is already the
   unidentified part: the area basis for the table, and limitation 4 for the meter.

## The decision it forces: what counts as "properly specified"

| option | as-built | reference | deficiency |
|---|---:|---:|---|
| (a) same surcharge both sides | 0.10 | 0.10 | **unchanged, exactly** (H_ab − H_rf does not move) |
| (b) new build has better junctions | 0.10 | 0.05 | **+29,259 kWh/yr fleet (+9.1%)**, median +158 |
| (b') | 0.10 | 0.00 | +58,519 (+18.2%) |

(a) improves the level and the slope validation without touching the headline.
(b) is physically defensible, since SIA 380/1 limits Ψ for new build, but it is a
**policy choice about the reference**, and CLAUDE.md requires that to be declared and
taken from a standard. **Miguel's call.** Recommendation: **(a)** until the SIA 380/1
Ψ limits have been read.

NOTHING WAS TUNED.

## Addendum, same day — P17 changes how this reads

The table above is measured against P9's **straight-line** slope, which P17 showed is
inflated by an unmodelled heating-season step. On the **step** slope (P17 §5):
ΔU_tb 0.10 takes the era range from 0.52 to 0.40, pushes pre-1975 from 0.80 to **0.74**
(over-predicted), and brings the level to 1.06. 2001–2010 stays the outlier.

**The thermal-bridge "improvement" in the level was partly the step.** The shape effect,
a narrower range, survives. **At 0.05 the level lands on 1.009. That is trap 4 and is not a
reason to choose 0.05.**

Revised recommendation: add ΔU_tb = **0.10** under option **(a)** as a *completion* of the
formula. It is TABULA's own method and the stock default, and it is fixed before looking. It
is **not** a fit. The deficiency is unchanged. Rejecting a sourced term because it worsens a
fit would be the calibration rule broken in the other direction.
