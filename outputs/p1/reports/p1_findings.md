# P1 — the capacity term: is the heat pump the right size for the building?

Run 2026-09-10. Script `p1_sizing.py`, transcript `outputs/p1/logs/p1_run.txt`,
data `outputs/p1/data/`.

**Result: oversizing is detectable at AUC 0.773 [0.651, 0.880]. It is the first
signal in this project whose interval excludes 0.5 with margin.**

---

## 1. What was computed

```
required_kW  = design_load_W_per_m2(era, renovation) * heated_area / 1000
installed_kW = HeatPump_Installation_HeatingCapacity
sizing_ratio = installed_kW / required_kW
```

Design loads are SIA 384.201 / EN 12831 benchmarks at `T_design = −10 °C`
(Zurich / Swiss plateau). **PENDING PAGE-LEVEL CITATION** — working constants,
nothing ships on them until sourced properly.

| era | W/m² band used | note |
|---|---|---|
| < 1975 | 50–70 | |
| 1976–80, 1981–85, 1986–90 | 40–50 | |
| 1991–95, 1995–00 | 32–45 | **INTERPOLATED — no 1990s band supplied** |
| 2000–10 | 25–40 | |
| > 2010 | 20–30 | |
| pre-1975 with ≥1 renovation flag | 40–50 | the source's "partially renovated" band |

Population: **200 of 214** carry area + capacity + era.

## 2. No smart meter data was used

This run is protocol data plus published standards. **The physics identifies the
deficiency before any consumption data is involved.** Consumption's role is to
*price* the deficiency in kWh/year, not to find it. Worth stating plainly because
it means the capacity term survives every consumption-side attrition problem —
the post-visit window, the summer requirement, the PV bias.

## 3. Validation — inspector's verdict, LABEL ONLY

`HeatPump_Installation_CorrectlyPlanned`, 198 of the 200 answer it: **166
correctly planned / 32 not**. Of the 32: 18 oversized, 6 undersized, **8 with no
direction recorded**.

**Base rate 16.2%, against 78.5% for settings faults — five times rarer, and
therefore five times more informative to detect.** This is the S-series'
central complaint answered: a flag true four times in five ranks nothing; a flag
true one time in six ranks something.

| test | era only | renovation-adjusted | n |
|---|---|---|---:|
| **oversized**, signed log ratio | 0.751 [0.616, 0.864] | **0.773 [0.651, 0.880]** | 18 vs 166 |
| mismatch either direction, \|log ratio\| | 0.646 [0.519, 0.764] | 0.689 [0.579, 0.785] | 32 vs 166 |
| undersized, reversed | 0.743 [0.479, 0.952] | 0.740 [0.425, 0.953] | **6** vs 166 |

Group medians of the sizing ratio (renovation-adjusted): correctly planned
**1.25**, oversized **1.70**, undersized **0.80**. Right order, right direction.

**The renovation adjustment helps consistently** (+0.043 and +0.022 AUC). Weak
evidence that the renovation flags carry real envelope information, on a crude
rule that only moves pre-1975 houses.

## 4. Defects and caveats

**4.1 The whole fleet reads as oversized, and this run cannot say why.** Median
ratio **1.25**; 42% (era only) to 48% (renovation-adjusted) exceed 1.3. Two
explanations, not separable here:

* Swiss installers genuinely oversize — real and documented. Capacity must cover
  the DHW reheat peak as well as space heating, and non-modulating units get
  rounded up to the next size.
* The design-load midpoints are too low.

**The AUC is unaffected — it is rank-based.** But **every absolute claim depends
on the level, and the level is not established.** The same lesson as P0's:
comparisons are sound, levels are not. **The design loads must NOT be tuned to
move the median to 1.0** — that is the calibration rule, and the fleet median is
exactly the kind of quantity it forbids fitting to.

**4.2 Heavy overlap. This is a ranking signal, not a separator.** Inspector-called
oversized spans 0.95–3.00; correctly planned spans 0.22–2.60. One house called
oversized computes at 0.95; one called correctly planned computes at 2.60.

**4.3 Undersized cannot be measured at n=6.** Interval [0.425, 0.953] crosses 0.5.
Direction is right and consistent across both adjustments. **Report it, never
rank on it, never claim it works.**

**4.4 24 households run on interpolated design loads** (1991–95 and 1995–00). No
1990s band was supplied; the value used is a straight interpolation between the
1980s and 2000s bands. Flagged on every row, not hidden.

**4.5 The either-direction test is diluted** by the 8 incorrectly-planned
households with no direction recorded — they enter the `|log ratio|` test with an
unknown sign of deviation.

**4.6 `Building_FloorAreaHeated_Total` is the inspector's measurement**, and the
inspector also produced the verdict being validated against. If an inspector who
judged a pump oversized also recorded the area differently, the two are not fully
independent. Not testable here; declared.

## 5. What this licenses, and what it does not

**Licensed:** the capacity term becomes Category B's lead signal, ranked on
`|log sizing_ratio|`, with `oversized` as the direction that carries evidence.

**Not licensed:**

* **No absolute oversizing threshold.** "Ratio > 1.3 means oversized" is not
  supported — see 4.1. Rank, do not threshold, until the level is sourced.
* **No undersizing claim.** n=6.
* **No tuning of the design loads.** Not to centre the fleet, not to raise the AUC.
* **No use of `CorrectlyPlanned` as a model input**, here or downstream. It is the
  scoring label and spending it as an ingredient would end the only validation
  this workstream has that clears 0.5.
