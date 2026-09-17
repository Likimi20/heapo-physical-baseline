# P18 — limitation 5, short records

Script `p18_normal_year_hdd.py`, transcript `outputs/p18/logs/p18_run.txt`, data
`outputs/p18/data/`. 2026-09-11. **172 households.** Weather only; no consumption read.

## Spec v3's fix is the wrong tool

A PRISM change-point fit projected onto a typical year **reads the meter**, and Category
B must not. The problem was never the fit. It was that Category B's degree-days were
averaged over the household's own **meter days**, which ties a building score to how long
the meter happened to run.

## The fix: each station's normal year

Mean annual HDD_12 over the complete years in the weather file (≥360 full days):

| station | years | normal HDD_12/yr | sd between years |
|---|---:|---:|---:|
| 8jB / Hg / ceOxS | 5 | 1,357–1,360 | 141–156 |
| HbsbG / sV3mR | 3–4 | 1,400–1,402 | 144–148 |
| wDD | 5 | 1,479 | 147 |
| z6I | 5 | 1,324 | 137 |
| **MqO** | 5 | **1,952** | 182 (the cold station, T_me 8.1 °C) |

Year-to-year CV is **10.4%**. **Declared:** this is the 2019–2024 record-period mean, 3–5
years, **not** a 20-year climate normal. The deficiency is linear in HDD for the heating
terms, so it is rescaled exactly from `evaluate()`'s own terms, and `p_physics` does not
change.

## Results

| | P6 route | normal year |
|---|---:|---:|
| fleet deficiency | 321,330 | **351,229 kWh/yr (+9.3%)** |
| median household | 1,609 | 1,696 |

Ranking: fleet Spearman **0.973**; within era 0.90–0.98. **Worst quartile within era: 44
of 45 shared**, one in and one out.

### P6's correction over-corrected this cohort

| record | n | raw HDD / normal | P6-corrected / normal | P6 divided by |
|---|---:|---:|---:|---|
| < 365 d | 15 | **0.842** | 0.672 | 1.252 (extrapolated) |
| 365–548 | 24 | **1.053** | 0.841 | 1.252 |
| 548–730 | 26 | 0.879 | 0.919 | 0.956 |
| 730–1095 | 39 | 0.994 | 0.894 | 1.112 |
| 1095+ | 68 | 1.045 | 0.971 | 1.077 |

P6 measured its bins on 1,032 fleet households. **On this cohort the bias it corrects is
much smaller** (1.053, not 1.252, at 365–548), and records under a year read **warm**, not
cold. Most of them are 2023/24 visits whose records miss part of a winter. So P6 **deflated**
short-record households, by up to a third below the normal. The −29% P6 reported was part
real correction and part over-correction. The normal year needs neither bins nor
extrapolation.

`897731` (212 days, P6's flagged extrapolation): 7,435 → **7,957 kWh/yr**, now with no
record-length dependence at all.

## Verdict — SOLVED IN METHOD, pending adoption

Record length no longer enters Category B. The band term changes from HDD_SAMPLING's bins
to the between-year CV, which is weather, not modelling.

**Open decision (Miguel):** adopt station normal-year HDD_12 as the Category B degree-day
input? The fleet headline moves +9.3% while the ranking barely moves. The visit axis would
annualise its slope excess on the same normal. A MeteoSwiss 1991–2020 normal would be
better still, but it is not on disk.
