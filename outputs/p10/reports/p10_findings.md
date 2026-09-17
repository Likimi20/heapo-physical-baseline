# P10 — portability, demonstrated rather than claimed

Run 2026-09-10. `p10_portability.py`, transcript `outputs/p10/logs/p10_run.txt`.
**23 checks, 23 passed.**

Until now "portable method" was enforced only by a test that greps
`p_physics.py` for HEAPO column names. **That proves the physics does not MENTION
HEAPO. It does not prove another dataset can drive it.**

---

## Three bindings, run end to end

| binding | rows in | modellable | outcome |
|---|---:|---:|---|
| **#1** `p_adapter_heapo.py` — `protocols.csv` | 214 | 190 | the live deliverable |
| **#2** `p_adapter_synthetic.py` — foreign schema | 120 | 120 | round trip, all exact |
| **#3** `p_adapter_meta.py` — `meta_data.csv` | **1,358** | **0** | **REFUSED, 5 roles absent** |

**`p_physics.py` was not touched for any of them.**

## Binding #2 — a genuinely foreign schema

Column names in German, areas arriving as a **list per building** rather than one
column per floor, era as a **numeric code**, emitter as `FBH`/`HK`/`MIX`, heat
pump as `L/W`/`S/W`. Nothing HEAPO-shaped anywhere.

The round trip checks the physics against **arithmetic done by hand**, not against
itself: envelope term, emitter and DHW terms exactly zero when the house *is* the
reference, electric-DHW term, linearity in degree-days, ventilation cancelling out
of the difference, and an older house losing more than a newer one.

### The round trip caught its own test, which is the point

The envelope check first **failed** at −98.66 vs −106.26 kWh/yr, a 7% gap.
**That gap was exactly the HDD correction**, which is live inside `evaluate()`
while my hand arithmetic had used the raw 4.0 degree-days. The model was right and
the test was wrong.

Fixed, and a check added that the correction is genuinely in the path
(`4.000 → 3.714`). **A round trip that can catch the person writing it is doing
its job.**

### It also probes outside HEAPO's range

The synthetic fleet holds smaller bungalows than HEAPO contains, producing
Gebäudehüllzahl up to **3.61** against HEAPO's real maximum of 2.96. Not a defect:
a small single-storey building genuinely is nearly all roof and floor. **Probing
parameter space the real data does not cover is what a synthetic binding is for**,
and the ordering holds — the smallest single-storey buildings carry the largest
Hüllzahl.

## Binding #3 — the one that matters

`meta_data.csv` covers **1,358 households, six times the protocol cohort**, and
**cannot drive this model.**

| role | present | status |
|---|---:|---|
| area_m2 | 1,339 (98.6%) | OK |
| residents | 1,348 (99.3%) | OK |
| hp_type | 1,354 (99.7%) | OK |
| emitter | 1,310 (96.5%) | OK |
| dhw_electric | 1,358 (100%) | OK |
| **era** | 0 | **MISSING** — no construction or installation year exists |
| **footprint_m2** | 0 | **MISSING** — only one whole-dwelling living area |
| **n_storeys_above** | 0 | **MISSING** — no storey information of any kind |
| **heated_basement** | 0 | **MISSING** |
| **renovation_count** | 0 | **MISSING** |

**Five of ten required roles absent. Nothing was invented or defaulted, and
`p_physics.evaluate()` raises rather than guessing.**

**A contract that only ever says yes is decoration.** This one says no, names the
missing roles, and does so *before* a number is computed.

It also puts the generic-versus-specific split into code: **`meta_data` is what
the PEER model runs on** — any fleet, no site visit, imprecise. **The physical
model needs someone to have walked through the building**, and the contract now
states that requirement machine-checkably rather than in prose.

## What this does NOT prove

**Synthetic proves the INTERFACE travels. It cannot prove the CONSTANTS travel.**

TABULA U-values, SIA design loads and FAWA/WPZ field JAZ are **Swiss**. A UK,
German or Nordic fleet needs its own typology and its own field performance
figures, and the era bands would not even mean the same thing.

**Still absent: a second REAL dataset with audit-level building data.** That is
the only thing that would test whether the constants — not the code — survive a
move. The three roles that blocked `meta_data` (era, per-storey geometry,
renovation) are exactly what such a dataset must carry.
