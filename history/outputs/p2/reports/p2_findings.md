# P2 — `E_as_built` versus `E_reference`, the two-baseline model

Run 2026-09-10. Script `p2_two_baselines.py`, transcript `outputs/p2/logs/p2_run.txt`.
Constants from spec v2 citation table, with one rejection (§1).

**Status: the machinery works and the decomposition is exact. Two independent
checks pass, two fail. The balance-temperature route is NOT validated and should
not ship. Read §5 and §6 before using any number here.**

Population **209** of 214 with area + residents + era + HP type + emitter; **203**
also have a usable consumption day.

---

## 1. One supplied constant is REJECTED

Spec v2 gives **GSHP + radiators at 50–55 °C a JAZ of 4.4**, against GSHP + floor
heating at 35 °C of **4.10–4.40**. That makes 55 °C radiators outperform 35 °C
floor heating. **Thermodynamically impossible** — raising flow temperature always
costs COP — and it contradicts the same table's own ASHP column, which is
correctly monotonic (2.80 at 55 °C < 3.10 at 45 °C < 3.40–3.60 at 35 °C).

**Used instead:** the ASHP flow-temperature ratio applied to the published GSHP
floor value. `4.25 × (2.80/3.50) = 3.40` for radiators, `4.25 × (3.10/3.50) = 3.76`
for mixed. **DERIVED, not published.** Affects **26 households (12.4%)**, each
carrying `jaz_derived = True`.

Had 4.4 been used, those 26 would have had their consumption under-predicted and
would have surfaced as false over-consumers.

## 2. Two checks that PASS

**2.1 The reference envelope, from two independent standards.** SIA 380/1 target
U-values area-weighted with the TABULA envelope split give
`0.20·0.50 + 0.15·0.22 + 0.20·0.18 + 1.00·0.10 = **0.269 W/m²K**`. TABULA's own
`> 2010` overall mean band is **0.20–0.28**. **They agree.** The reference house is
a citation, not a matter of taste.

**2.2 The implied non-heating electricity has the right magnitude.**
`E_as_built` deliberately excludes lighting, cooking and appliances — no SIA
heating standard supplies them. The residual `actual − E_as_built` should
therefore be roughly a Swiss household's non-heating electricity.

Measured median: **3,052 kWh/yr**. Swiss single-family non-heating consumption
runs ~3,500–4,500 kWh/yr. **The median lands.**

## 3. The deficiency, decomposed

Decomposition residual: **max |sum of terms − total| = 0.000000 kWh**. Exact.

| | median kWh/yr | share of fleet total | n carrying it |
|---|---:|---:|---:|
| envelope | 2,321 | **86.3%** | 183 |
| emitter | 0 | 6.0% | 68 |
| DHW | 0 | 8.3% | 59 |

**Fleet total: 942,634 kWh/yr across 203 households.** Envelope dominates.

By era, median deficiency and median share of that household's consumption:

| era | n | kWh/yr | % of `E_as_built` |
|---|---:|---:|---:|
| < 1975 | 48 | **9,832** | **68.6%** |
| 1976–80 | 30 | 2,935 | 46.3% |
| 1981–85 | 29 | 3,042 | 43.2% |
| 1986–90 | 12 | 2,707 | 42.8% |
| 1991–95 | 14 | 2,380 | 29.7% |
| 1995–00 | 13 | 1,814 | 29.0% |
| 2000–10 | 37 | 965 | 26.7% |
| > 2010 | 20 | **−92** | −2.9% |

**The `> 2010` negative is correct, not a bug.** TABULA's `> 2010` stock (0.20–0.28,
mid 0.24) is *better* than the SIA 380/1 target reference (0.269). MoPEC 2014
houses beat the target. The reference is therefore **not an upper bound**, and
negative deficiency reads as "already better than reference".

## 4. Ventilation dominates in new buildings

`H_V/A = 0.34 × 0.7 × 2.05 = **0.4879 W/m²K**`, identical in both baselines and
**cancelling exactly** in the difference.

For a `> 2010` house: transmission `0.24 × 1.4 = 0.34 W/m²K` against ventilation
**0.49**. **Ventilation is the larger loss in new Swiss buildings.** Physically
correct, well known, and invisible to any peer model — a genuine thing the physics
route sees that the statistical route cannot.

