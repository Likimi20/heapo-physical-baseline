# P14 — limitation 1, "levels are not predictions"

Script `p14_level_check.py`, transcript `outputs/p14/logs/p14_run.txt`, data
`outputs/p14/data/p14_level_check.*` and `p14_submeter_other.*`. 2026-09-11.

## What changed

`p_physics.appliance_electricity(residents)` — non-heat-pump household electricity
for a single-family house. **Source: BFE/EnergieSchweiz Faktenblatt 08.2021,
Tabelle 1** (2019 data): 4 persons **4,048 kWh/yr**, ±593.5 per person, −50 per
person from five (footnote 1). It **excludes heat pump, electric heating and electric
DHW** — exactly what `E_as_built` omits, so nothing is counted twice.

Band: no household spread is published, so the band spans the two editions of the
same model — 2019 data (value, `lo`) to S.A.F.E./Nipkow 2013, 2011 data (`hi`: 4 P
5,200, 750–850 per person). **A declared choice, not a measured spread.**

**Kept outside `evaluate()`.** It is identical in both baselines and cancels in the
deficiency; drawing it inside would shift every existing Monte Carlo stream.
`p_pipeline_test.py` section J pins the table and asserts the term never enters
`evaluate()`. **112/112 checks green — every P6 number is unchanged.**

205 of 214 households are single-family houses; 6 "other", 2 MFH, 1 blank carry the
EFH value anyway. Declared, not corrected.

## Test 1 — sub-meter: does the term predict measured non-heat-pump electricity?

`Total − HeatPump` on paired usable days, ≥180 paired days, residents recorded:
**n = 20** (0 days with Total < HeatPump).

| pool | n | median measured / predicted | inside band | Spearman |
|---|---:|---:|---:|---|
| PV False | 10 | **1.29** | 2 / 10 | −0.263 [−0.876, +0.419] |
| PV False + Unknown | 18 | 1.07 | 4 / 18 | +0.000 [−0.483, +0.470] |

**The term does not predict individual households.** Measured spread 2,300–10,600
kWh/yr at 5–95% against a predicted 2,800–8,300, and no rank agreement. On the
non-PV median, the typical value runs **~29% low** for this fleet.

**Electric-DHW households are over-predicted** (ratios 0.41, 0.45, 0.53, 0.69): the
DHW term at JAZ 1.0 (850 kWh/person) adds more than their `Other` channel shows.
Possibly the heater is metered on the heat-pump channel, or DHW is split. n is too
small to say. Logged, not chased.

## Test 2 — the level, like-for-like on each household's own recorded days

Predicted kWh/day uses the raw mean HDD of the same days the meter recorded, so no
annualisation and no HDD correction enter. 172 households at ≥180/60/60.

| PV False, n = 117 | without appliances | **with appliances** |
|---|---:|---:|
| residual median, kWh/yr | 5,933 | **2,631** |
| residual 5–95%, kWh/yr | 2,071 – 14,038 | −1,633 – 10,480 |

* measured / predicted median **1.30**, IQR 1.08–1.61
* inside the 95% band **31 / 117 (26%)**, above 69, below 17; band width 27% median
* **Spearman per m² +0.566 [+0.436, +0.673]** vs area alone +0.301 — the level
  ranks houses, and not only by size
* by era, measured/predicted: 1.28 / 1.27 / 1.52 / 1.44 / 1.22 — the same direction
  and shape as P9's slope gap
* appliances are a median **42%** of the predicted level

PV True (n = 30) sits at ratio **1.00**. That is **self-consumption hiding an
under-prediction, not a success.** Never quote it.

## Verdict — PARTLY SOLVED

1. **The unmodelled bias is mostly gone.** A sourced term removes 3,300 kWh/yr of
   the median gap; the remainder (+30%) matches two limitations already on record —
   the ~22% slope gap (limitation 4) and a typical appliance value running ~29% low
   on the sub-meter.
2. **The level is still not a per-household prediction.** 74% of households fall
   outside a band that carries only constant uncertainty. It does not carry
   occupant behaviour, which is the dominant spread. **The difference stays the
   only quantity that ships as a finding.**
3. **"Outside the band" must never be read as a fault.** A band built from constant
   spread alone is too narrow for a level by construction.

NOTHING WAS TUNED. The 1.30 and the 1.29 are findings about the constants.
