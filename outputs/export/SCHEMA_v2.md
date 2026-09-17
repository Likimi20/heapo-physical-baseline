# `physical_baseline_v2` — dashboard export contract

Produced by `p11_export.py`. **214 rows × 66 columns**, one row per HEAPO protocol
household. Written as `.csv` (semicolon) and `.parquet`.

**The contract is the SCHEMA, not the numbers.** Column names, units and meanings are
frozen at `v2`; the values behind them move as the model improves. Bind to columns,
never to a number in a report.

**`physical_baseline_v1` has been retired** (2026-09-18). Its one cycle is over: the
dashboard page reads v2, the S-series split reads v2, and nothing else named it. The only
remaining reference is `p11_export.py`’s `PREVIOUS_VERSION` constant, which is the
bookkeeping that implements the side-by-side rule for the NEXT version bump.

**Run order:** `p22_registry` → `p24_lifecycle` → `p13_visit_queue` → `p11_export` →
`p_notebook`, then `p_pipeline_test` (141 checks) and `p10_portability` (23) must be green.

---

## What this model answers, and what it does not

**It answers:** *how much more electricity does this house use than a code-compliant
version of itself?* — computed from geometry, construction era, the unit's generation and
published Swiss sources. **It never reads the meter for this**, only for weather.

**It does not answer:** whether a heat pump is misconfigured. That axis belongs to
Aaditya's model, in **his own section**. The two meet only in a **final target overview**,
each keeping its own column. **There is no fault column in this file.**

**Never merge with the peer model.** Every column is prefixed `phys_` or `visit_` so a
pasted table cannot be misread.

## The section this feeds: one section, two pages

| page | what it shows |
|---|---|
| **1 — explain the rank** | what the number means and **who fixes it**: builder, installer, or both |
| **2 — the one list** | a **single fleet-wide list**, three columns: **house / heat pump / total** |

| group | columns | owner |
|---|---|---|
| **house** | `phys_group_house_*` = envelope + emitter + DHW | a builder |
| **heat pump** | `phys_group_heat_pump_*` = the unit's generation | an installer |
| **total** | `phys_deficiency_*` = house + heat pump (asserted) | the rank |

## Identity

| column | type | meaning |
|---|---|---|
| `household_id` | int | HEAPO `Household_ID`, unique, all 214 present |
| `schema_version` | str | `physical_baseline_v2` |
| `generated_utc` | str | ISO 8601 build timestamp |

## Status — four states, and none says "normal"

| state | n | meaning | action |
|---|---:|---|---|
| **`HIGH_EXCESS`** | 40 | confirmed excess, worst 25% **of the fleet** | **act** |
| **`EXCESS_CONFIRMED`** | 118 | confirmed excess, below the action cut | real, not first |
| **`INCONCLUSIVE`** | 14 | computed, band straddles zero | **no claim** |
| **`INCOMPLETE_AUDIT`** | 42 | never computed. **A MIXED SET, and the cause is now PER HOUSEHOLD:** 21 building data missing, 18 meter record too short, 3 both | **read `phys_no_result_fix`** — 24 an auditor can fix, 18 need only a longer record |

Supporting columns: `phys_status_reason`, `phys_no_result_reason` (this
household’s cause, 8 distinct values), **`phys_no_result_fix` — who can act**,
`phys_no_result_is_fixable`, `phys_excess_confirmed`.

**Read `phys_no_result_fix`, not the boolean, to decide whether to send anyone.**
`phys_no_result_is_fixable` means only *will this ever become answerable* (`True` for
both audit gaps, `False` once the sources cannot resolve it). The action lives in the
string: **“record the missing building data — an auditor can do this” (24)** against
**“none — needs a longer meter record; a visit does not help” (18)**.

**No "normal" state exists.** It would need a household's whole band at or below code,
and not one is. We confirm an excess, never its absence.
**"Excess", not "below"** — *below* reads as *good*; a rule asserts no status on either
axis contains the word.
**Neither no-result state may render green.** Both are visible and filterable
(decision 4).

> **FIXED 2026-09-17 (found by P27).** The two reason columns used to put ONE blanket
> string on a mixed set. The cause was read from a frame left-merged onto the SCORED
> households, so `drop_reason` was NaN for exactly the 42 unscored ones and every one of
> them fell through to a single default. `phys_no_result_reason` now carries **8 distinct
> per-household causes**, and the new `phys_no_result_fix` names who acts. Two export
> rules guard it: reasons must be **per household** (≥ 2 distinct) and the two audit
> causes must differ — because “the column is populated” is not “the column is true of
> this household”, which is how the original passed every check.

## The order — fleet-wide, by decision

| column | meaning |
|---|---|
| **`phys_rank_fleet`** | **the primary order**, 1 = act first |
| `phys_rank_in_era` | kept so the era bias stays checkable |
| `phys_rank_on` | `phys_rank_value_lo_kwh_yr` |
| `phys_rank_scope` | `fleet` |
| `phys_rank_bias_note` | the caveat, on every row |
| `phys_rank_value_kwh_yr` / `_lo_kwh_yr` | the ranked quantity, point and lower bound |
| `phys_rank_excludes_vintage` | `True` = a `KEEP_IN_LIFE` unit, vintage left out of the rank |

**Fleet-wide overrides the old "rank within era" rule** (Miguel, 2026-09-12). Ship the
caveat with it: per m² the physics under-predicts newer eras by 24–53%, so the order
tilts toward older houses. **Era is a filter**; `phys_rank_in_era` remains.

**Option A:** vintage counts in the total but **not** in the ranking value for units we
would keep — a 10-year-old unit must never push a near-compliant house onto the act list.

## Energy — rank and display the lower bound

