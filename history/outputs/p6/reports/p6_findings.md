# P6 — the window, PV, and a bias that revises every earlier number

Run 2026-09-10. `p6_window_and_pv.py` plus the HDD-bias work folded into
`p_physics.py`. Transcript `outputs/p6/logs/p6_run.txt`.

**Headline: `hdd_per_day × 365` systematically overestimates annual heating
degree-days, worst on short records, and every deficiency figure before this run
is inflated. The fleet total falls from ~454,840 to 321,330 kWh/yr.**

---

## 1. THE BIAS — measured, corrected, and it changes everything

`hdd_per_day × 365` assumes the recorded days are a fair sample of a year. They
are not. Records are holey and start and end mid-season, so **a one-to-one-and-a-
half-year record covers two winters and one summer** and reads far too cold.

Measured on **1,032 households carrying at least one complete calendar year**, as
`(hdd_per_day × 365) ÷ (mean HDD over complete years)`:

| record length | median est/true | 2.5–97.5% | n |
|---|---:|---|---:|
| **365–548 days** | **1.252** | 1.156 – 1.328 | 354 |
| 548–730 | 0.956 | 0.928 – 1.158 | 333 |
| 730–1095 | 1.112 | 0.982 – 1.223 | 174 |
| 1095+ | 1.077 | 0.962 – 1.145 | 171 |

**Short records run 25% hot.** Even the longest run 8% hot.

**This is weather only — no consumption enters, so the calibration rule is not
engaged.** It is a sampling correction on a weather aggregate, not a tuning of
physics to the meter.

Now in `p_physics.HDD_SAMPLING` / `hdd_correction()`, applied to the point
estimate and sampled in the Monte Carlo.

**Consequence: every deficiency number in P2, P4 and P5 is inflated.** Fleet total
**454,840 → 321,330 kWh/yr**, a 29% reduction. Median household **1,609** kWh/yr.
**155 of 172 decisive.**

*Reconciled 2026-09-10: the first pass reported 317,947 / 1,590 / 154 of 171,
before `p_pipeline_test.py` forced the footprint fix in §5.*

### Known extrapolation

The bins were measured on records of 365+ days, because the reference needs a
complete calendar year. **Records shorter than 365 days receive the 365–548
correction, which is extrapolated, not measured.** `897731` (212 days) sits in the
current top 10 on that basis. Its band of 9,043 kWh on a deficiency of 7,435 is
the widest in the top 10, so the uncertainty engine does flag it — but the point
estimate rests on an unmeasured correction and must be marked, not trusted.

## 2. The post-visit window is a CALENDAR filter

| visit year | excluded by the rule | kept |
|---|---:|---:|
| 2016–2022 | **0** | 145 |
| 2023 | 19 | 22 |
| 2024 | **7** | 0 |

**Every excluded household was visited in 2023 or 2024.** The rule finds recent
visits, not bad data — recent visits simply have not accumulated a year of
post-visit record. Cost: **172 → 145, −15.7%.** Of those lost, 4 have no
post-visit day at all and the rest have too few (median 74 days, **zero warm days**).

They are not a random draw: **30.8% pre-1975 against 20.0%** in the kept group,
**50.0% renovated against 37.9%**, median record 456 days against 1,045.

### The window does not change Category B

On the 145 present in both windows: **Spearman 0.9916**, median deficiency ratio
**1.000**, `hdd_per_day` 3.884 vs 3.820.

**Category B never reads the meter.** It is computed from geometry, era, JAZ,
residents and HDD — and HDD is a *weather* quantity. So the non-circularity
argument that justified the post-visit rule **does not apply here**: there is no
consumption fit, therefore nothing of the inspector's to rediscover.

**DECISION: all days for Category B, post-visit for the meter-based axis (A and
C), where the pre-visit period genuinely describes a machine that no longer
exists.**

They are retained. **After the bias correction they are ordinary** — comparable
median deficiencies and near-identical bands, nearly all decisive. Their presence
in the overall top 20 falls from **4 to 2** once the inflation is removed.

**Note the near-coincidence:** the calendar rule was excluding these households
for a reason unrelated to the record-length bias that was inflating them. Two
different problems pointing the same way. Fixing the real one is the correct
move; excluding by calendar would have been right by accident and wrong in method.

## 3. PV does not bias Category B — measured

**21 True, 99 False, 25 Unknown.** Absence is not "no PV" (parent trap 3).

| PV level | n | median deficiency | median implied appliance load |
|---|---:|---:|---:|
| PV | 21 | 1,522 | **3,679** |
| no PV | 99 | 1,356 | **5,980** |
| Unknown | 25 | 2,016 | 6,964 |

**Deficiency is materially the same across PV levels. The meter-based check is
not** — PV households sit ~2,400 kWh/yr lower, which is invisible self-consumption
appearing exactly where theory says it should and nowhere else.

**DECISION: keep PV in Category B; exclude PV from any meter-based comparison.**
Stronger than "separate subgroup with a declared bias" — the bias is real, and it
lands on a quantity Category B does not use.

## 4. Standing limitations after this run

* Records under 365 days use an **extrapolated** HDD correction (§1).
* The design-load offset against SIA 384.201 (1.13–1.49) is unchanged and
  unexplained.
* Capacity is detected (AUC 0.786) but still **not priced**.
* `b_ground = 0.5` now sourced to SIA 380/1 / 384.201, section number still
  outstanding; 26 households on a **derived** GSHP JAZ.
* 24 of 214 remain unjudgeable, 21 of them for missing per-storey geometry.
* The B/D line is still a **ranking**, not a threshold. Physics cannot supply one.
