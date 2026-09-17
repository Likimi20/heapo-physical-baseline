# P11 — the dashboard export. 214 × 66, and it refuses to write when a rule fails

Run: `p11_export.py` · contract `outputs/export/SCHEMA_v2.md` · log `outputs/p11/logs/p11_run.txt`
Order: `p22_registry → p24_lifecycle → p13_visit_queue → p11_export`

**The contract is the schema, not the numbers.** Column names, units and meanings are
frozen at `v2`; the values move as the model improves. A consumer binds to columns and
never to a figure quoted in a report.

---

## What ships

**214 rows, one per audited household, 66 columns.** Every household appears, including
the ones never computed — **unjudged is never judged normal, and never totalled as zero.**

| `phys_status` | n | meaning |
|---|---:|---|
| `HIGH_EXCESS` | 40 | confirmed excess, worst 25% of the fleet — act |
| `EXCESS_CONFIRMED` | 118 | confirmed excess, below the action cut |
| `INCONCLUSIVE` | 14 | computed, band crosses zero — no claim |
| `INCOMPLETE_AUDIT` | 42 | never computed |

**There is no "normal" state, by construction.** It would need a household's whole band
at or below code and not one achieves that. The model confirms an excess or says nothing.

Confirmed excess: **158 households, 215,121 kWh/yr on the lower bound**, of which
`HIGH_EXCESS` is **118,462 across 40**. Three groups, each with an owner:

| group | kWh/yr (lower bound, confirmed rows) | owner |
|---|---:|---|
| house — envelope + emitter + DHW | 197,851 | a builder |
| heat pump — the unit's generation | 9,051 | an installer |
| total — house + heat pump, asserted | 215,121 | the rank |

Totals over *every scored* household are larger (196,311 / 9,291 / 214,004) and are a
**different quantity**. Never quote one as the other; the dashboard computes whichever it
displays rather than carrying a constant.

## The rules the file enforces on itself

About thirty, checked at write time; **the run refuses to write if one fails.** The ones
that earned their place:

* every energy figure travels with a band, per group;
* `house + heat_pump == total`, and the four terms sum to the deficiency;
* the capacity scenario is never summed into a headline (`phys_scenario_never_sum_into_total`);
* no column name contains "fault" — that model is not loaded in this workstream;
* no status contains the word "below", which reads as "good";
* the visit axis is flagged hidden from the building pages;
* record length never enters the building score — asserted against the station normal year.

## Two things this stage got wrong and now guards

**The `lo <= point <= hi` rule was wrong, not the model.** It failed on 172 rows. Measured
before changing anything: `lo > hi` never happens; the total's point sits 2 kWh below its
band on **one** row through independent rounding; and **63 heat-pump rows have point 0
under a positive band — exactly the households with no recorded installation year**, where
the point makes no claim while every draw samples an older unit. Replaced by three honest
rules plus **`phys_heat_pump_point_is_no_claim`**, so a page shows the band rather than
the zero. My first hypothesis — sourced values sitting at band edges — was refuted by the
diagnostic.

**The never-computed 42 were labelled as one thing and are not.** `phys_no_result_reason`
read `drop_reason` from a frame left-merged onto the *scored* households, so it was NaN
for exactly the unscored ones and all 42 fell through a single default. Measured cause:
**21 building data missing, 18 meter record too short, 3 both.** Now 8 distinct
per-household causes plus **`phys_no_result_fix`** naming who acts — 24 an auditor can
fix, 18 need only a longer record and no visit helps. **Two regression guards**: reasons
must be per household (≥2 distinct) and the two audit causes must differ, because every
older rule only asked whether the column was *populated*, and "populated" is not "true of
this household".

## What the file is not

Neither `phys_context_e_as_built_kwh_yr` nor `phys_context_e_reference_kwh_yr` is a
predicted bill — appliances are excluded from both, so only the difference is meaningful.
The ranking is fleet-wide by decision and carries its own bias note on every row: per m²
the physics under-predicts newer eras by 24–53%, so the order tilts toward older houses.