| column | unit | meaning |
|---|---|---|
| `phys_deficiency_kwh_yr` | kWh/yr | point estimate |
| **`phys_deficiency_lo_kwh_yr`** | kWh/yr | **2.5th percentile — the honest "at least this much"** |
| `phys_deficiency_hi_kwh_yr` | kWh/yr | 97.5th percentile |
| `phys_deficiency_band_kwh_yr` | kWh/yr | `hi − lo` |
| `phys_deficiency_pct_of_reference` / `_lo` / `_hi` | % | reads where kWh cannot: "+20% over code" |
| `phys_group_house_kwh_yr` / `_lo` / `_hi` | kWh/yr | the fabric, a builder's job |
| `phys_group_heat_pump_kwh_yr` / `_lo` / `_hi` | kWh/yr | the unit's generation, an installer's job |
| `phys_group_house_owner` / `phys_group_heat_pump_owner` | str | `builder` / `installer` |

Confirmed excess: **158 households, 215,121 kWh/yr on the lower bound**, of which
**`HIGH_EXCESS` is 118,462 across 40**. Fleet totals on the lower bound: **house
196,311 · heat pump 9,291 · total 214,004 kWh/yr**.

**`phys_heat_pump_point_is_no_claim`** — `True` on the **63** households with no recorded
installation year. Their point is `0` (no claim) while the band sits above it, because
every draw samples an older unit. **Show the band, not the zero.**

## Decomposition

| column | note |
|---|---|
| `phys_term_envelope_kwh_yr` | the largest term, and the only one with independent rank validation (ρ ≈ 0.54 per m²) |
| `phys_term_dhw_kwh_yr` | electric cylinders dominate it |
| `phys_term_emitter_kwh_yr` | radiators against floor heating |
| `phys_term_vintage_kwh_yr` | the unit's generation, 0 where the year is unknown |
| `phys_vintage_factor` | 1.0 = a current unit |

The four sum to `phys_deficiency_kwh_yr` within rounding, and
`house + heat_pump == total` — both asserted on write.

## The heat-pump decision

| column | meaning |
|---|---|
| `phys_unit_recommendation` | `REPLACE_END_OF_LIFE` 10 · `PLAN_REPLACEMENT` 23 · `KEEP_IN_LIFE` 76 · `RECORD_INSTALL_YEAR` 63 |
| `phys_unit_age_years` | age **as of the data end**, not today |
| `phys_unit_age_reference_year` | `2024` — **state this on the page** |
| `phys_unit_service_life_basis` | measured failures, Weibull fit (ZHAW): air 20 yr SD 7, ground 26.7 yr SD 4.7 |

**"Old" is not an action.** Replacement is recommended only at or past the expected
service life; a mid-life unit reads `KEEP_IN_LIFE` and its vintage kWh is information.
**Unknown year is a fixable audit gap**, like `INCOMPLETE_AUDIT` — never an old unit.
The **"adjust the heating curve first, then replace"** case belongs to the **end
section**, not these pages.

## Scenario — never summed

`phys_scenario_capacity_lo/mid/hi_kwh_yr` with `phys_scenario_never_sum_into_total`
always `True`. Not a measurement: no source maps sizing ratio to a penalty, so the shape
is assumed. Show per household, never as a fleet share.

## Context — not predictions

`phys_context_e_as_built_kwh_yr`, `phys_context_e_reference_kwh_yr`,
`phys_level_is_not_a_prediction`, `phys_appliances_excluded` (both always `True`).
**Never show these as an expected bill**: appliances are excluded from the model
entirely, and only the *difference* is meaningful.

## Data-quality flags — surface next to the number

`phys_completeness_tier` (`T1` tightest → `T3` widest) · `phys_geometry_reconciles` ·
`phys_pv_level` (`PV` / `no PV` / **`Unknown` is not `no PV`**) · `phys_n_meter_days` ·
`phys_hdd_normal_per_day` · `phys_weather_basis` (station normal year — **record length
never enters the building score**, asserted).

## Visit axis — in the file, HIDDEN from these two pages

For the **end section** only, where the two models meet.

| column | meaning |
|---|---|
| `visit_status` | `SLOPE_EXCESS` 40 · `INCONCLUSIVE` 82 · `USES_LESS_THAN_MODELLED` 23 · `NOT_ASSESSABLE` 69 |
| `visit_technician_recoverable_kwh`, `visit_slope_excess_lo/hi_kwh`, `visit_slope_excess_pct` | the slope excess, point and band |
| `visit_step_kwh_day` | the free heating-season step — a measurement, never judged |
| `visit_rank_in_era`, `visit_never_sum_with_phys_deficiency`, `visit_hidden_from_building_pages` | order, never-sum flag, and the display rule |

Computed on **post-visit days only**, with the step fitted free and status from a 95%
band. `USES_LESS_THAN_MODELLED` replaced `BELOW_PHYSICS` and **is not a fault**.

## Limits worth knowing before you quote a number

1. **Era gradient:** per m² the physics under-predicts newer eras by 24–53%; the list is
   fleet-wide by decision, so the filter and `phys_rank_in_era` are the mitigation.
2. **Chart-read U-values:** TEP's figures were read off bar charts; they pass the
   report's own text check but are approximate.
3. **One envelope split:** a single Swiss reference building, with a German typology as
   the band.
4. **Air-source service life** rests on 53 units, 43 from one firm — the authors call it
   less reliable; ground-source rests on 223.
5. **Design-load offset** against SIA 384.201 is only half explained.
6. **Swiss constants:** the code ports; the constants do not.
7. **Nothing is calibrated.** Where physics and meter disagree, the disagreement is
   reported, never tuned away.