## 5. FAILURE — the design-load cross-check breaks for old buildings

Two independent routes to the same quantity: ours is `H_tot × (20 − (−10))`, built
from TABULA U-values plus SIA geometry and ventilation; theirs is the SIA 384.201
design-load table.

| era | ours W/m² | benchmark | ratio |
|---|---:|---:|---:|
| < 1975 | 95.6 | 60.0 | **1.59** |
| 1976–90 | 54.2 | 45.0 | 1.21 |
| 1991–00 | 41.9 | 35.0 | 1.20 |
| 2000–10 | 31.4 | 32.5 | **0.97** |
| > 2010 | 24.7 | 25.0 | **0.99** |

**Modern buildings agree to within 3%. Pre-1975 disagrees by 59%.**

The two supplied sources are **mutually inconsistent for old buildings**. Either
TABULA's `< 1975` U (1.20–1.50) is too high as a whole-envelope mean, or the
Gebäudehüllzahl band (1.80–2.20) is too high, or the SIA 384.201 pre-1975 figure
already assumes partial renovation.

**This is not licence to tune either one.** It is a finding about the constants,
and it means **the pre-1975 deficiency figures — median 9,832 kWh/yr, 68.6% of
consumption — are very likely overstated, plausibly by ~1.5×.** Do not quote them
without this caveat.

## 6. FAILURE — the computed balance temperature is not validated

`T_bal = 20 − q_int·A / H_tot`, computed from constants, never fitted.

**6.1 It has no within-era variation, algebraically.** `H_tot` is proportional to
area, so area cancels and `T_bal = 20 − q_int/(U·huellzahl + 0.4879)`. It is an
**era lookup with five distinct values**, not a household quantity: 18.4 (<1975),
17.2 (1976–90), 16.4 (1990s), 15.2 (2000–10), 13.9 (>2010).

**6.2 It has zero relationship with the fitted changepoint.** Against
`../outputs/changepoint_indicator.parquet` on 144 households with a qualifying fit:

* computed `T_bal` median **17.2 °C**
* fitted `tau` median **15.2 °C**
* median difference **+1.6 °C**
* **correlation −0.016**

**Essentially zero.** The era ordering is not reflected in the fitted values at
all. The +1.6 °C offset is consistent with omitting solar gains; the zero
correlation is not explained by that.

**6.3 Consequence — do not ship the per-household base.** Using it gave old houses
a base of 18 °C, hence more degree-days, which **amplified** their deficiency on
top of the U-value difference. That amplification is unsupported. **Recommendation:
recompute on the fixed `HDD_12` settled in P0.** The difference is less sensitive
to the base than the level is, but the cross-era comparison is not.

Note this comparison is a **validation, not a calibration** — nothing was tuned to
`tau`, and nothing may be.

## 7. FAILURE — the level is unusable per household

Implied non-heating electricity, `actual − E_as_built`:

| | kWh/yr |
|---|---:|
| median | **3,052** |
| IQR | 113 – 5,975 |
| 5–95% | **−6,555 – 11,400** |
| min / max | −29,716 / 24,260 |

**The median lands on the right physical quantity. The individuals do not.** A
quarter of households imply under 113 kWh/yr of appliance electricity, which is
impossible, and 5% imply strongly negative, which is more impossible.

This is the level-versus-difference lesson, now measured rather than argued.
**`E_as_built` is not a per-household prediction and must never be presented as
one.** Only the difference ships.

## 8. What ships and what does not

**Ships:** the decomposed deficiency by term, as a **ranking** within era, with the
pre-1975 caveat from §5 attached.

**Does not ship:**
* any absolute `E_as_built` for a single household (§7)
* the per-household computed base (§6)
* pre-1975 deficiency magnitudes without the 1.59 cross-check caveat (§5)
* the supplied GSHP+radiator JAZ of 4.4 (§1)

**Not yet done:** the capacity term from P1 is detected but **not priced**. Cycling
losses from oversizing are not in a steady-state model and no derating source was
supplied. Category B currently carries envelope, emitter and DHW in kWh, and
capacity as a flag with no kWh figure.
