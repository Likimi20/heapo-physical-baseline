# P25 — the target overview in three groups. 2026-09-12

Run: `p25_overview.py` · data `outputs/p25/data/p25_overview.parquet` (172 × 48) ·
log `outputs/p25/logs/p25_run.txt`

**Why this run exists.** Miguel, 2026-09-12: instead of one ranked list per
construction era, split what the model says into the three things a reader can act
on, each with an owner. This run measured whether that split holds up and whether
the ranking can be fleet-wide. **Both answers fed the v2 export**, so this is the
run behind the shipped design, not a sketch beside it.

**Aaditya's fault model is deliberately absent**, here and in P13. The two models
meet only in a final target overview, each keeping its own column.

---

## 1. The three groups are exact, not approximate

172 households. `house + heat_pump == total` to **2.73e-12 kWh/yr** — floating-point
noise, so the decomposition is an identity and may be displayed as one.

| group | what | fleet kWh/yr | median | median lo | decisive (whole band > 0) |
|---|---|---:|---:|---:|---:|
| **house** | envelope + emitter + DHW | 274,851 | 1,345 | 830 | **155 of 172** |
| **heat pump** | vintage | 13,938 | 0 | 12 | 133 of 172 |
| **total** | house + heat pump | 288,788 | 1,498 | 907 | 158 of 172 |

The fleet figures are sums of **point** estimates. The v2 export's group totals
(house 196,311 · heat pump 9,291 · total 214,004) are sums of **lower bounds** on
its own scored set — different quantities, not a disagreement. Never quote one as
the other.

**The house group carries 95% of the energy** (274,851 of 288,788). The heat-pump
group is real but small, and that is a finding in itself: the fabric is where the
kWh are, the unit is where a single decision is.

## 2. Group 1 — house: era and renovation

| era | n | median | median lo | share renovated |
|---|---:|---:|---:|---:|
| pre1975 | 37 | 2,398 | 1,724 | 0.81 |
| 1976–1990 | 62 | 1,186 | 830 | 0.55 |
| 1991–2000 | 20 | 631 | 291 | 0.20 |
| 2001–2010 | 35 | 933 | 765 | 0.00 |
| **post2010** | 18 | **72** | **−86** | 0.00 |

Monotone from pre1975 to 1991–2000, then it turns up again at 2001–2010 before
collapsing. Two things to say about it, and the second is the important one:

* **Renovation tracks era almost perfectly** (0.81 → 0.55 → 0.20 → 0.00 → 0.00), so
  "old" and "renovated" are not separable in this data. An era cell is therefore
  not a clean instrument for the fabric's condition.
* **post2010's median lower bound is negative (−86).** It is the only era whose
  band crosses zero at the median — the model cannot confirm an excess for a
  typical post-2010 house. This is **the P9/P21 era gradient reappearing in the
  deliverable**, not a new result: per m² the physics under-predicts newer eras by
  24–53%. It is the reason the fleet-wide ranking ships with a declared bias note
  rather than silently.

## 3. Group 2 — heat pump: replace or keep, and no era at all

| recommendation | n | median age | median kWh/yr | fleet kWh/yr |
|---|---:|---:|---:|---:|
| `KEEP_IN_LIFE` | 76 | 7 | 0 | 3,850 |
| `PLAN_REPLACEMENT` | 23 | 15 | 215 | 5,414 |
| `REPLACE_END_OF_LIFE` | 10 | 28 | 433 | 4,674 |
| `RECORD_INSTALL_YEAR` | 63 | — | 0 | 0 |

Age and cost rise together across the three known-year classes (7 → 15 → 28 years;
0 → 215 → 433 kWh/yr), which is what a vintage term should do and is **not**
evidence that it is right — the term is built from published JAZ generations, not
fitted to these households.

**The group needs no era ranking, measured.** Median heat-pump kWh by era is
`0, 0, 0, 0, 14` — no structure across building age. A unit's vintage is equipment;
its efficiency gap does not depend on when the house was built. So the three-group
split is not cosmetic: **group 2 is genuinely a different axis**, with a different
owner and a different decision.

**The no-claim asymmetry is visible here.** The heat-pump median point is 0 while
its median lower bound is 12, and 133 of 172 bands sit wholly above zero — including
unknown-year households, where every Monte Carlo draw samples an older unit while
the point makes no claim. This is exactly the pattern that broke the export's
`lo <= point <= hi` rule and produced `phys_heat_pump_point_is_no_claim`.

## 4. The era question — fleet-wide against within-era

Worst quartile by each group's lower bound, 172 households:

| group | fleet-wide | within-era | shared |
|---|---:|---:|---:|
| house | 43 | 45 | **34** |
| heat pump | 43 | 45 | 39 |
| total | 43 | 45 | **34** |

Era composition of the two act-first lists, house group:

| | pre1975 | 1976–1990 | 1991–2000 | 2001–2010 | post2010 |
|---|---:|---:|---:|---:|---:|
| fleet-wide | **16** | 10 | 5 | 12 | **0** |
| within-era | 10 | 16 | 5 | 9 | **5** |

**The two lists disagree on about a fifth of their members** (34 shared of ~43–45).
The trade is explicit: fleet-wide sends nobody from post2010 and leans on pre1975;
within-era guarantees 5 post2010 visits by construction, whatever their absolute
size.

**Decision taken (Miguel, 2026-09-12): fleet-wide, with era as a filter and
`phys_rank_in_era` kept as a column.** The reasoning was his — under-predicting
newer houses is expected because they are newer, and the filter stops them going
unnoticed. This run is the measurement that made that an informed override of the
earlier "rank within era" rule rather than a preference.

## 5. What the overview says per house

Top of the list by total lower bound, showing that the three groups separate
cleanly in practice:

| household | era | house lo | pump lo | unit | visit axis |
|---|---|---:|---:|---|---|
| 116121 | pre1975 | 6,778 | 282 | `PLAN_REPLACEMENT` | `USES_LESS_THAN_MODELLED` |
| 876511 | 1991–2000 | 5,354 | 23 | `RECORD_INSTALL_YEAR` | `SLOPE_EXCESS` |
| 1111201 | pre1975 | 5,053 | 70 | `KEEP_IN_LIFE` | `SLOPE_EXCESS` |
| 5011111 | pre1975 | 4,663 | 17 | `RECORD_INSTALL_YEAR` | `USES_LESS_THAN_MODELLED` |
| 671781 | pre1975 | 2,719 | 199 | `REPLACE_END_OF_LIFE` | `USES_LESS_THAN_MODELLED` |

Two readings that justify the split: **1111201** needs a builder and explicitly not
an installer (`KEEP_IN_LIFE`, 70 kWh on the unit against 5,053 on the fabric), while
**671781** is the rarer case where both owners have something to do. A single
combined number would have hidden the difference.

`visit_status` is `nan` for households the visit axis cannot assess. That is
`NOT_ASSESSABLE`, not a missing value to fill.

## Re-run 2026-09-17 — the stale status column is FIXED, and the run reproduces

The first run (2026-09-12) wrote `visit_status = BELOW_PHYSICS`, a name retired later
that day in favour of `USES_LESS_THAN_MODELLED` (the export asserts no status contains
"below", which reads as "good"). **Re-run against the v2 visit axis, so the parquet now
carries the live vocabulary.** `grep BELOW_PHYSICS` over `outputs/p25/` returns nothing.

**Everything else reproduced exactly**, which is the point worth printing: the RNG is
seeded (`20260919`), so the two runs are comparable line by line.

| quantity | first run | re-run | |
|---|---|---|---|
| `house + heat_pump == total` | 2.73e-12 | 2.73e-12 | identical |
| fleet house / heat pump / total | 274,851 / 13,938 / 288,788 | same | identical |
| decisive bands | 155 / 133 / 158 | same | identical |
| era medians and renovation shares | — | same | identical |
| era quartiles, shared | 34 / 39 / 34 | same | identical |
| `visit_status` | `BELOW_PHYSICS` present | **gone** | **the fix** |

Refreshed axis on these 172: `INCONCLUSIVE` 82 · `SLOPE_EXCESS` 40 ·
`USES_LESS_THAN_MODELLED` 23 · 27 not assessable (`NaN`). The 27 are this cohort's share
of the export's 69 `NOT_ASSESSABLE` — **a state, not a missing value to fill.**

**No conclusion in this report changed.** The fix was to the label, exactly as the
earlier "logged, not fixed" note predicted; Miguel asked for it cleaned rather than
carried, so it was re-run instead of documented around.

## What this run does not establish

* It does not validate the vintage term against measured consumption. Nothing here
  is calibrated, and the calibration rule forbids it.
* The 172 are audited households with sufficient geometry and weather — not a fleet
  sample. The era composition above is this cohort's, not Switzerland's.
* `n = 18` for post2010 and `n = 20` for 1991–2000 are thin. The negative post2010
  lower bound is consistent with the measured era gradient, but on 18 households it
  is a pointer to that known bias, not an independent measurement of it.
