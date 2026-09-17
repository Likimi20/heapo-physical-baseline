# P4 — Category B on real geometry and a fixed base

Run 2026-09-10. Script `p4_deficiency.py`, transcript `outputs/p4/logs/p4_run.txt`,
deliverable `outputs/p4/data/p4_category_b.csv`.

**189 households, 183 with consumption. This is the first version whose numbers
are defensible, with the limits in §5 attached.**

Everything P0–P3 settled, applied together: fixed `HDD_12`; audited per-storey
geometry, basement corrected; per-household Gebäudehüllzahl; TABULA as-built and
SIA 380/1 reference U; derived GSHP+radiator JAZ; **ranked within era**.

---

## 1. The basement fix worked

P3's storey table read backwards. Counting the heated basement as a storey and
charging its walls and floor at the ground b-factor:

| heated storeys incl. basement | n | median Hüllzahl |
|---|---:|---:|
| 1 | 8 | **2.34** |
| 2 | 92 | 1.89 |
| 3 | 79 | 1.91 |
| 4 | 10 | 1.90 |

**Now physically correct at the end that matters** — a bungalow carries the most
envelope per heated m². Flat beyond two storeys, which is also correct: added wall
area trades off against reduced roof and ground contact, and the two roughly
cancel. **71 of 189 (37.6%) have a heated basement.**

Geometric Hüllzahl: median **1.90**, IQR 1.76–2.04, 5–95% 1.42–2.35.

## 2. The deliverable

**Fleet deficiency 454,840 kWh/yr across 183 households.**

| term | share of fleet total | n carrying it |
|---|---:|---:|
| envelope | **79.9%** | 164 |
| DHW | 14.7% | 49 |
| emitter | 5.4% | 57 |

| | median kWh/yr | IQR |
|---|---:|---|
| `E_as_built` | 4,526 | 3,664 – 6,250 |
| `E_reference` | 2,717 | 2,247 – 3,425 |
| **deficiency** | **1,838** | 1,011 – 3,176 |

Decomposition residual **0.000000 kWh**.

**P2 reported 942,634 kWh/yr — more than double.** That figure was inflated by
the dead balance-temperature route, which handed old houses a base of 18 °C and so
far more degree-days. **P4 supersedes it.**

By era, ranked within era (the settled rule):

| era | n | median kWh/yr | % of own use |
|---|---:|---:|---:|
| < 1975 | 41 | 4,914 | 63.4% |
| 1976–80 | 26 | 1,754 | 41.7% |
| 1981–85 | 28 | 1,930 | 42.5% |
| 1986–90 | 11 | 1,630 | 40.7% |
| 1991–95 | 14 | 1,627 | 29.6% |
| 1995–00 | 10 | 1,477 | 36.3% |
| 2000–10 | 35 | 1,242 | 30.6% |
| > 2010 | 18 | **−100** | −3.2% |

`> 2010` negative is correct: TABULA's post-2010 stock (0.24) beats the SIA 380/1
target reference (0.269). **The reference is not an upper bound.**

## 3. The physical plausibility check now PASSES

`E_as_built` excludes lighting, cooking and appliances, so `actual − E_as_built`
should be a household's non-heating electricity — a positive number around
3,500–4,500 kWh/yr for a Swiss single-family house.

| | P2 (era lookup, computed base) | **P4** |
|---|---|---|
| median | 3,052 | **5,365** |
| 5–95% | **−6,555 to 11,400** | **897 to 14,878** |
| impossible negatives | yes, 5%+ of households | **none** |

**Every household now implies a positive appliance load.** P2's median was closer
to the norm but a quarter of households implied under 113 kWh/yr and 5% implied
strongly negative — physically impossible. **P4 trades a slightly high median for
a distribution with no impossible values, which is the better failure mode.**

The high median (5,365 vs ~4,000) is consistent with the design-load offset in §4:
if `E_as_built` is ~1.2–1.3× too low… no — if the *design load* runs high, heating
is over-predicted and the residual would be *lower*. The high residual therefore
suggests `E_as_built` is **under**-predicting heating despite the high design load,
plausibly because fixed `HDD_12` understates degree-days relative to the true
per-house balance point. **Unresolved; logged.**

## 4. Two independent routes to the sizing validation AGREE

P1 derived required capacity from the SIA 384.201 W/m² table. P4 derives it from
our own physics, `H_tot × 30 K`. Different inputs, same question.

| test | P1 (SIA benchmark) | **P4 (own physics)** |
|---|---|---|
| **oversized** | 0.772 [0.649, 0.883] | **0.786 [0.675, 0.878]** |
| mismatch, either direction | 0.685 [0.574, 0.780] | **0.484 [0.358, 0.612]** |

**Oversizing replicates across two independent derivations.** That is the strongest
evidence this workstream has produced.

**The either-direction test does not replicate** — it collapses to chance. It mixes
over- and under-sizing with 8 no-direction cases, and the two routes centre the
ratio differently (P1 median 1.30, P4 median 0.98). **Report oversizing only.
Drop the either-direction test.**

Note the centring difference is not resolved: on our own physics the fleet is
centred at 0.98, i.e. correctly sized; on the SIA benchmark it is 1.30, i.e.
oversized. That is the §4 offset restated, and it is **circular to claim either
settles the other**.

## 5. Defects — read before quoting

**5.1 The design-load offset persists and got marginally worse.** Ratios now
1.13 (`>2010`) to 1.49 (`<1975`), **range 0.36** against P3's 0.32. The basement
fix added wall area and raised every ratio. Still far better than the era lookup's
0.62 range, and still roughly uniform, which is what allows the difference to be
used. **Unexplained. Not licence to tune.**

**5.2 The high implied appliance load is unexplained** — see §3.

**5.3 The capacity term is detected but NOT PRICED.** Cycling losses from
oversizing are absent from a steady-state model and no derating source exists.
Category B carries envelope, emitter and DHW in kWh; capacity is a flag only.

**5.4 25 of 214 households are dropped** for missing footprint, era, residents,
emitter or a supported HP type. They are not in the deliverable and must be
reported as unjudgeable, never as normal.

**5.5 Cross-era comparison remains unsafe.** Within-era ranking is the shipped
form. The `<1975` column above is quoted for completeness and inherits the 1.49
offset.

**5.6 `b_ground = 0.5` is unsourced.** Assumed, not cited. It scales basement
walls and the lowest floor.

**5.7 26 households run on a derived, not published, GSHP+radiator JAZ** (P2 §1).
