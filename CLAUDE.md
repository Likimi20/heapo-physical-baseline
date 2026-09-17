# Project context — Physical baseline model

Physics-based expected consumption for domestic heat pumps, Swiss audit data.
Sibling of `../STRATUM-LEVEL RESIDUAL MODEL/` and of the parent at `../`,
**not a continuation of either**. Read `../CLAUDE.md` for the shared data facts
and the 20 traps; this file states what is different here and **overrides both
wherever they disagree**.

Working with Miguel: academically strong, new to hands-on research and coding.
Explain statistics and method concepts properly, do not assume prior knowledge.
Blunt beats polite. All output English.

---

## Generic versus specific — the one-line reason this exists

**Peer comparison is the GENERIC instrument.** It runs on any company's fleet
with survey metadata alone, needs nobody to enter a building, and is imprecise by
construction — measured next door, the best stratum key still leaves **77–94% of
variance unexplained**. It says *this house ranks above its neighbours*. It cannot
say what any house *should* use.

**The physical baseline is the SPECIFIC instrument.** It requires somebody to
have walked through the house. In exchange it computes what that house **should**
consume from first principles, so its output is a quantity with a cause attached,
not a rank.

**Two methods, two sections, never one number.** They are presented side by side
and must not be merged, averaged, pooled or reconciled into a single score. A
household can be high here and normal there, and that disagreement is a finding
to report, not a bug to fix.

## Scope — what this workstream is

Compute what a household **should** consume from building physics and cited
constants, and categorise how far its building falls short of a code-compliant
version of itself.

**Category B never reads the meter** (P6) — it is geometry, era, JAZ, residents
and weather. The meter belongs to the A/C axis.

The source spec is `../STRATUM-LEVEL RESIDUAL MODEL/heapo-physical-model-spec.md`.
**It is a starting point with twelve known defects, listed under "Corrections to
the spec" below. Do not implement it as written.**

### The real deliverable is a PORTABLE METHOD, not a HEAPO result

Confirmed by Miguel 2026-09-10. The point is to run this on **other datasets that
carry the same specifications**. HEAPO's 214 inspected households are the **test
bed**, not the product.

So the model is written against **variable ROLES, never HEAPO column names**:

| role | meaning | required? |
|---|---|---|
| `heated_area_m2` | total heated floor area | **required** |
| `construction_era` | building age band | **required** |
| `renovation_windows / walls / roof` | envelope upgrade flags | optional, tiered |
| `emitter_type` | floor heating / radiator / both | **required** |
| `dhw_source` | heat pump / electric / solar / hp-boiler | **required** |
| `residents` | occupant count | **required** |
| `rated_cop` | certified nominal COP | optional, tiered |
| `hp_type` | air-source / ground-source | **required** |
| `pv_present` | PV installed | optional, tiered |

**Two layers, two files, never mixed.**

* `p_physics.py` — the formula and the constants. Knows nothing about HEAPO.
* `p_adapter_heapo.py` — maps `protocols.csv` columns onto the roles above.
  **Binding #1.** A second dataset gets `p_adapter_<name>.py` and nothing else
  changes.

If a physics function ever references a string like `Building_FloorAreaHeated_Total`,
the separation has been broken and it is a defect.

## Scope — what this workstream is NOT

* **Not a fault detector, and not a fault namer.** Fault identification is
  **Aaditya's area**. ML detectors for the top three recorded faults arrive later.
  Category A ships here as a **sized but unnamed slot** — a household list and a
  kWh figure with no fault string, or at most the slope hypothesis carried
  explicitly as a hypothesis. **Do not build a detector here, not even as a
  by-product.**
* **Not peer comparison.** No strata, no cells, no within-group z, no robust MAD
  against neighbours. If a decision needs another household to be made, it does
  not belong here.
* **Not fed by `meta_data.csv`.** Miguel, 2026-09-10: this workstream is
  **divided from metadata**. Inputs are `protocols.csv` + smart meter + weather.
  **This inverts the S-series rule.** Heated area comes from
  `Building_FloorAreaHeated_Total` (214/214), never from
  `Survey_Building_LivingArea`.
* **Not calibrated against the meter.** See *The calibration rule* below. This is
  the single most important constraint in this file.
* **Not the forecaster.** No F-series artefact is an input, ever.

## THE CALIBRATION RULE — settled 2026-09-10, not open

**No constant in this model may be fitted, tuned, nudged or selected by looking
at the consumption data it will later be compared against.**

Why, plainly: if you compute `E_expected = 20`, see the meter says 26, and adjust
a U-value until the formula also says 26, then `E_expected` secretly came from the
meter. Comparing them afterwards compares the meter with itself. It will always
look right and it can never catch anything. A bathroom scale adjusted until it
shows the weight you expected is not a measurement.

**Rejected explicitly:** a fleet-median correction factor. Miguel, 2026-09-10 —
the fix for an idealised formula is a **better justified formula**, not a
correction applied afterwards.

### So the formula gets MORE COMPLETE, not more tuned

The spec's formula is idealised: it omits ventilation and infiltration losses,
internal gains (occupants, appliances, lighting), and solar gains. Those are not
unknowable — they are tabulated in **SIA 380/1**, the same standard family as the
SIA degree days the spec already uses. Swiss, citable, and not invented here.

**Every constant carries `value`, `unit`, `source`, `source_year`. A constant with
no source does not ship.**

### The constants, supplied 2026-09-10 — PENDING PAGE-LEVEL CITATION

Source names are known; page locations are not. **Usable to build and test with,
not to publish on.** Every artefact built on them says so.

**Envelope, overall mean U (W/m²K).** `E_as_built` from **TABULA / EPISCOPE Swiss
national typology** — what houses *are*. `E_reference` from **SIA 380/1 target
values** — what they *should be*. Two independent standards mapping onto the two
baselines, which is a far stronger position than picking a reference by taste.

| era | TABULA overall mean | spec claimed | error |
|---|---|---|---|
| < 1975 | **1.20–1.50** | 1.4–1.8 | spec +20–25% |
| 1976–1990 | **0.70–0.90** | 0.9–1.2 | spec +25% |
| 1991–2000 | **0.50–0.60** | 0.6–0.8 | spec +20–30% |
| 2001–2010 | **0.35–0.45** | — | |
| > 2010 | **0.20–0.28** | 0.3–0.5 | spec +50% |

**The spec's U-values were 20–50% too high, every band in the same direction.**
That inflates `E_expected` for old houses, so an old leaky house would have to be
wildly over-consuming to be flagged — **the spec would have made old leaky houses
look efficient**, the exact opposite of Category B's purpose.

SIA 380/1 target per element: wall 0.20, roof 0.15, floor-to-ground 0.20,
windows 1.00, area-weighted with the supplied TABULA SFH envelope split
(wall .50 / roof .22 / floor .18 / window .10) to **U_reference = 0.269 W/m²K**.
That lands inside TABULA's own `> 2010` band (0.20–0.28) — **two independent
standards agreeing, so the reference house is a citation, not a taste.**

**Design heat load, SIA 384.201 / EN 12831, `T_design` = −10 °C** (Zurich /
plateau, SIA 2028): <1975 **50–70 W/m²** (80–100 extreme); partially renovated and
1980s **40–50**; modern MoPEC/SIA **25–40**; Minergie **20–30**; Minergie-P 8–20.
1990s **30–40** (supplied by spec v2; my earlier 32–45 interpolation is retired).

**Standard usage, SIA 380/1 Standardnutzungsdaten:** internal gains
**5.0 W/m²** (33.3 kWh/m²a); indoor setpoint **20.0 °C**; air change
**0.7 h⁻¹** natural, 0.4 with MVHR.

**Climate, SIA 2028:** `T_design` −10 °C; SIA heating limit 12.0 °C daily mean —
which independently confirms the P0 base choice.

### The five gaps — CLOSED 2026-09-10 by spec v2, with one rejection

| was | now |
|---|---|
| GSHP + radiators JAZ | **supplied and REJECTED — see below** |
| solar gains | 15–25 kWh/m²·a (SIA 380/1:2016 Ziff 3.5.4); g by era 0.85/0.75/0.65/0.50–0.55; `F_g` 0.90, `F_F` 0.70–0.75, `F_S` 0.75–0.80; gain utilisation `η_g` 0.80–0.85 annual |
| DHW demand | **2.33 kWh/person/day** (40–50 L at ΔT 50 K), SIA 385/2:2015 Ziff 4.1 |
| storey height | clear 2.40–2.60 m; **net air volume 2.05 m³ per m² of A_E**; `n = 0.7 h⁻¹` applies to **NET** volume — using gross overstates ventilation loss by exactly 25% |
| Gebäudehüllzahl | SFH pre-1975 **1.80–2.20**, 1976–2000 **1.50–1.80**, post-2000 **1.30–1.50**; envelope split wall .50 / roof .22 / floor .18 / window .10 |
| *(bonus)* 1990s design load | **30–40 W/m²** — my interpolation of 32–45 is retired |

**REJECTED: GSHP + radiators JAZ = 4.4.** It would make 55 °C radiators outperform
35 °C floor heating (published 4.10–4.40), which is thermodynamically impossible
and contradicts the same table's own ASHP column (2.80 < 3.10 < 3.50 as flow
temperature falls). **Derived instead** by applying the ASHP flow-temperature ratio
to the published GSHP floor value: **3.40** radiators, **3.76** mixed. Affects
**26 households (12.4%)**, each carrying `jaz_derived = True`. Using 4.4 would have
under-predicted their consumption and surfaced them as false over-consumers.

### Two internal inconsistencies in the supplied constants — logged, not resolved

1. **Internal gains.** 5.0 W/m² continuous is 43.8 kWh/m²·a, but the same source
   states 33.3 kWh/m²·a, which is **3.80 W/m²**. Both are carried; P2 runs the
   5.0 primary and 3.80 as a sensitivity.
2. **Solar is an ANNUAL figure and solar is lowest exactly when heating is
   needed.** Using an annual mean overstates winter gains. P2 therefore computes
   the balance temperature on internal gains only and **declares the omission**.
   The measured consequence is a +1.6 °C offset — see the P2 failures below.

**Still true: page-level citations now exist for every constant, but the documents
themselves have not been read here. Values are second-hand.**

## Data completeness tiers and the per-household band

**Settled 2026-09-10.** The spec's flat 1.5σ threshold for all households is
**wrong here and is replaced.**

Why, plainly: guessing a man's weight. Knowing only "adult male" gives 60–110 kg.
Add height: 70–95. Add waist and build: 78–86. Same guess, tighter as you learn
more. He steps on the scale at 90 kg — inside the vague range, outside the precise
one. **Same 90 kg, opposite conclusion, and the difference is how much you knew
about him, not how heavy he is.**

A flat threshold punishes well-documented houses and lets poorly-documented ones
hide. Given `rated_cop` is present for **56 of 214**, most houses are the vague
kind, so a flat threshold gets it backwards for the majority of the cohort.

**Therefore:**

1. Every household carries a `completeness_tier` recording which terms came from
   real audit values and which from declared defaults.
2. Every household carries an **uncertainty band on `E_expected`** propagated from
   that tier.
3. A household is categorised **against its own band**, never a fleet constant.
4. Every household carries per-term provenance flags. Minimum:
   `cop_source in {certified, type_default}`,
   `envelope_source in {era_plus_renovation, era_only}`,
   `dhw_source_known in {True, False}`.
5. **A household whose band is too wide to decide is declared UNJUDGEABLE and
   reaches the output as such.** It never falls quietly into "normal".

This is the S-series discipline applied to physics instead of peers: NaN is never
a category, never force a household into a level to avoid a gap, and the flag
reaches the output.

### COP — SOLVED 2026-09-10, and `Normpoint_COP` is NOT the answer

**Use field-measured seasonal performance (JAZ) keyed on `hp_type` × emitter type.
Do not use `HeatPump_Installation_Normpoint_COP`.** Three reasons:

1. **Coverage.** Stated COP 56/214, derivable from the power ratings 50, **union
   58**. `hp_type` and emitter type are **214/214**.
2. **It is not one variable.** The 58 are measured at mixed operating points —
   34 at `A2/W35`, 10 at `B0/W35`, 5 at `A7/W35`, one each at `A-7/W35` and
   `A2/W45`, and **160 do not record the point at all**. A COP at A7/W35 and one
   at A−7/W35 are different numbers in the same column.
3. **Nameplate is the wrong quantity.** It is a lab figure at one pleasant
   operating point. Real life has defrost, part-load, cycling and 55 °C DHW.
   Dividing by nameplate under-predicts electricity for **every** house.

**Working values (FAWA / WPZ Buchs field measurements, supplied 2026-09-10,
PENDING PAGE-LEVEL CITATION):**

| system | flow temp | JAZ |
|---|---|---|
| air-source, radiators | 50–55 °C | 2.80 |
| air-source, low-temp radiators | 40–45 °C | 3.10 |
| air-source, floor heating | 35 °C | 3.40–3.60 |
| ground-source, floor heating | 35 °C | 4.10–4.40 |
| DHW (any) | | 2.10–2.50 |

**GAP: ground-source with radiators has no figure** and exists in this fleet.
Do not interpolate silently — flag those households until a value is sourced.

`Normpoint_COP` is **not discarded**: it becomes a cross-check on the JAZ
assignment for the 58 that carry it, and the gap between nameplate and field is
itself a reportable finding. It is never a model input.

## The post-visit rule — settled 2026-09-10

**Fit on POST-VISIT days only for the production categorisation. Pre-visit days
are used ONLY for validation.**

Two reasons, and the second is the one that matters:

1. **The dashboard question is "who should we visit *now*."** Every household here
   has already been inspected. Ranking them on pre-visit data ranks a state that
   no longer exists.
2. **Circularity.** The recorded fault flags describe the pre-visit window. Fitting
   on that same window means any agreement is a **rediscovery of what the inspector
   already wrote down**, not a prediction.

**Correction of record — do NOT justify this as "the corrected state."** Measured
in `../STRATUM-LEVEL RESIDUAL MODEL/outputs/s10`: the visits did not measurably
move consumption. Visited vs placebo on slope change **AUC 0.474 [0.387, 0.561]**;
median difference **−0.0034 kWh/DD [−0.117, +0.074]**; 66.2% of visited houses
improved against 60.6% of placebo controls. Both drifted down together.
**Post-visit data is TODAY'S STATE, not a repaired state.** The rule stands; the
reason is recency and non-circularity, not repair.

**Measured cost**, on the 134 visited households inside the S-series scored pool,
at ≥180 days / ≥60 warm / ≥60 cold / identified slope: **post usable 96, pre
usable 104, both sides 74.** Visits cluster in Jan/Feb/Nov/Dec, so a short
post-visit record often contains **no summer at all** — and with no summer the
floor and the slope cannot be separated. **Expect roughly a quarter of the cohort
to be unscoreable. Measure the real number over the full 214 in P0; do not assume
96 transfers.**

## Validation — the flags are LABELS, never inputs

**No inspector verdict enters the model.** Specifically barred as inputs:
`HeatPump_HeatingCurveSetting_TooHigh_BeforeVisit`,
`HeatPump_HeatingLimitSetting_TooHigh_BeforeVisit`,
`HeatPump_NightSetbackSetting_Activated_BeforeVisit`,
`DHW_Storage_LastDescaling_TooLongAgo`, `HeatPump_TechnicallyOkay`,
`HeatPump_Installation_CorrectlyPlanned`, and every `*_Categorization` column.

The spec's §5 puts `HeatingCurveSetting_TooHigh_BeforeVisit` **inside**
`classify_household()`. That is marking your own exam with the answer key copied
onto the answer sheet: you score 100% and learn nothing. **It also would not
work** — 78.5% of inspected households carry at least one recorded fault, so the
flag is true four times in five and sorts nothing.

**Division of labour:**

* **Physics decides JUSTIFICATION.** Is this consumption explained by this
  building? A calculation. Needs no inspector.
* **Aaditya's models decide the FAULT NAME.** ~~The A-slot, later.~~ **REVERSED
  2026-09-12: there is no A-slot here any more.** His model keeps its own section;
  the two meet only in a final end-section overview. The division of labour above
  still holds conceptually — physics justifies, his model names — but **nothing in
  this workstream reserves, populates or displays a fault name.**
* **The inspector's flags decide WHETHER WE WERE RIGHT.** Kept clean so the
  question stays askable.

**Setpoint numbers are instrument readings and are permitted; verdicts are not.**
`HeatPump_HeatingCurveSetting_Outside0_BeforeVisit` (209/214) is a value a
technician read off a controller. `..._TooHigh_BeforeVisit` (188/214) is a human
judgement about that value. **The first may be used, the second may not.** Keep
this distinction explicit in code and in review.

Expect the same validation ceiling as next door: small n, wide intervals.
**Report validation, never gate on it. "Not shown to work, not shown to fail" is
the honest phrasing and both halves are required.**

## Population — measured, not assumed

| quantity | value | source |
|---|---:|---|
| protocol reports | 410 | `../heapo_data/reports/protocols.csv` |
| reports carrying a `Household_ID` | **217** | `s10_run.txt` §1 |
| **distinct households** | **214** | `s10_run.txt` §1, `sp0_column_census.csv` |
| households with multiple visits | 3 (first visit used, flagged) | `s10_run.txt` §1 |
| visit dates span | 2016-02-09 → 2024-02-29 | `s10_run.txt` §1 |
| inside the S-series scored pool | 134 | `sp0_column_census.csv` |
| post-visit scoreable, of those 134 | 96 | `s10_run.txt` §2 |

**The spec's "217 Protocol Households" is wrong: 217 is REPORTS CARRYING AN ID,
and there are 214 distinct households.** The spec's own arithmetic agrees — its
"1,194 control households" is 1,408 − 214. The 193 reports without an ID are
overwhelmingly 2015–2017 inspections predating the smart-meter programme. **No ID,
no join, no consumption.** Never write 217 households.

### Coverage on the 214 — the numbers that constrain the design

Source: `../STRATUM-LEVEL RESIDUAL MODEL/outputs/sp0/data/sp0_column_census.csv`.

| field | n / 214 | consequence |
|---|---:|---|
| `Building_FloorAreaHeated_Total` | 214 | area is safe |
| `Building_Residents` | 214 | baseload is safe |
| `Building_Renovated_Windows/Walls/Roof` | 214 | envelope modifiers safe |
| `HeatDistribution_System_Radiators / _FloorHeating` | 214 | emitter safe |
| `DHW_Production_ByHeatPump / _ByElectricWaterHeater` | 214 | DHW safe |
| `Building_ConstructionYear_Interval` | 212 | era safe |
| `HeatPump_Installation_HeatingCapacity` | 202 | usable |
| `Building_PVSystem_Available` | 183 | tier it |
| **`HeatPump_Installation_Normpoint_COP`** | **56** | **26% — the load-bearing denominator is mostly absent** |
| `Building_ElectricVehicle_Available` | 33, **True/NaN, zero False** | **UNUSABLE, see trap 2** |

**`Normpoint_COP` at 56/214 is the defining constraint of this workstream.**
`beta_H` divides by it. 158 households will run on a declared type-default and
must carry `cop_source = "type_default"` and a wider band. Do not paper over it.

## Corrections to the spec — twelve defects, resolved

| # | spec says | correction |
|---|---|---|
| 1 | 217 protocol households | **214 households**, 217 reports-with-ID |
| 2 | `Building_ElectricVehicle_Available` gates Category B | **Unusable**: 33/214, True/NaN, zero False. Trap 3 next door. Drop the EV term or source it elsewhere and declare it |
| 3 | flowchart: not-justified → A | **Code disagrees with its own flowchart** — §5 returns B for not-justified-but-no-setting. Pick one, write it down, and it is A |
| 4 | fault flag is an input | **Label only.** See *Validation* above |
| 5 | `Normpoint_COP` available | **56/214.** Tier it |
| 6 | `HDD_SIA = max(0, 20 − T)` when `T < 12` | Project standard is **`HDD_12`, BASE 12 °C, permanent, never fitted**. These are different quantities. **P0 must compute both and report the difference before either is adopted** |
| 7 | fit the whole record | **Post-visit days only.** 100% of this cohort is visited |
| 8 | `beta_H = U · A / COP` | **No unit conversion** (W/K → kWh/day per degree-day needs ×24/1000), **no ventilation or infiltration**, **no internal or solar gains**. Add all four, cited |
| 9 | threshold at 1.5σ of the peer group | **Reintroduces the peer group the spec opens by rejecting**, and does not say σ of what. Replaced by the per-household band |
| 10 | deduct PV self-consumption | **Unobservable.** No 15-min `kWh_returned` channel exists, and `Installation_HasPVSystem` provenance is **UNTRACED** (parent defect 4.12). Either exclude PV households or declare them a separate reported group. **Do not estimate self-consumption** |
| 11 | `eta_emitter = 0.72` for radiators (implies +39%) | **Measured next door: +66% steeper slope, +33% winter kWh/m².** Keep the constant, **report the gap as a finding.** Do not tune 0.72 to fit — that is the calibration rule |
| 12 | `HeatingCurveSetting_Outside0_BeforeVisit`, `Normpoint_COP` | **Column names are wrong.** Real names carry the `HeatPump_` / `HeatPump_Installation_` prefixes. §2 and §4.1 drop them, §5 keeps them. Verify every name against the CSV header |

## TWO BASELINES — the core design, settled 2026-09-10

**Compute two expected values, not one.**

* **`E_as_built`** — physics using the house as it actually is: its real era, real
  envelope, real capacity, real DHW, real emitters.
* **`E_reference`** — physics for the **same house, same size, same occupants**,
  properly specified: reference envelope, correctly sized pump, heat-pump DHW,
  low-temperature emitters.

| gap | meaning | owner |
|---|---|---|
| `E_actual − E_as_built` | physics cannot explain this at all | a setting fault → **Aaditya** |
| **`E_as_built` − `E_reference`** | **the cost of the building's physical deficiencies** | **ours** |

The second gap **decomposes by term**, and each term is a named physical cause
with a number and its own intervention:

| term | reads as | intervention |
|---|---|---|
| envelope / era | poor thermal insulation, X kWh/yr | insulate |
| **capacity mismatch** | pump under/oversized for this building, Y kWh/yr | replace the unit |
| DHW | electric cylinder instead of heat-pump DHW, Z kWh/yr | change the cylinder |
| emitter | radiators instead of floor heating, W kWh/yr | change the emitters |

**None of these is a controller setting. That is exactly why they are a separate
category from a setting fault.**

### WHY THE TWO BASELINES — CORRECTED 2026-09-10 BY P5. Read this, not the old claim.

**The old claim was: "a difference between two baselines sharing the same
constants is far better conditioned than either level." P5 MEASURED IT AND IT IS
FALSE.** Median relative 95% width: `E_as_built` **0.28**, `E_reference` **0.18**,
**deficiency 0.94**. The difference is **3.4× worse in relative terms**, not
better. Classic catastrophic cancellation — subtracting two large similar numbers
leaves a small one whose absolute error barely shrank while its denominator
collapsed.

**The two-baseline design is still right, for a DIFFERENT reason.** There are two
distinct error sources and the old claim conflated them:

| error source | what the difference does to it |
|---|---|
| **systematic bias** — `E_as_built` omits all appliance electricity, which no SIA heating standard supplies | **REMOVED.** It is identical in both baselines and subtracts out exactly. This is the real justification. |
| **propagated constant uncertainty** — the published spread on U, JAZ, geometry | **AMPLIFIED in relative terms** (0.28 → 0.94), partly reduced in absolute terms (median band 1,113 kWh) |

So: the level is unusable per household because of an **unmodelled bias** (P4 §3 —
implied appliance load 897 to 14,878 kWh/yr). The difference removes that bias and
is therefore the right quantity — **but it is not a precise quantity**, and every
deficiency figure must travel with its band.

**Never repeat the variance-cancellation argument. It is measured false.**

**The one policy choice: what counts as "properly specified."** It is declared out
loud, defended, and taken from a standard — **never** from looking at the
consumption data. Current setting: SIA 380/1 target values, with TABULA's own
`> 2010` overall mean as the area-weighted reference envelope.

## Categories — reordered 2026-09-10, NORMAL LAST

> **THE A/B/C/D 2x2 BELOW IS NOT WHAT SHIPS. Superseded 2026-09-12.** Its
> horizontal axis is Aaditya's setting-fault axis, which was **removed from this
> workstream** — so A and C cannot be populated here and never will be. **What
> ships is the four states of `physical_baseline_v2`** (`HIGH_EXCESS`,
> `EXCESS_CONFIRMED`, `INCONCLUSIVE`, `INCOMPLETE_AUDIT`) plus the three groups —
> see P26 and `outputs/export/SCHEMA_v2.md`. The 2x2 is kept because the
> COMPENSATING / COMPOUNDING distinction below it is still the reason the two
> baselines exist, and that argument is unaffected.

Two independent axes. Aaditya owns one, we own the other. **The S-series letters
mean something different; never quote counts from the two workstreams side by
side without saying which method produced them.**

| | **no setting fault** | **setting fault (Aaditya)** |
|---|---|---|
| **no physical deficiency** | **D** — normal | **A** — adjust the setting. Cheap, and it sticks. |
| **physical deficiency (ours)** | **B** — capital work: insulate, resize, change cylinder | **C** — both |

Plus **U — unjudgeable**: band too wide to decide, or no scoreable record. It
reaches the output as such and **never falls quietly into D**.

### C is the class this workstream exists to produce

**A setting fault can be a rational response to a physical deficiency.** A house
is badly insulated, or its radiators were sized for a 70 °C oil boiler. The
occupants are cold, so someone turns the heating curve up. The inspector writes
"heating curve too high" — and it is too high, **and it is also doing its job**.
Turn it down and the house gets cold and the occupant turns it back up.

**The two baselines settle which it is:**

* `E_actual ≈ E_as_built`, far above `E_reference` → **COMPENSATING.** The house is
  expensive to heat and is being heated about as much as it needs.
  **Do not just turn the setting down.**
* `E_actual` far above **even** `E_as_built` → **COMPOUNDING.** Deficient building
  *and* genuinely over-heated. Fix the setting first, it is free, then plan the
  capital work.

C carries a `compensating` boolean. It is a computation, not a judgement.

**This may explain S10's null result.** The visits did not move consumption
(AUC 0.474, median −0.0034 kWh/DD). If many "corrected" heating curves were
holding up a deficient building, they either reverted or left the occupants cold —
and either way consumption does not fall. **Testable on data already on disk:**
among households with `HeatingCurveSetting_Changed = True`, do those with a
computed physical deficiency show *less* post-visit reduction? Not yet run.

~~**Aaditya's model exists now. Integrate it LAST** (Miguel, 2026-09-10). Until
then A and C are defined but unpopulated, and B and D are fully computable
without it.~~

**REVERSED 2026-09-12 by Miguel — DO NOT INTEGRATE IT HERE AT ALL.** It was
integrated on 2026-09-11 (P12/P13) and then removed: no fault column survives in
`physical_baseline_v2` (asserted on write), `p13_visit_queue.py` v2 is fault-free,
and `models.joblib` is loaded nowhere in this workstream. **A and C stay
permanently unpopulated here**; B and D's content ships as the four `phys_status`
states. A fault percentage may sit beside this model's columns in the final
end-section overview — never inside its scoring, ranking or two pages.

## P2 results — what ships and what does not, 2026-09-10

Full record: `outputs/p2/reports/p2_findings.md`. **209 households modelled, 203
with consumption. Decomposition exact to 0.000000 kWh.**

**PASSES.** Reference envelope agrees across two independent standards (SIA 380/1
area-weighted **0.269** vs TABULA `>2010` **0.20–0.28**). Design-load cross-check
agrees within 3% for post-2000 buildings. Implied non-heating electricity has the
right magnitude — **median 3,052 kWh/yr** against a Swiss norm of ~3,500–4,500.

**Fleet deficiency 942,634 kWh/yr over 203 households.** Envelope **86.3%**, DHW
8.3%, emitter 6.0%.

**Ventilation dominates in new buildings** — a `>2010` house has transmission
0.34 W/m²K against ventilation **0.49**. Invisible to any peer model.

### THREE FAILURES — read before quoting any number

**F1. The design-load cross-check breaks for old buildings.** Ours vs SIA 384.201:
`>2010` **0.99**, `2000–10` **0.97**, 1990s 1.20, 1976–90 1.21, **`<1975` 1.59**.
The two supplied sources are **mutually inconsistent for pre-1975 stock**.
Consequence: **the pre-1975 deficiency figures (median 9,832 kWh/yr, 68.6% of
consumption) are likely overstated, plausibly by ~1.5×.** Never quote them without
this caveat. **Not licence to tune either source.**

**F2. The computed balance temperature is NOT validated. Do not ship it.**
Against the fitted changepoints (n=144 qualifying): computed median 17.2 °C,
fitted 15.2 °C, **correlation −0.016** — essentially zero. It also has **no
within-era variation at all**: area cancels algebraically, so `T_bal` is an era
lookup with five values, not a household quantity. Using it gave old houses base
18 °C and so **amplified** their deficiency on top of the U difference, which is
unsupported. **Recompute on the fixed `HDD_12` from P0.** (This comparison is a
validation, not a calibration — nothing was tuned to `tau`, and nothing may be.)

**F3. The LEVEL is unusable per household.** Implied non-heating electricity:
median 3,052 kWh/yr but 5–95% **−6,555 to +11,400**, min −29,716. **The median
lands on the right physical quantity; the individuals do not.** `E_as_built` is
never a per-household prediction. **Only the difference ships.** This is the
level-versus-difference argument, now measured rather than asserted.

### Also

`> 2010` gets a **negative** median deficiency (−92 kWh/yr). Correct, not a bug:
TABULA's `>2010` stock (0.24) beats the SIA 380/1 target (0.269), so **the
reference is not an upper bound** and negative reads as "already better than
reference".

**The capacity term is detected (P1, AUC 0.772) but NOT PRICED.** Cycling losses
from oversizing are not in a steady-state model and no derating source exists.
Category B carries envelope, emitter and DHW in kWh, and capacity as a flag with
no kWh figure.

## P3 — GEOMETRY IS NOT AN ERA PROPERTY, 2026-09-10

Full record: `outputs/p3/reports/p3_findings.md`. **191 households.**

**Use the audited per-storey areas, never an era lookup, for the
Gebäudehüllzahl.** `protocols.csv` records floor area per storey and it reconciles
to the total at median ratio 1.000 (190 of 193 within 5%).

**Within-era spread is ~2×** — pre-1975 runs 1.23–2.32 at 5–95% where the lookup
says a flat 2.00. Two houses of the same age and same heated area differ by twice
in envelope area. First-order, and the lookup cannot see it.

**The Gebäudehüllzahl is NOT era-dependent in this fleet** — measured medians run
1.70–1.90 across every era with no trend, while the SIA lookup imposes 2.00 →
1.40. **Shape barely changed by era; insulation did.** Assigning it by era imports
a **spurious era trend** that inflates old-versus-new differences, and **part of
P2's pre-1975 1.59 gap is that artefact, not the U-values.**

**The design-load disagreement became UNIFORM, which is what matters.** Era lookup
ratios spanned 0.97–1.59 (range 0.62); real geometry spans 1.10–1.42 (range 0.32).
**A uniform offset largely cancels in the two-baseline difference; an era-varying
one does not.** The old "perfect agreement" at 0.97/0.99 was two errors of
opposite sign cancelling in the modern eras only. A residual uniform ~1.2–1.3
remains, unexplained.

**THE BALANCE-TEMPERATURE ROUTE IS DEAD.** Real geometry gave `T_bal` 45 distinct
values instead of 5, and the correlation with the fitted changepoint **did not
move off zero**: −0.016 → −0.066. It fails for a reason other than geometry —
probably occupant behaviour, or noise in `tau` itself (parent ICC 0.59).
**Fixed `HDD_12` from P0 stands. Never ship a computed per-household base.**

**OPEN DEFECT — basement handling is wrong.** `n_above` counts only above-ground
storeys but `Building_FloorAreaHeated_Total` includes the heated basement, so a
bungalow-with-basement is scored as 1 storey while carrying two storeys of area.
Basement walls against earth are ignored entirely. **73 of 214 have a heated
basement.** The storey-count table in P3 §5 reads backwards because of this and
**must not be quoted**. The within-era spread and era-independence findings
survive — they concern variation and trend, not level. **Fix before P4.**

**Ranking rule, settled:** **rank WITHIN era.** A common inflation factor cannot
reorder a list, so within-era ranking is safe under P2's F1. A single fleet-wide
list is not, until the residual offset is resolved.

## P4 — SUPERSEDED BY P6. Kept for the audit trail.

**P4's numbers are VOID: they predate the HDD bias correction and the footprint
fix. The current deliverable is `outputs/p6/data/p6_category_b_final.csv`.**
P4 remains on record because it is where the two-baseline model first ran end to
end and where the sizing validation replicated. Read its numbers as history.

Full record: `outputs/p4/reports/p4_findings.md`. Output
`outputs/p4/data/p4_category_b.csv`. **189 households, 183 with consumption.**

Everything settled applied at once: **fixed `HDD_12`**, audited per-storey geometry
with the **basement defect fixed**, per-household Gebäudehüllzahl, TABULA as-built
vs SIA 380/1 reference U, derived GSHP+radiator JAZ, **ranked within era**.

**Fleet deficiency 454,840 kWh/yr.** Envelope **79.9%**, DHW 14.7%, emitter 5.4%.
Median household 1,838 kWh/yr. Decomposition exact to 0.000000 kWh.

**P2's 942,634 kWh/yr is VOID** — inflated by the dead balance-temperature route,
which gave old houses a base of 18 °C and so far more degree-days. Never quote it.

**The basement fix worked.** Storey table now physically correct: 1 storey
Hüllzahl **2.34**, 2 storeys 1.89, then flat (1.91, 1.90) — correct, because beyond
two storeys added wall trades off against reduced roof and ground contact.
**71 of 189 (37.6%) have a heated basement.**

**Physical plausibility now PASSES.** Implied non-heating electricity 5–95%
**897 to 14,878 kWh/yr, no impossible negatives**, against P2's −6,555 to 11,400.
Median 5,365 is above the Swiss norm of ~3,500–4,500 and that is **unexplained**;
P4 trades a slightly high median for a distribution with no impossible values,
which is the better failure mode.

**OVERSIZING REPLICATES ACROSS TWO INDEPENDENT DERIVATIONS** — the strongest
evidence this workstream has produced:

| | required kW from SIA 384.201 (P1) | required kW from our own physics (P4) |
|---|---|---|
| **oversized** | 0.772 [0.649, 0.883] | **0.786 [0.675, 0.878]** |
| either direction | 0.685 [0.574, 0.780] | **0.484 [0.358, 0.612]** |

**Report oversizing only. DROP the either-direction test** — it does not replicate,
mixes both directions with 8 no-direction cases, and collapses to chance.

### Standing defects

* **Design-load offset 1.13–1.49, range 0.36.** Roughly uniform, so it largely
  cancels in the difference. Unexplained. **Not licence to tune.**
* **Capacity is detected but NOT PRICED** — cycling losses are absent from a
  steady-state model and no derating source exists. Flag only, no kWh.
* **25 of 214 dropped** for missing footprint/era/residents/emitter/HP type.
  **Report as unjudgeable, never as normal.**
* **Cross-era comparison unsafe.** Within-era ranking is the shipped form.
* `b_ground = 0.5` is sourced to SIA 380/1 / 384.201 (ground swings roughly half of
air); section number outstanding. 26 households on a **derived** JAZ.

## P5 — THE BAND, MEASURED. And the architecture split, built.

Full record: `outputs/p5/reports/p5_findings.md`. **183 households × 400 draws
over the published spread of every constant.**

**`p_physics.py` + `p_adapter_heapo.py` now exist.** The physics holds the formula,
the constants with bands and sources, and the sampler, and contains **no HEAPO
column name**. The adapter is binding #1. **The portability requirement is met in
code, not only in intent.** Every new rung builds on these two, never on a fresh
copy of the constants.

**Band: median 1,113 kWh/yr against a median deficiency of 1,686. Decisive
(whole 95% band above zero) 165 of 183 = 90.2%.**

**90.2% is not a selective gate** — it answers "can we say anything at all", not
"is this worth acting on". **Confirms: the B/D line cannot be a statistical
threshold.** A relative gate is worse — +15% selects 85.2% of the fleet.

**The tiers work**, and consistently within era (1976–1990: T1 848, T2 1,510,
T3 2,125 kWh). T1 n=100, T2 n=68, T3 n=15. T1's low *decisive* rate (83%) is not a
flaw — 17 of the 18 non-decisive households are post-2010, unrenovated hence T1,
and correctly at zero deficiency.

**RANK ON `deficiency_lo`, the 2.5th percentile — not the point estimate.** The
honest "at least this much", and it penalises poorly-documented houses instead of
rewarding them for vagueness. Costs little: 9 of the top 10 are unchanged.

**Pre-1975 carries a band as large as its own deficiency** (3,899 vs 3,690) —
biggest numbers, least certain. Both facts travel together, always.

**24 of 214 are unjudgeable** with declared reasons; **21 of them lack per-storey
geometry.** The dominant loss is geometry, not consumption.

## P6 — THE HDD BIAS. Revises every earlier number. 2026-09-10

Full record: `outputs/p6/reports/p6_findings.md`.

**`hdd_per_day × 365` systematically OVERESTIMATES annual degree-days.** A record
of one to one-and-a-half years covers **two winters and one summer** and reads far
too cold. Measured on 1,032 households carrying a complete calendar year:

| record length | median est/true |
|---|---:|
| **365–548 days** | **1.252** |
| 548–730 | 0.956 |
| 730–1095 | 1.112 |
| 1095+ | 1.077 |

Weather only — **no consumption enters, so the calibration rule is not engaged.**
Now in `p_physics.HDD_SAMPLING` / `hdd_correction()`, applied to the point estimate
and sampled in the Monte Carlo.

**EVERY DEFICIENCY FIGURE IN P2, P4 AND P5 IS INFLATED. Fleet total 454,840 →
321,330 kWh/yr, −29%.** Median household **1,609**. **155 of 172 decisive.**

*(Reconciled 2026-09-10 after `p_pipeline_test.py` forced the geometry fix below;
P6's first pass reported 317,947 / 1,590 / 154 of 171 on the old footprint rule.)*

**EXTRAPOLATION, declared:** the bins were measured on 365+ day records, so
**anything shorter uses an extrapolated correction**. `897731` (212 days) is in the
current top 10 on that basis, with the widest band in it (9,043 on 7,435). Mark
it; do not trust it.

### The window rule — SETTLED

**All days for Category B. Post-visit for the meter-based axis (A and C).**

**Category B never reads the meter** — it is computed from geometry, era, JAZ,
residents and HDD, and HDD is a *weather* quantity. The non-circularity argument
that justified post-visit binds on A and C, where a consumption fit could
rediscover what the inspector wrote. There is no such fit here.

Measured: on the 145 in both windows, **Spearman 0.9913**, deficiency ratio 1.000.
The post-visit rule is a **pure calendar filter** — every excluded household was
visited in 2023 or 2024, none before. It cost 27 households (−15.7%) to move the
ranking by 0.008 (Spearman **0.9916**).

**They are retained.** After the bias correction they are ordinary — comparable
medians and near-identical bands — and their share of the top 20 falls from 4 to 2. **Two unrelated problems pointed the same way** — the calendar rule
would have been right by accident and wrong in method.

### PV — SETTLED

**Keep PV in Category B. Exclude PV from any meter-based comparison.**

21 True / 99 False / **25 Unknown** — absence is not "no PV" (parent trap 3).
Deficiency by level: PV 1,522, no PV 1,356, Unknown 2,016 — materially the same.
Implied appliance load: PV **3,679**, no PV **5,980** — PV sits ~2,300 kWh/yr
lower, the invisible self-consumption appearing exactly where theory predicts and
nowhere else. **The bias is real and it lands on a quantity Category B never uses.**

## P7 — THE COMPENSATION TEST: NOT SHOWN, 2026-09-10

Full record: `outputs/p7/reports/p7_findings.md`. **83 households both sides
sufficient at strict 180/60/60; 52 curve changed, 26 left alone.**

**The C-class mechanism was tested and is NOT confirmed.** Do not present it as
established. **Defensible on mechanism, unproven on evidence** — unchanged from
what this file already claimed.

**Predicted pattern, on the right parameter:** among houses whose curve WAS turned
down, low-deficiency houses dropped **−11.74%** on the heating slope, high-
deficiency houses **−0.65%**. AUC **0.596 [0.436, 0.759]**, Spearman **+0.276**.
It lands on the *slope*, which is what a heating curve controls, and not on the
level (AUC 0.536, rho +0.117) — the mechanistically correct place.

**And the falsification arm stops the claim.** The same split on the 26 houses
whose curve was LEFT ALONE: slope AUC **0.562 [0.320, 0.775]**, level **0.627
[0.396, 0.840]**. **Deficient houses drift upward even when nothing was changed**,
and on the level the control arm exceeds the treatment arm. **§4 may be measuring
drift, not blunting.**

**S10's null is NOT explained.** Compensation remains a candidate, now tested once
and not confirmed.

**New, logged not chased:** a possible drift effect — households with a large
computed deficiency appear to trend upward regardless of intervention. Untested;
plausibly regression to the mean or an age correlate.

**Also confirmed here:** the curve change itself is not separable from drift —
changed vs unchanged, slope AUC 0.501 [0.368, 0.637], level 0.408 [0.276, 0.547].
Consistent with S10's 0.474.

## P8 — CAPACITY PRICED AS A SCENARIO, NOT MEASURED. 2026-09-10

Full record: `outputs/p8/reports/p8_findings.md`. **160 households.**

**Nothing in P8 is measured.** Sources give a penalty RANGE (5–15%, FHNW / BEYOND
/ Brudermueller) but **nothing maps sizing ratio to a penalty**, so the shape is
assumed and declared: zero at ratio 1.0, linear to full at 2.0, flat above.

| d_max | fleet kWh/yr | median household |
|---|---:|---:|
| 5% | 3,825 | **0** |
| 10% | 7,650 | **0** |
| 15% | 11,476 | **0** |

**Fleet level: small.** 2.6% of the measured deficiency, an eighth of DHW, a
thirtieth of the envelope. **Household level: concentrated.** The median carries
zero (half the fleet is at or below required capacity), but **52 of 160 exceed
their own DHW term and 17 exceed their own ENVELOPE term.**
**Report capacity per household, never as a share of the total.**

**Category B ships envelope + emitter + DHW. Capacity ships as a separate,
labelled scenario column and is NEVER summed into the headline.**

**The sizing ratio median is 1.00 on our own physics against 1.30 on the SIA
384.201 table.** Both cannot be right; the gap is the unexplained design-load
offset. **Neither settles the other — it is circular to claim so.**

**The P8 validation AUC of 0.793 is CIRCULAR and must not be quoted as a third
confirmation.** The cost is a monotone function of the ratio, and P1/P4 already
validated the ratio against that same flag. Independent evidence would require
disaggregating real cycling from the 15-minute meter — meter-based work, A/C axis.

## P9 — term_envelope IS VALIDATED ON RANK. 2026-09-10

Full record: `outputs/p9/reports/p9_findings.md`. **172 households.**

**The term carrying 75–80% of the deficiency is no longer unvalidated.**
Oversizing (AUC 0.772/0.786) only ever validated the *capacity* term — 2.6% of the
total, shipped as a scenario.

| | Spearman | 95% CI |
|---|---:|---|
| raw physical vs measured slope | +0.540 | [+0.419, +0.648] |
| **area alone** | +0.292 | [+0.145, +0.432] |
| **per m² — THE TEST** | **+0.536** | **[+0.422, +0.645]** |

**Per m² the physical prediction varies ONLY through era, renovation and the
geometric Gebäudehüllzahl — nothing left to borrow from — and it still tracks the
meter at ρ 0.54.** The raw figure would have been inflated by house size; area
alone reaches only +0.292, so the agreement is not an area artefact. **Always do
this test per m².**

### The magnitude test — not rejected, but the era gradient is TOO STEEP

pre-1975 over post-2010, slope per m²: physics **3.38×**, meter **2.50×**
[1.68, 3.45]. Inside the interval, at the top edge.

| era | measured / physics |
|---|---:|
| pre-1975 | **0.97** |
| 1976–1990 | 1.26 |
| 1991–2000 | 1.24 |
| 2001–2010 | **1.53** |
| post-2010 | 1.31 |

**Physics matches pre-1975 almost exactly and under-predicts every newer era by
24–53%.** A gradient error, not noise: the U-value spread across eras is too
steep. Candidates, untested — thermal bridging, the design-vs-actual performance
gap in new build, unmodelled mechanical ventilation, higher setpoints in
comfortable houses.

**DO NOT ADJUST THE CONSTANTS TO CLOSE THIS.** Calibration rule. It is a finding
*about* the constants.

**Consequence: newer houses are UNDER-stated and the cross-era tilt toward
pre-1975 is EXAGGERATED. Reinforces: rank within era, never across.**

**Overall the physics runs ~22% below the measured slope** (ratio 0.78), and 0.83
on the sub-metered channel — same direction. Unexplained, untuned.

### Two negatives, both kept

**Sub-meter check: n=18.** ρ +0.342 [−0.133, +0.744], crosses zero, underpowered
exactly as predicted before running. 72 households have `kwh_hp`, 63 clear
180/60/60, **only 18 are also modellable here.** The overlap between sub-metering
and the protocol cohort is the ceiling, not our modelling.

**Consultant consumption rating: NULL.** `term_envelope` is flat across normal /
rather high / rather low (1,132 / 1,188 / 1,179 kWh/yr). The *measured* slope does
order correctly, so the rating tracks consumption — unsurprising from someone who
had seen the bills. **It rates CONSUMPTION, not envelope, and was never envelope
validation. Do not quote it as such.**

## P10 — PORTABILITY DEMONSTRATED, not claimed. 2026-09-10

Full record: `outputs/p10/reports/p10_findings.md`. **23 checks, 23 passed.**

Three bindings run end to end, **`p_physics.py` untouched for all three**:

| binding | rows in | modellable | outcome |
|---|---:|---:|---|
| #1 `p_adapter_heapo.py` | 214 | 190 | the live deliverable |
| #2 `p_adapter_synthetic.py` | 120 | 120 | round trip, all exact |
| #3 `p_adapter_meta.py` | **1,358** | **0** | **REFUSED — 5 roles absent** |

**Binding #3 is the point.** `meta_data.csv` covers six times the protocol cohort
and **cannot drive this model**: no construction era, no per-storey geometry, no
renovation flags, no basement. Nothing invented or defaulted; `evaluate()` raises
rather than guessing. **A contract that only ever says yes is decoration.**

It also puts the generic-versus-specific split into code — **`meta_data` is what
the PEER model runs on; the physical model needs someone to have walked through
the building**, and the contract now says so before a number is computed.

**The round trip caught its own author.** The envelope check first failed at
−98.66 vs −106.26 kWh/yr — a 7% gap that was **exactly the HDD correction**, live
inside `evaluate()` while the hand arithmetic used raw degree-days. Model right,
test wrong. A check that the correction is in the path (`4.000 → 3.714`) is now
permanent.

**Synthetic probes outside HEAPO's range on purpose** — Hüllzahl to 3.61 against
HEAPO's real max 2.96, because a small bungalow genuinely is nearly all roof and
floor. That is what a synthetic binding is FOR.

### What it does NOT prove — say this whenever portability is claimed

**Synthetic proves the INTERFACE travels. It cannot prove the CONSTANTS travel.**
TABULA, SIA and FAWA/WPZ are **Swiss**. A foreign fleet needs its own typology and
its own field JAZ, and the era bands would not mean the same thing.
**Still absent: a second REAL dataset with audit-level building data.** The three
roles that blocked `meta_data` — era, per-storey geometry, renovation — are
exactly what such a dataset must carry.

## Notebooks — the per-stage rule, and a declared deviation

**`p_notebook.py` builds `outputs/deliverable/DELIVERABLE_physical_baseline.ipynb`**
— 16 cells, **5 embedded figures**, covering the LIVE chain: constants with
sources, deficiency by era with bands, term decomposition, the ranked queue,
tier widths, and the compensation test.

**DEVIATION, DECLARED: P0–P4 get no notebook and will not.** P4 is marked VOID and
P2 with it, both superseded by the HDD correction and the footprint fix. **A
notebook for a dead number documents nothing and invites someone to quote it.**
P0, P1 and P3 survive as reports whose findings are folded into the deliverable
notebook.

**`matplotlib` 3.11 renamed `boxplot(labels=)` to `tick_labels=`.** The old
keyword now raises. Noted because every future figure script will hit it.

## P11 — THE DASHBOARD EXPORT. Model finished for integration. 2026-09-10/11

**`outputs/export/physical_baseline_v1.csv` / `.parquet` + `SCHEMA.md`.**
214 rows x **47** columns, `p11_export.py`, **26 self-validation rules passing on write**
*(was 38 columns / 19 rules before the visit axis landed — see THE VISIT AXIS IS IN
THE EXPORT)*.

**THE CONTRACT IS THE SCHEMA, NOT THE NUMBERS.** Columns, units and meanings are
frozen at v1; values are expected to move — this model has revised its own totals
twice. **Bind the dashboard to columns, never to a number in a report.** Breaking
changes bump to `v2` with both shipping for one cycle; additive columns do not.

### FOUR STATES, AND NONE OF THEM SAYS "NORMAL"

| state | n | meaning | action |
|---|---:|---|---|
| **`HIGH_EXCESS`** | 41 | confirmed excess, worst 25% of its era | **act** |
| **`EXCESS_CONFIRMED`** | 114 | confirmed excess, below the action cut | real, not first |
| **`INCONCLUSIVE`** | 17 | computed, band straddles zero | **no claim** |
| **`INCOMPLETE_AUDIT`** | 42 | never computed, building data missing | **fixable — go record it** |

**There is no "normal" state and there never will be.** It would require a
household's whole band to sit at or below code and **not one does**. We can
*confirm an excess*, never *confirm its absence*. **The low end is the absence of
a finding, not a verdict.**

**"Excess", not "below code".** *Below* reads both ways — a user can take it as
*under the threshold*, i.e. good. *Excess* can only mean more than it should be.
A rule now asserts no status contains the word "below".

**The two no-result states are SEPARATE because the actions differ**, and
`phys_no_result_is_fixable` carries it so the dashboard need not parse text.
`INCOMPLETE_AUDIT` is fixable — 42 households where the audit did not record era,
per-storey geometry or renovation. `INCONCLUSIVE` is not.

**NEITHER NO-RESULT STATE MAY RENDER GREEN.** 59 households have no finding. That
is not the same as being fine, and a colour scheme will want to treat it as such.

**NO SINGLE LETTERS ON THIS AXIS.** An earlier version used B/D/U here while
`combined_category` uses A/B/C/D for the 2x2 — the same letters meaning different
things in adjacent columns, the exact collision this file has a rule against.
A test now asserts every status is longer than two characters.

### Numbers

**Confirmed excess 220,959 kWh/yr on the lower bound**, of which **`HIGH_EXCESS`
is 111,115 across 41 households. Quote the lower bound.**

**`phys_deficiency_pct_of_reference`** reads where kWh cannot — *"+20% over code"*
versus *"+208%"*. Median **+66%**, IQR 32–101%, range −4% to +233%.

**The action cut is a RANKING choice, not physics** — `PRIORITY_FRACTION = 0.25`,
worst quartile within era, adjustable without touching the model. 155 of 172
scoreable households carry a confirmed excess (90%), so a threshold would select
nearly everyone; **most Swiss housing genuinely does exceed current code.**

### Four rules enforced in the file, not left to a README

1. **All 214 households appear.** No total can hide them.
2. **Every energy figure travels with its band.**
3. **The capacity scenario is never summed into the headline.**
4. **The level is not a prediction** — it excludes appliance electricity.

### Integration slots — SUPERSEDED 2026-09-11

These were reserved empty for Aaditya's detectors. **They are now populated** —
see *THE VISIT AXIS IS IN THE EXPORT* below. `setting_fault_flag` and
`setting_fault_name` carry the logistic model's named fault, **null where the
model never ran**. **`combined_category` was removed** and replaced by
`visit_status` in words.

### A pandas trap this run hit

**`NaN <= NaN` returns `False` in pandas, not `NaN`**, so `.fillna(True)` after a
comparison never fires. A range check appeared to fail on 42 rows when zero were
actually out of range. **`.dropna(subset=[...])` before comparing, never patch
afterwards.**

## P12 — FAULT MODELS INTEGRATED. 2x2 works; the models do not generalise. 2026-09-11

Full record: `outputs/p12/reports/p12_findings.md`. Bundle
`../Heat_Pump_Failure_Prediction/artifacts/models.joblib`, 89 train / 30 test.

### The 2x2 is populated, on 97 households, from the RECORDED protocol flags

|  | no physical excess | excess confirmed |
|---|---:|---:|
| no setting fault | **D** 3 | **B** 18 |
| setting fault | **A** 10 | **C** 66 |

**C is 68%.** Two thirds carry both a controller fault and a building materially
above code. **The cell this workstream was built to expose is the COMMON CASE.**
A is only 10 — a setting fault with no physical excess, where turning the curve
down is cheap and should stick.

**Built on the inspector's record, not on predictions.** All 214 audited
households carry the verdict; the model exists to reach the UN-audited. On this
cohort no model is needed.

### THE MODELS DO NOT SURVIVE HELD-OUT DATA

**Train AUC is exactly 1.000 for random forest and hist-GBM on all four
targets** — memorisation on 89 households x 38 features, so the train column
carries no information. **NEVER REPORT TRAIN AUC**; it will be read as accuracy.

**Eleven of twelve model-target pairs sit at or near chance on test. Six are
below 0.5.** Night setback / logistic is **0.230 [0.060, 0.460]** — significantly
WORSE than chance, interval excluding 0.5 from below.

**One genuine signal:** DHW descaling / hist-GBM **0.752 [0.536, 0.944]** — but
**n=5 test positives**, and DHW descaling is the one target that is not a
controller setting.

**Consistent with the S-series, not in conflict.** It measured the same ceiling:
largest class 43 positives, 58.8% of visits carrying 2+ faults, no inter-rater
signal, and a supervised fault classifier already tested and rejected.
**The binding constraint is the LABEL, not the algorithm.**

**Consequence: the fault axis is SCOPED TO AUDITED HOUSEHOLDS.** Extending it to
un-audited ones was the model's purpose and the evidence does not support it yet.

### The axes are NOT independent — 8 shared features

`Building_ConstructionYear`, `FloorAreaHeated_Total`, `Residents`,
`HeatPump_Installation_Type`, `HeatingCapacity`, both `HeatDistribution_System_*`,
`DHW_Production_ByHeatPump`. **Never present the 2x2 as "two independent methods
agreeing".** Measured mitigation: model scores correlate with the physical excess
at only **-0.145 to +0.185**, so the shared inputs are not dominating. That is the
strongest thing this run found in the models' favour.

### Two operational notes

**The bundle is NOT self-contained** — its pickle references `heapo_core`, so that
directory must be importable or `joblib.load` raises `ModuleNotFoundError`.

**Category C's compensating/compounding split is a PLACEHOLDER and must not be
displayed.** 63/3 on an `actual / E_as_built > 1.5` threshold that is arbitrary:
`E_as_built` excludes appliances so the ratio exceeds 1 for everyone and no
principled cut exists (P4 section 3). P7 tested the mechanism directly and
returned NOT SHOWN.

**Output `outputs/p12/data/p12_combined.csv`. NOT written back into
`physical_baseline_v1` yet** — whether the shipped export carries the record, the
prediction, or both is a decision, not a default.

## P13 — THE COMBINED VISIT QUEUE. Settled with Miguel 2026-09-11.

Full record: `outputs/p13/reports/p13_findings.md`. Output
`outputs/p13/data/p13_visit_queue.csv`. **172 households.**

**ONE ORDER, TWO kWh COLUMNS — the fault FILTER was REMOVED the same day (see THE FILTER TRAP).** Sort on the heating consumption the
building does not justify; filter on the probability of a named controller fault;
show what a technician could recover and what they cannot, **never summed.**

**NO PROBABILITY x kWh.** It would produce a number that looks like money and is
not — inheriting the 22% baseline AND a probability from models that do not
survive held-out data. Rejected explicitly.

### The recoverable quantity is the SLOPE excess, not the level

`E_actual − E_as_built` median **6,045** kWh/yr — **dominated by appliances,
unusable.** The slope excess `(beta_meas − beta_phys) x HDD x 365` median **719**.
**Appliances are weather-independent and cancel from the slope**; a heating curve
set too high raises exactly the slope. **~22% slope excess is BASELINE for
everyone (P9), not a fault — rank within era, never read it as recoverable energy.**

### The fault model: `logistic`, heating curve + heating limit — INFORMATION ONLY since the same day, no longer a filter

**Logistic because a filter needs CALIBRATED probabilities**, not because it
discriminates best — none do (P12). RF and hist-GBM reach train AUC 1.000 so their
probabilities collapse to ~0/1 and a threshold decides nothing. Share of rows at
the extremes: heating curve **12%**, heating limit **36%** (coarser).

**NIGHT SETBACK EXCLUDED from the filter, carried as advisory only.** Logistic
test AUC **0.230 [0.060, 0.460]** — inverted. As a filter it would remove exactly
the households that have the fault. `FAULT_THRESHOLD = 0.50`, adjustable.
**Model used READ-ONLY. Nothing writes to Aaditya's tree or re-fits anything.**

### The statuses — SUPERSEDED the same day: the fault no longer gates (see THE FILTER TRAP). Kept as history.

| status | n | meaning |
|---|---:|---|
| **`UNJUSTIFIED_LOAD`** | 40 | slope excess **and** a named fault — dispatch, setting named |
| **`UNEXPLAINED_LOAD`** | 32 | slope excess, model **ran**, below threshold — remote check first |
| **`EXCESS_FAULT_UNSCORED`** | 53 | slope excess, fault model **never ran** — axis unavailable |
| **`NO_SLOPE_EXCESS`** | 47 | heating response fits the building |

**A LABELLING ERROR CAUGHT BEFORE SHIPPING.** The first run had 85
`UNEXPLAINED_LOAD`; **53 carried no fault probability at all** — the models only
scored the 97 they were trained on. **Absence read as a negative finding.** Fixed
with `EXCESS_FAULT_UNSCORED` and `fault_axis_available`. **75 of 172 cannot carry
the filter.**

### The two columns must never be summed — two rows show why

**`7374981`** post-2010, **−140 not recoverable** (better than code), 3,752
recoverable, curve fault likely: **a pure technician case**. **`7771161`** 1,862
recoverable against **4,472 not recoverable** at prob 1.00: the fault is real and
fixing it leaves most of the problem in the walls. **Summing hides that the bigger
number needs a builder, not a technician.**

**Under the original gated design the two leaders, `6981151` and `680861`, were both HELD OUT** — their
probabilities were not memorised, making them the most trustworthy rows.

**Training contamination:** no over-representation at the top (75.0% vs 77.3%
base); a **modest lean across all `UNJUSTIFIED_LOAD` (82.5%)** — the direction
expected from overconfident training probabilities crossing the threshold. Every
row carries `in_training_set`.

### The dashboard's PR-AUC table is train-contaminated — never quote it

`app.py` multilabel section (≈ lines 518–535) builds `X` from **all 119**
households with no split filter; the binary section (line 330) **does** filter to
`test_ids`. So the displayed **0.895 / 0.819 / 0.812 / 0.781 are ~75% in-sample.**
Held out, the same models sit near chance. **A display fix in their app, not a
model flaw — not ours to change, but the numbers must not be quoted.**

## THE VISIT AXIS IS IN THE EXPORT. 2026-09-11

`physical_baseline_v1` now carries both axes: **214 rows x 47 columns, 26
self-validation rules passing on write.** `SCHEMA.md` documents every column.

**RUN ORDER IS p13 -> p11.** `p11_export.py` reads
`outputs/p13/data/p13_visit_queue.parquet` and **refuses to run if it is missing**.

**`combined_category` WAS REMOVED** and replaced by `visit_status` in words. It had
been reserved as letters A/B/C/D; the design settled on words, and **nothing had
consumed v1**, so it changed at no migration cost. Do this kind of change BEFORE
anything binds, never after.

*Superseded the same day — the fault no longer gates. Now **SLOPE_EXCESS 125 /
NO_SLOPE_EXCESS 47 / NOT_ASSESSABLE 42**. Table kept as history.*

| `visit_status` | n |
|---|---:|
| `UNJUSTIFIED_LOAD` | 40 |
| `UNEXPLAINED_LOAD` | 32 |
| `EXCESS_FAULT_UNSCORED` | 53 |
| `NO_SLOPE_EXCESS` | 47 |
| `NOT_ASSESSABLE` | 42 |

**Rules now enforced on write, for the visit axis:** a fault is only named where
the fault model actually ran (**absence is not a negative**); every
**status and rank never depend on the fault** (the UNJUSTIFIED_LOAD /
EXCESS_FAULT_UNSCORED rules were retired with the filter); **night setback never names the fault**; both kWh columns carry
a never-sum flag; every column is prefixed `phys_` or `visit_`.

**The dashboard reads ONE table.** Two sections on the page — building axis and
visit axis — but one file, one schema, one version.

## THE FILTER TRAP — checked 2026-09-11. DECIDED: SHOW THE FAULT, DON'T GATE ON IT.

**Miguel's decision, 2026-09-11: the fault is shown as information and never
decides status or rank.** `visit_status` is now **three** words:
`SLOPE_EXCESS` **125** (ranked within era on slope excess alone),
`NO_SLOPE_EXCESS` **47**, `NOT_ASSESSABLE` **42**. `visit_fault_probability` and
`visit_named_fault` still ride along on every row.

**Effect on the queue:** 4 of the top 12 were never scored by the fault model
and now reach the top on slope excess alone. **The new #1, `1114677`**
(post-2010, 6,162 kWh/yr), was never scored. Two HELD-OUT houses with LOW fault
probability, `881223` (0.20) and `991118` (0.22), now rank 4th and 5th - under
the gate they were pushed out. **Two rules enforce it on write:** the fault
never gates status; every `SLOPE_EXCESS` row is ranked, fault or no fault.

*The findings below are why.*

Full record: `outputs/p13/reports/p13_filter_trap.md`.

**Miguel asked whether the fault filter and the slope sort target the same
variable. RULED OUT** — fault probability vs slope excess ρ −0.39 (curve), −0.23
(limit); slope/weather features carry only 22–24% of the logistic weights.

**BUT THE FILTER PULLS AGAINST THE SORT.** The heating-curve probability is
**NEGATIVELY** correlated with slope excess. Physics predicts positive — a curve
set too high raises the slope. So `UNJUSTIFIED_LOAD` intersects two quantities
moving in opposite directions. **Not a principled gate.**

**The recorded label inverts too — REPLICATED.** Our physics slope excess vs the
inspector's heating-curve flag: **AUC 0.441** (n=97). The S-series peer slope:
**AUC 0.386, "backwards"** (`STRATUM_TRACEABILITY.md` §3). **Two independent slope
measures, same inversion. It is a property of the LABEL, not of the model.**
Candidate mechanism, untested: an over-high curve on a tight house is flagged but
barely raises consumption; on a leaky house it may be needed and go unflagged —
the compensation hypothesis (P7) from the other side.

**THE HEATING-LIMIT MODEL LEARNS DOCUMENTATION THOROUGHNESS.** Its top weights are
missingness flags. `BufferTankAvailable` is blank for 70 of 119; heating-limit
fault rate **0.45 where recorded vs 0.16 where blank** — 2.8x, from form-filling
alone. `ElectricVehicle_Available` is **18 True / 0 False / 101 missing** — the
True/NaN column flagged unusable from day one (parent trap 3). **It should never
have been a feature.**

**The model adds nothing beyond the slope:** held-out, slope alone 0.617/0.670 vs
model 0.567/0.527; on all 97 the slope alone is at chance too. **Nothing robustly
predicts the recorded fault.**

**Aaditya's model is used read-only; nothing in this workstream changes it.**

## HANDOFFS — settled with Miguel 2026-09-11

Two briefs, each for a NEW CHAT that Miguel drives.

**Handout 1 — this workstream into the dashboard. REFRESHED 2026-09-12 for v2.**
One merged notebook, `outputs/deliverable/DELIVERABLE_physical_baseline.ipynb`,
built by `p_notebook.py`: the data workflow **P0 -> P26** with the result figures
placed in their stages (24 cells, 2 figures, 0 errors). The brief tells the new
chat to add it and **`physical_baseline_v2`** as **ONE section with TWO pages** —
page 1 explains the rank and names the owner, page 2 is the single fleet-wide list
— following that app's existing page pattern. **`physical_baseline_v1` is frozen
and stale; do not bind to it.**

**Handout 2 — the S-series stratum model. SPLIT THE FLEET, DON'T COMBINE MODELS.**
Aaditya's model needs protocol fields, so it cannot run on `meta_data`-only houses.
Instead each household is scored by exactly ONE method:

| S-series scored pool, 1,127 | n | goes to |
|---|---:|---|
| audited AND assessed by the physical model | **118** | physical model (fault % attached) |
| audited but NOT assessable here | **16** | stays in the S-series |
| not audited, `meta_data` only | **993** | S-series |

**Key the split on "assessed by the physical model", NEVER "has a protocol"** —
the protocol key drops those 16 from BOTH models. **The 118 leave the S-series
DASHBOARD QUEUE, not the S-series MODEL**: its validation evidence (every AUC behind
"not shown to work, not shown to fail") is computed on audited households and must
stay. **Aaditya's model never enters the S-series.**

**Reconciliation — the S-series queue after the split, per baseline:** A 102 -> 90,
B 68 -> 60, C 957 -> 859; 1,127 -> 1,009. The 118 leaving are S-series A 12 / B 8
/ **C 98**, and physically `EXCESS_CONFIRMED` 78 / `HIGH_EXCESS` 25 /
`INCONCLUSIVE` 15.

**98 of the 118 are S-series category C, "nothing material" — and the physical
model confirms an excess in 103 of them. NOT a contradiction:** the peer model asks
"above comparable houses?" (an old leaky house among old leaky peers looks
ordinary); the physical model asks "above a code-compliant version of itself?"
(the same house is far above). **This is the concrete reason each house is scored
by one method and the two are never combined.**

**Edge, decided by the rule:** the 15 `INCONCLUSIVE` go to the physical model and
show "no finding" there. Routing them back to the S-series is Miguel's call, not
taken.

**Files:** `HANDOFF_dashboard_integration.md` (this workstream) and
`../STRATUM-LEVEL RESIDUAL MODEL/HANDOFF_split_with_physical_model.md`.

**Dashboard-facing framing of Aaditya's model — SUPERSEDED 2026-09-12: it is not
framed here at all, because it is not here.** Miguel reversed the 2026-09-11
"neutral, added as a percentage alongside" arrangement: his fault prediction is
**removed from this workstream's export, notebook and pages**, and the two models
meet only in a final end-section target overview. No column in
`physical_baseline_v2` contains "fault" (asserted on write). The measured findings
about his model stay in this file and the P12/P13 reports as history.

> *Superseded wording, for the audit trail:* "Dashboard-facing framing of Aaditya's
> model: NEUTRAL. Miguel 2026-09-11 — the notebook and both briefs say the queue is
> ranked by slope excess and his fault probability is added as a percentage
> alongside. They make no claim about his model either way."

## P14 — LIMITATION 1: the appliance term. PARTLY SOLVED. 2026-09-11

Full record: `outputs/p14/reports/p14_findings.md`.

**`p_physics.appliance_electricity(residents)`**, source **BFE/EnergieSchweiz
Faktenblatt 08.2021 Tab 1** (2019 data): EFH 4 P **4,048 kWh/yr**, ±593.5/person,
−50/person from five. **Excludes heat pump, electric heating and electric DHW**, so
nothing double-counts. Band = 2019 edition to S.A.F.E./Nipkow 2013 (2011 data),
**a declared edition spread, not a household spread** — none is published.

**Kept OUT of `evaluate()`**: it cancels in the deficiency, and drawing it inside
would shift every Monte Carlo stream. Section J of `p_pipeline_test.py` pins it;
**112/112 green, every P6 number unchanged.**

**Level, like-for-like on the household's own days, PV False n=117:** residual
median **5,933 → 2,631 kWh/yr** with the term. Measured/predicted **1.30**. Per m²
Spearman **+0.566** vs area alone +0.301. **Only 31/117 inside the band.**
**Sub-meter (n=20):** the term does not rank households (ρ ≈ 0) and runs ~29% low
on the non-PV median.

**The level is still NOT a per-household prediction** — occupant behaviour is the
dominant spread and no band carries it. **"Outside the band" is never a fault.** The
difference stays the only quantity that ships. PV True reads 1.00 because
self-consumption hides the gap — never quote it.

**Not in the export.** Whether the level ships as an info column is Miguel's call.

## P15 — LIMITATION 2: the design-load offset. PARTLY EXPLAINED. 2026-09-11

Full record: `outputs/p15/reports/p15_findings.md`. 190 households, nothing tuned,
`p_physics` unchanged.

**Spec v3's α_oversize = 1.25 is REJECTED** — installer oversizing is installed ÷
required; this offset is two calculations of *required* disagreeing, and 1.25 is our
own measured midpoint.

**Half of it is a convention mismatch.** Our design load uses the ANNUAL-ENERGY air
change (SIA 380/1, 0.7 h⁻¹); EN 12831 design load uses n_min **0.5**. Ground via
EN 12831 f_g1·f_g2 (f_g1 1.45 **PENDING VERIFICATION**, T_me from the weather file)
gives b 0.443 vs 0.50. Fleet median **1.23 → 1.13 → 1.12.**

**The remainder is NOT uniform:** post-2000 now 0.96–1.03, pre-2000 **~1.18**. Range
across eras 0.18 → 0.23. **"Largely cancels" is weaker than P3/P4 claimed** — still
true for the envelope difference, not for the capacity scenario.

**The table and the meter disagree with each other in opposite eras:** pre-1975
physics matches the meter (0.97) but sits 18% above the table; post-2000 it matches
the table but sits 24–53% below the meter. **The design-load table is a cross-check,
never a validation target for the energy model.**

**The live offset is 1.13–1.31**, not P4's 1.13–1.49 (pre-footprint-fix, superseded).

**Open, Miguel's call:** compute `design_kw` with EN 12831 conventions? Changes the
P8 capacity scenario only.

## P16 — LIMITATION 3: thermal bridges. PARTLY. 2026-09-11

Full record: `outputs/p16/reports/p16_findings.md` (read its P17 addendum).

**Spec v3's γ(>2000) = 1.30 is REJECTED** — it sits inside P9's ratios, calibration
with a citation. Setpoint rebound cannot enter: base fixed at 12 °C.

**TABULA Common Calculation Method eq. 4 / Table 3: thermal bridging is a SEPARATE
surcharge ΔU_tb on all U-values**; element U excludes it; `p_physics` never carried it.
Worked example 0.10 (= DIN 4108 Bbl 2 stock default). Low/high category values and
"CH U-values are element values" are **PENDING VERIFICATION**.

On P9's line slope ΔU_tb 0.10 narrows the era range 0.56 → 0.43, ρ unchanged. **On
P17's step slope** pre-1975 goes 0.80 → 0.74 (over-predicted), range 0.52 → 0.40,
2001–2010 stays the outlier. **The era gradient survives every sourced term.**

**0.05 lands the level on 1.009 — TRAP 4, never a reason to choose it.**

Deficiency: same ΔU both sides → **exactly unchanged**; as-built 0.10 / reference
0.05 → +9.1%, a declared reference choice. **Miguel's call.** Recommended: 0.10 on
both sides as formula completion.

## P17 — LIMITATION 4: the ~22% WAS MOSTLY A FITTING ARTEFACT. 2026-09-11

Full record: `outputs/p17/reports/p17_findings.md`. 172 households, P9/P13 days.

**Spec v3's "subtract the fleet median" is REJECTED** — rejected correction, and
78.5% carry a fault, so the median is not fault-free.

**`beta_meas` was a straight line through a real heating-season step.** Free step
(CLAUDE.md already permits it): R² 0.7248 → 0.7545; step median **5.70 kWh/day**,
134/172 band above zero, **2.49 K** → balance ~14.5 °C, consistent with the fitted
changepoints. Step slope = 0.835 × line slope.

**Physics/measured 0.778 → 0.946. The ~22% becomes +6%**, inside the 38% physics
band. Distribution losses NOT added — not needed, not sourced. Rank unchanged
(ρ 0.534).

**Band on the slope excess** (month-block bootstrap × physics MC): line 77 confirmed
/ 75 inconclusive / 20 below; **step 40 / 91 / 41**. **Of P13's 125 SLOPE_EXCESS,
40 survive.** Median excess 719 → 107 kWh/yr.

**The step absorbs a curve OFFSET as well as the building's balance point** — the
step slope measures steepness only; the step has no physics prediction (P3), so it
ships as a measured column, never a finding.

**Open, Miguel's call:** re-rank the visit axis on the step slope with band status
(SLOPE_EXCESS 125 → 40)? Still open too: P13 fits all days, not post-visit.

## P18 — LIMITATION 5: station normal-year HDD. SOLVED IN METHOD. 2026-09-11

Full record: `outputs/p18/reports/p18_findings.md`. Weather only.

**Spec v3's PRISM fit is the wrong tool** — it reads the meter; Category B must not.
Each household gets its **station's normal-year HDD_12** (complete years, 2019–2024,
3–5 years — declared, not a climate normal; between-year CV 10.4%). Record length
leaves Category B entirely.

Fleet deficiency **321,330 → 351,229 (+9.3%)**; within-era worst quartile **44/45
shared**; fleet Spearman 0.973.

**P6's bins OVER-CORRECTED this cohort:** raw/normal at 365–548 days is **1.053**,
not 1.252; under 365 days records read WARM (0.842). P6 deflated short records by up
to a third. `897731` 7,435 → 7,957, no extrapolation.

**Open, Miguel's call:** adopt normal-year HDD for Category B (and the visit-axis
annualisation)?

## P19 — LIMITATIONS 6 + 7: THE CITATIONS DO NOT HOLD. 2026-09-11

Full record: `outputs/p19/reports/p19_findings.md`.

**OVERRIDES "The constants, supplied 2026-09-10" above: every as-built U-value and
every heating JAZ there cites a document that does not contain it.**

* **Switzerland is not a TABULA/EPISCOPE country** (episcope.eu, 23 countries, no CH).
  "TABULA/EPISCOPE CH 2013 Tab 4" could not be found. Values plausible, UNVERIFIED.
* **OST WPZ 2020 "Tabelle 1" is a list of the 23 systems**, not a JAZ table. The report
  gives fleet averages only: air WNG 3.0–3.3, ground 4.2–4.5. **No emitter split.**
* **FAWA 2004 has 99 pages** — "S. 331" does not exist. Ground-source mean JAZ **3.5**
  (1996–2003 systems). Usable relation: +5 K flow → −9% JAZ.

**`constants_ch.json` is the region file AND the registry** — `p_physics` loads it;
`STATUS` per constant: **4 VERIFIED, 7 SECOND_HAND, 9 CITATION_MISMATCH, 2 DERIVED,
1 PHYSICAL.** The nine are the terms that carry the deficiency. Test K prints them as
WARN on every run. Reproduction exact (0 mismatches on 172; 115/115; P10 23/23).

`b_ground` value now sourced (TABULA CCM eq. 4, 0.50); **its band is not.** The
`or True` test is fixed. `dhw_known` role added — **1** household unknown (not 27:
23 tick a separate heat-pump boiler, 3 solar only).

**Rank-and-level agreement with the meter (P9, P17) is NOT a source and can never
become one** — calibration rule.

**Open, Miguel's call:** where the U-by-era values come from.

## P20 — THE VERIFIED NOTEBOOK. Corrects P19 on JAZ. 2026-09-11

Full record: `outputs/p20/reports/p20_findings.md`; notebook answers with citations
in `outputs/p19/data/notebooklm/` (`p19_notebooklm_query.py`).

**How to query:** notebook `b02e42f0` via the `notebooklm` CLI
(`...\Python313\Scripts\notebooklm.exe ask -n b02e42f0 --json`). The MCP server is
configured in `~/.claude.json` but was not loaded in this session.

**Sources 6/7/8 are NotebookLM-generated "Research report" files, NOT literature.**
An answer citing only them is circular. **The as-built U-values exist in the notebook
ONLY in source 7** — still unverified.

**P19 was WRONG on ASHP JAZ.** The real source is OST WPZ, *Wie gut sind aktuelle
Wärmepumpen im Feld?*, P+I 11/12-2020, **Tabelle 1** (JAZ by application). Our
2.8/3.1/3.5 = its **heating + DHW** column → VERIFIED.

**THE "GSHP + RADIATORS = 4.4 REJECTED" DECISION IS OVERTURNED.** Tabelle 1: ground
Altbau 4.4 / 4.3, Sanierung 5.0 / 4.6, **Neubau 5.7 / 4.9** (heating / heating+DHW).
The spec's error was the FLOOR value (4.10–4.40, AI report only). Derived 3.40
under-credits ground-source non-floor houses.

**S2 (heating-only column + DHW-alone JAZ by type, 2.8 / 3.3) is the principled
mapping** — the model carries DHW separately. Fleet deficiency **−5.5%**, worst quartile
41/45 unchanged, **ρ per m² 0.534 → 0.579**, level 0.946 → 0.816 (trap 4 either way).
FAWA 1996–2003 vintage gives 1.112 — **the fleet is bracketed by vintage.**
`HeatPump_Installation_Year` 129/214 → vintage-aware JAZ possible, **flagged, not
started.**

**Not in the notebook:** thermal bridges, b-factor, EN 12831 n_min, prebound effect.
TABULA CCM, BFH 2013, BFE 2021 were read outside it — sourced, not notebook-verified.

**Open, Miguel's call:** adopt S2 (and retire the 4.4 test)?

## P21 — A REAL SWISS TYPOLOGY. The registry U-values are wrong, not just unsourced. 2026-09-11

Full record: `outputs/p21/reports/p21_findings.md`. 20 primary sources imported into
notebook `b02e42f0` after arguing 30 research candidates; every question restricted to
the 35 non-AI sources (`p21_notebook_research.py`).

**TEP Energy 2016, BFE Schlussbericht, §3.2.1 Abb. 30–33, EFH** — the Swiss
building-stock model. Envelope means: pre-1975 **0.943** (registry 1.35, band does not
overlap; Jakob 2002 gives 1.10), 1976–90 0.740, 1991–2009 0.393, post-2010 legal MuKEn
2008 0.319 / 2014 0.267. Chart readings pass the report's own text check (−58/−42% vs
~60/40%). **Declared: read off a chart; the area split still carries the dead TABULA-CH
citation.**

**`p21_u_sourced.py`:** fleet deficiency **−20%** (−24% with P20 JAZ); worst quartile
38/45. **Four checks improve at once:** pre-1975 design load / SIA table 1.27 → **0.96**
(P2's F1 gone), pre-1975 meter/physics 0.80 → 1.07, era range 0.52 → 0.39, ρ per m²
0.534 → **0.595**. The level moves AWAY from 1.0, so this is no fit. Middle eras
1991–2010 still under-predicted 28–33%.

**Also sourced in the notebook:** u_reference 0.269 ≈ MuKEn 2014 0.267 (re-cite);
b = 0.5 measured (FHNW 2017, basements ~8 K warmer), normative 0.7/0.8 → band 0.5–0.8;
ΔU_tb 0.10 / 0.05 (TABULA); **T_design −8 °C** (EnDK 2014, CEPE 2002 — −10 only in
the AI report); n_air 0.6 (TABULA; 0.7 not verified); **DHW 45 L/p/d → 2.61 kWh/p/d**
(SIA 385/2 via IEA Annex 46; FAWA measured 2.61); T_set 20 VERIFIED; JAZ table
reproduced by RISE 2023. **Not in the notebook:** EN 12831 n_min, prebound by age,
the area split.

**Nothing adopted — every value change is Miguel's decision.** Dashboard untouched.

## P22 — DECISIONS APPLIED. The live model. 2026-09-11

Full record: `outputs/p22/reports/p22_findings.md`. **OVERRIDES every earlier constant,
the P6 totals, the "~22% slope baseline" and P13 v1.** Export NOT regenerated — closing
session.

**Registry (`constants_ch.json`, written by `p22_registry.py`, deterministic):** as-built
U DERIVED from TEP 2016 EFH elements × the **Swiss INSPIRE 2015 Table 15 split** (46.9 /
27.3 / 18.2 / 7.5 %, read in the primary PDF), band widened to cover the German TABULA
split: pre-1975 **0.903**, 1976–90 0.709, 1991–2010 0.364, post-2010 0.269 (MuKEn band),
reference **0.247** (MuKEn 2014). JAZ heating-only table, ground 5.7/5.0/4.4 published
(no derivation); DHW JAZ air 2.8 / ground 3.3; b 0.5 [0.5–0.8]; ΔU_tb 0.10 on both sides;
DHW 2.61; T_design −8; n_air 0.6 (TABULA — **European standard method**).
**17 VERIFIED, 8 DERIVED, 1 PHYSICAL, 1 SECOND_HAND (storey_height); 0 mismatch.**

**Physics:** `station_normals()` feeds `hdd_normal_per_day` — **record length never enters
Category B** (asserted). `u_as_built` point = registry value when unrenovated (bands can be
asymmetric).

**Category B, 172 households: 268,271 kWh/yr (−16.5% vs v1 321,326), median 1,286.**
Envelope / emitter / DHW 61 / 8 / 31 %. Spearman vs v1 0.928; 35 of 41 HIGH_EXCESS keep.

**P13 v2 (live):** post-visit days, free step, band status, ranked on the lower bound.
**145 assessed: SLOPE_EXCESS 51 (49 were in v1's 125), INCONCLUSIVE 73, BELOW_PHYSICS 21.**
Physics/measured 0.808. v1 archived.

**127/127 tests, P10 23/23.** Closing session: `p11_export.py` needs the normals merge and
the new visit_status levels → schema v2.

## P23 — HEAT-PUMP VINTAGE IS IN. Archive done. 2026-09-11

Full record: `outputs/p23/reports/p23_findings.md`. **Overrides the P22 totals.**

`vintage_factor`: FAWA 1996–2003 fleet / OST 2015–19 table → a 1999 unit delivers
**0.794 (air) / 0.761 (ground)** of a 2017 unit; linear 1999→2017, flat outside, never
extrapolated; **no ageing loss** (FAWA), so it is technology vintage. As-built JAZ only;
new term **`term_vintage`** ("replace the unit"). Unknown year (63/172): no point claim,
band widened, tier +1.

**Category B 288,788 kWh/yr (+7.6%), median 1,498.** The meter confirms it: measured/
physics by install year **<2008 1.47 → 1.28**, 2008–14 1.22 → 1.15, ≥2015 1.05 → 1.03;
ρ per m² 0.593 → 0.618.

**P13 re-run: SLOPE_EXCESS 40, INCONCLUSIVE 82, BELOW_PHYSICS 23.** Old-unit consumption
moved to the building axis.

**BELOW_PHYSICS is not a fault and not PV (1/23):** 65% ground-source, 74% floor heating,
16/19 known units from 2008+, median 2 residents in 235 m². Candidate causes: unit beats
the table, house heated less than 20 °C everywhere (prebound), building beats its era
average. A check on the model, no action.

**Vintage is NOT curve settings in disguise (`p23_confound.py`, n=92):** curve@0 °C
median 33.5 / 35.0 / 33.0 °C by age group, curve-fault rate 57 / 48 / 57 %,
corr(age, curve) 0.016. The age gradient survives within equal curve settings. **Age
+2.1%/yr [+0.9, +3.4]**, unchanged when the curve enters, so the modelled vintage (~1.4%/yr)
is if anything low. **Interaction: an old unit with a high curve** loses most (1.86 vs
1.16) — for those houses, curve first, then replacement. Flag for the dashboard wording.

**137/137 tests, P10 23/23.** Closing: `p11_export.py` also needs `term_vintage`.

## P24 — LIFE-CYCLE RECOMMENDATION. 2026-09-11

Full record: `outputs/p24/reports/p24_findings.md`. **The +2.1%/yr is OUR measurement
(P23b), never a constant**; the model's vintage (~1.4%/yr) is sourced and sits inside it.

**Service life, ZHAW (Hubbuch & Vecsei), Weibull + Kaplan-Meier on a Swiss survey:**
ground **26.7 yr** (SD 4.7, N=223), air **20 yr** (SD 7, N=53, "less reliable");
borehole 50 yr (SIA 384/6). **Read in the primary PDF and confirmed in the notebook (q15).**
Same report: expert opinion 18±3 / 20±4, cost baseline 16 / 23 — **replace count 12 →
25–27 under those; the basis must be shown.** No source says early replacement pays.

**NOTEBOOK HYGIENE:** the web-research runs imported all 30 candidates, duplicated (105
sources vs 42). **Every question goes through the vetted whitelist in
`p21_notebook_research.allowed_sources()`** — never "all non-AI sources". P21/P22
answers predate the flood. **CLEANED 2026-09-12 (`p24_notebook_cleanup.py --apply`,
Miguel authorised): 63 deleted, 42 remain**, all vetted; the three "Research report"
files are kept but never asked. `auth check` says "valid" on stale cookies — **trust a
real call, not the check**; `login --browser chrome` works when the session expires.

`p24_lifecycle.py` → `unit_recommendation`, **age counted to `REF_YEAR = 2024`, the data
end — CHANGE IT IF THE DATA IS UPDATED** (the run prints the last meter date and flags a
mismatch): **REPLACE_END_OF_LIFE 12**, **PLAN_REPLACEMENT 30**, **KEEP_IN_LIFE 87**,
**RECORD_INSTALL_YEAR 85**. **Curve first, then replace: 13.** Usage does not enter:
vintage = generation (efficiency), life = failure risk.

**Act first (`p24_actfirst.py`):** vintage everywhere changes 5 of 45; two post-2010 houses
enter only because of a mid-life unit's vintage (wrong reason). **Option A — vintage in the
headline, not in the ranking for KEEP_IN_LIFE units — changes 3 of 45, all with units
due.** Recommended; closing-session item for `p11_export.py`. **141/141 tests.**

## P25 — THE THREE-GROUP OVERVIEW. The run behind the v2 design. 2026-09-12

Full record: `outputs/p25/reports/p25_findings.md`. 172 households.

**`house + heat_pump == total` to 2.73e-12 kWh/yr** — the decomposition is an
identity and ships as one. Fleet **points**: house 274,851 · heat pump 13,938 ·
total 288,788 kWh/yr. **The v2 export's group totals are sums of LOWER BOUNDS
(196,311 / 9,291 / 214,004) — different quantities, never quote one as the other.**

**The house group carries 95% of the energy.** The heat-pump group is small, and
that is the finding: the fabric is where the kWh are, the unit is where one
decision is.

**GROUP 2 NEEDS NO ERA RANKING, AND THIS IS MEASURED.** Median heat-pump kWh by
era is `0, 0, 0, 0, 14` — no structure across building age. A unit's vintage is
equipment; its efficiency gap does not depend on when the house was built. So the
three-group split is not cosmetic — group 2 is a genuinely different axis with a
different owner. Age and cost do rise together across the known-year classes
(7/15/28 yr → 0/215/433 kWh/yr), which is what a vintage term should do and is
**not** evidence it is right: it is built from published JAZ generations, not
fitted.

**THE ERA QUESTION, measured, and it is what made the override informed.** Worst
quartile on the lower bound: fleet-wide 43, within-era 45, **shared only 34** —
the two lists disagree on about a fifth. Fleet-wide sends **16 pre1975 and 0
post2010**; within-era forces **5 post2010** in by construction. Decision
(Miguel): **fleet-wide, era as a filter, `phys_rank_in_era` kept.**

**post2010's median lower bound is NEGATIVE (−86)** — the only era whose band
crosses zero at the median. **The P9/P21 era gradient reappearing in the
deliverable**, not a new result, and the reason the ranking ships with a declared
bias note. Renovation also tracks era almost perfectly (0.81 → 0.55 → 0.20 → 0.00
→ 0.00), so **"old" and "renovated" are not separable here** and an era cell is
not a clean instrument for fabric condition.

**The no-claim asymmetry first showed up here:** heat-pump median point 0 against
median lower bound 12, with 133 of 172 bands wholly above zero. Same pattern that
later broke the export's `lo <= point <= hi` rule.

**THE STALE STATUS COLUMN IS FIXED — re-run 2026-09-17 on Miguel's instruction.**
The first run wrote `visit_status = BELOW_PHYSICS`, retired later that day. It was
logged rather than re-run at the time; Miguel chose clean over carried, so P25 was
re-run against the v2 visit axis. **`grep BELOW_PHYSICS` over `outputs/p25/` now
returns nothing**, and **every other number reproduced exactly** (seeded RNG
`20260919`): the 2.73e-12 identity, 274,851 / 13,938 / 288,788, decisive
155 / 133 / 158, and the era quartiles. Refreshed axis on these 172:
`INCONCLUSIVE` 82 · `SLOPE_EXCESS` 40 · `USES_LESS_THAN_MODELLED` 23 · 27 `NaN`
(this cohort's share of the export's 69 `NOT_ASSESSABLE` — a state, not a gap).
**No conclusion changed; only the label did.**

## P26 — THE v2 EXPORT: DECISIONS SETTLED WITH MIGUEL. 2026-09-12

Interviewed and confirmed before any code (`/interview-me`). **Audience: fellowship
review now, and a demo for an operator who would dispatch technicians to THEIR OWN
fleet** — so it must be both defensible and operationally legible.

**Shape: ONE section, TWO pages.** Page 1 explains the rank and names the owner
(builder / installer / both). Page 2 is **one fleet-wide list** with three columns:
**house** (envelope + emitter + DHW), **heat pump** (vintage + recommendation),
**total**.

| # | settled |
|---|---|
| 1 | act-first = **A**: vintage in the total, NOT in the ranking value for `KEEP_IN_LIFE` |
| 2 | service life = **measured failures** (air 20 / ground 26.7), basis named on the page → replace 12 |
| 3 | `BELOW_PHYSICS` → **`USES_LESS_THAN_MODELLED`**; the "no status says below" rule STAYS |
| 4 | both no-claim states **visible and filterable**, neutral, never green |
| 5 | `REPLACE_END_OF_LIFE` / `PLAN_REPLACEMENT` / `KEEP_IN_LIFE` / `RECORD_INSTALL_YEAR`; **"curve first, then replace" belongs to the END section**, not here |
| 6 | `term_vintage` stays **inside** the headline total; never-sum set unchanged (two visit kWh columns, capacity scenario) |
| 7 | the 27 lost to the post-visit rule: not assessable on the visit axis, **building score kept** |
| 8 | 85 unknown install years: **fixable audit gap**, no vintage claim |
| 9 | appliance level column **out**; **appliances never enter the model** |
| 10 | ages **as of the data end (2024)**, stated on the page |
| 11 | **schema v2**, v1 alongside for one cycle |
| 12 | notebook: **P0, P1, P10, P13 v2 + P17–P25 evidence**; P5/P7/P8/P9 stay in `history/` |
| 13 | **PRIMARY ORDER IS A SINGLE FLEET-WIDE LIST** on the total lower bound, era filterable, within-era rank kept as a column. **THIS OVERRIDES "rank within era, never fleet-wide"** — Miguel's call, 2026-09-12 |
| 14 | visit-axis columns stay in v2 but are **HIDDEN from our two pages**; the end section consumes them |

**OUR SECTION IS BUILDING-SIDE ONLY. No heating slope, no fault %, on either page.**
Aaditya's model is not loaded anywhere in this workstream (removed from P13
2026-09-12); the two models meet **only** in the end section, each in its own column.

### BUILT 2026-09-12 — `physical_baseline_v2`, 214 rows x 66 columns, all rules pass

**66 not 65 since 2026-09-17:** `phys_no_result_fix` was added (additive, so no version
bump) when P27 found the reason columns were labelling a mixed set with one string.

`p22_registry -> p24_lifecycle -> p13 -> p11 -> p_notebook`; **141/141 and P10 23/23.**
`SCHEMA_v2.md` written, `HANDOFF_dashboard_integration.md` rewritten, v1 left on disk
for one cycle, S-series notified (`../STRATUM-LEVEL RESIDUAL MODEL/NOTE_from_physical_baseline_v2.md`).

**`phys_status`: HIGH_EXCESS 40 · EXCESS_CONFIRMED 118 · INCONCLUSIVE 14 ·
INCOMPLETE_AUDIT 42.** Confirmed excess **158 households, 215,121 kWh/yr on the lower
bound** (HIGH_EXCESS 118,462 across 40). Groups on the lower bound: **house 196,311 ·
heat pump 9,291 · total 214,004**. Units: keep 76 · record year 63 · plan 23 · replace 10.
Visit axis, hidden from the pages: SLOPE_EXCESS 40 · INCONCLUSIVE 82 ·
USES_LESS_THAN_MODELLED 23 · NOT_ASSESSABLE 69.

**A VALIDATION RULE WAS WRONG, NOT THE MODEL.** "lo <= point <= hi" failed on 172 rows.
Measured before touching it: `lo > hi` never happens; the total's point sits 2 kWh below
its band on **one** row (independent rounding of three columns); and **63 heat-pump rows
have point 0 below a positive band — exactly the unknown-installation-year households**,
where the point makes no claim and every draw samples an older unit. Replaced by three
rules (`lo <= hi` always; total within the same ±2 kWh rounding tolerance; known-year
rows bracketed, unknown-year rows asserted as a zero point under a non-negative band)
plus **`phys_heat_pump_point_is_no_claim`** so a page shows the band, not the zero.
**My first guess — sourced values sitting at band edges — was wrong; the diagnostic
caught it.**

**Act-first becomes 43 (fleet-wide) against 45 within era.** Declared with it: P9/P21
measured that per m² the physics under-predicts newer eras by 24–53%, so a fleet-wide
list tilts toward older houses; the era filter and the retained within-era rank are the
mitigation, and the bias is stated on the page.

## P27 — THE WORKED EXAMPLE. One house traced, and a defect it found. 2026-09-17

Full record: `outputs/p27/reports/p27_walkthrough.md` (+ `.html`, print-ready).
Generated by `p27_walkthrough.py`. **NO NUMBER IS TYPED BY HAND** — the document is
emitted from the registry, the adapter and the shipped export, and the run **asserts**
that the trace reproduces `evaluate()` **and** the export (7,987.5 vs 7,988.0, inside
the 2 kWh rounding tolerance). If the model moves and the document does not, the run
**fails** instead of printing a stale story.

**Scope, set by Miguel 2026-09-17: it says HOW the model works, NOT whether it works.**
No performance claim, no AUC, no "not shown to work / not shown to fail" — that belongs
in the report's results section. What **is** kept are the scope limits that change how a
number should be read (the order leans old, bands are wide by design, levels are not
bills, nothing is calibrated), because dropping those would oversell by omission.

**FOUR PROVENANCE TAGS, not three** — "from a reference" is two different things.
43 trace rows: **GENERATED 17, DATABASE 13, VERIFIED 7, DERIVED 4, SECOND_HAND 1,
PHYSICAL 1.** Every DATABASE row names its HEAPO column; every constant row carries its
registry source, section and status.

**Deep trace `116121`** (rank 1, pre1975, T1, air-source + radiators, electric
cylinder): envelope 600.84 m2 = 1.52x floor area; u_as_built 0.9028 vs u_reference
0.2466; H 767.71 vs 373.44 W/K; JAZ 2.900 x vintage 0.908 = 2.634 against a reference
3.700; E_as_built 12,251 vs E_reference 4,264; **deficiency 7,988 kWh/yr
[7,142–9,935]**. Terms envelope 5,313 / dhw 1,225 / emitter 989 / vintage 461 —
**three of four are the builder's**, so replacing the unit leaves 89% of the gap.

**Contrast cases, selected deterministically from the export:** `876511` (rank 2,
no-claim — pump point 0 under a band opening at 13), `121728` (post2010,
`INCONCLUSIVE` — band crosses zero, no rank), `100120` (never computed).

### THE DEFECT THIS RUN FOUND — the 42 are NOT one thing

**Measured: 21 building data missing ONLY, 18 meter record too short ONLY, 3 both.**
The export puts **one blanket string on a mixed set**: `phys_status_reason` says
"required building data missing" (**true for 24 of 42**), `phys_no_result_reason` says
"insufficient usable meter days" (**true for 21 of 42**). Neither holds for all 42.
Worse, **`phys_no_result_is_fixable` is `True` on all of them, merging "go and look"
with "wait"** — 21 need an auditor to record missing geometry, 18 need only a longer
record and no visit helps them.

**I asserted the wrong cause twice before measuring it.** First I documented all 42 as
"building data missing" (from `phys_status_reason`); then, on seeing
`phys_no_result_reason`, I "corrected" it to all-meter-days. **Both were blanket claims
read off a single column.** Only `modellable()` + the meter filter settle it, per
household.

### FIXED the same day, on Miguel's instruction. The root cause was a merge.

`phys_no_result_reason` read `m.drop_reason`, and `m` is H's id column left-merged onto
**S, the SCORED frame** — so `drop_reason` is NaN for **exactly** the unscored households,
and every one of them fell through `.fillna("insufficient usable meter days")`. The
per-household cause was always intended; it was being read from the one frame guaranteed
not to have it. Now read from `H`.

**Now: 8 distinct causes over the 42** (the commonest is `no_footprint;no_storeys`, 21
households — per-storey floor areas never recorded), plus a new column
**`phys_no_result_fix`**: *"record the missing building data - an auditor can do this"*
**24** against *"none - needs a longer meter record; a visit does not help"* **18**.
`phys_status_reason` no longer asserts a cause it cannot know.

**`phys_no_result_is_fixable` KEPT ITS MEANING and it is NOT "send someone"** — it means
only *will this ever become answerable*. **Who acts lives in `phys_no_result_fix`.** Said
in SCHEMA_v2 in those words, because overloading the boolean is what made the original
wrong in practice.

**TWO REGRESSION GUARDS, because the blanket string passed every existing rule:**
reasons must be **per household** (>= 2 distinct over the 42) and the two audit causes
must differ. The old rules only asked whether the column was *populated* — and
**"populated" is not "true of this household"**. That gap is the whole lesson.

Re-ran `p11 -> p_notebook -> p27`, **141/141 and 23/23**, every energy figure identical:
only the two strings changed and one column was added.

### FIGURES AND TAG COLOUR, 2026-09-17 — the six-colour idea FAILED validation

Miguel asked whether the grey provenance tags would read better in colour. **Measured,
not judged:** an inline badge can sit beside any other badge, so it needs the
**all-pairs** gate — and **six distinct tag colours FAIL it**: worst pair normal-vision
ΔE **12.9**, under the 15 floor, meaning hard to tell apart *with full colour vision*,
before colour-blindness is even considered. **Three families PASS all-pairs** (worst CVD
ΔE 9.2, normal-vision 24.0).

So **colour carries the FAMILY** (from the database / from a reference / ours) and **text
carries the precise tag** — which is also exactly the three-way split Miguel asked for in
the first place. The hue sits on a border plus a pale tint while the text stays ink, so
legibility never depends on hue, **the document still reads in greyscale print**, and
nothing is encoded by colour alone.

**Three figures, form chosen before colour:** F1 the two baselines (stacked bar,
categorical 2), F2 the four terms with the builder/installer divider (stacked bar,
categorical 4), F3 the bands (interval plot, **emphasis** — one hue + grey).
**F3 is PERCENT OF REFERENCE, not kWh** (+187% / +70% / +4.1%): 8,000 against 176 kWh on
one axis hides the small one, and this figure's job is the **sign**. It is what makes
"the band crosses zero, so we claim nothing" visible at a glance. 150 dpi PNG,
base64-embedded in the HTML so the file stays self-contained for PDF, referenced as files
from the `.md`. No hover layer: a printed raster cannot have one, and every figure
duplicates a table already in the document.

**A HERO FIGURE LEADS THE DOCUMENT, AND IT LEADS ON THE LOWER BOUND** — `7,142 kWh/yr`
at 48px, labelled *"at least this much more electricity than a code-compliant version of
the same house"*, with the point, band, `+168%` and tier on a sub-line. One headline
number is a hero figure, never a one-bar chart. Leading on the **lower** bound rather
than the point means the first thing a reader meets also teaches the model's own display
rule, instead of stating the biggest number available.

**LOOKING AT THE RENDERED OUTPUT CAUGHT THREE DEFECTS THE VALIDATOR CANNOT SEE** — the
gap annotation sitting on F1's legend, `461` printed twice in F2, and F3 ordered bottom-up
against the reading order. **The validator checks colour, not layout.**

### THE DOCUMENT ROTTED WITHIN THE HOUR, AND THAT IS THE LESSON

P27's own defect note said *"export not yet changed — take the split from this table
until the export emits a per-household cause"*. **One hour later the export was fixed and
that sentence was false**, in the very document whose stated rule is that no number is
typed by hand.

**"Generated" protects NUMBERS, not CLAIMS.** The figures were all derived and stayed
correct; the *prose around them* was hard-coded, and prose asserting the state of another
file is just as hand-typed as a number. The note is now **derived from the export** — it
counts the distinct causes and reads `phys_no_result_fix`, then describes whichever state
it finds, with a branch for "not yet fixed".

**Rule for anything generated here: if a sentence asserts the state of another artefact,
derive it or do not write it.** Found by reading the rendered output instead of trusting
the generator — which also caught "a air-source unit" and a raw
`4.052917477628678` in a printed table.

## P28 — THE DASHBOARD PAGE. Built as a SEPARATE v2 page. 2026-09-17

**The integration was not un-started — it existed and was bound to v1.**
`pages/3_Physical_baseline.py` read `physical_baseline_v1.parquet` and displayed
`visit_fault_probability` / `visit_named_fault` by **direct indexing**, so on v2 it
would raise `KeyError` rather than degrade. It also ranked **within era**, which v2
overrode. I had reported integration as "still to do" because I had only scanned the
two model workstreams, never the dashboard.

**DIVISION, not conversion (Miguel, 2026-09-17).** I first recommended converting page 3
in place and Miguel confirmed; he then chose a clean split instead, and that is what
shipped:

| file | state |
|---|---|
| `pages/5_Physical_baseline_v2.py` | **NEW.** Three views: what the rank means · the one list · the worked example |
| `pages/3_Physical_baseline.py` | **LEGACY**, untouched but for a warning banner and a retitle |

The split de-risks the demo — the old page keeps working — and lets the new one be built
to the v2 contract instead of inheriting a per-era structure.

**What the page implements:** ONE fleet-wide list on the lower bound (never per-era
tables); the three groups with their owners, **computed from the frame, not hardcoded**;
all 214 rows in two tables (158 ranked, 56 not ranked) so unjudged is never judged
normal and never totalled as zero; `phys_no_result_fix` surfaced so a reader sees which
of the 42 an auditor can fix; the `†` marker on the **61** ranked no-claim rows with the
"show the band, never the zero" note; no fault column; no green — `theme.POS` is red
(`#e66767`) despite its name.

**Group totals must be computed, never quoted.** Over confirmed-excess rows they are
house 197,851 / pump 9,051 / total 215,121; over all scored rows 196,311 / 9,291 /
214,004. **Different subsets, different quantities.** The page sums the frame and says
which subset.

**The walkthrough renders the `.md`, not the `.html`.** The `.md` references figures as
`../figures/*.png`, which Streamlit cannot resolve, so the page **inlines them as data
URIs** — that keeps the document in the dashboard's own theme instead of an iframe
white sheet. My first attempt used an iframe and contradicted this file's own handoff
instruction ("render the `.md`; the `.html` is for the printed report"); the existing
`f6_walkthrough.py` pattern is what caught it. Spanish has no `.md`, so it alone renders
its self-contained HTML in a frame, labelled as the print version.

**VERIFIED AGAINST THE EXPORT, NOT RENDERED.** 158 + 56 = 214 none dropped; 0 ranked
rows missing a unit recommendation; 0 unranked rows missing a reason or a fix; 3/3
figures inline with 0 unresolved refs; both pages byte-compile. **Streamlit is installed
in no environment here** — `venv_viz`, `.venv`, the `py` launcher and PATH all lack it,
so nothing was opened in a browser. `requirements.txt` pins `streamlit>=1.40`, which
covers `st.pills`. **Render it once before demonstrating it.**

### `p28_page_test.py` — the pages are EXECUTED, without Streamlit

Streamlit being absent is not a reason to ship unexecuted code, so the test **stubs the
Streamlit API** and runs each page once per view against the real export. Transcript:
`outputs/p28/logs/p28_page_test.txt`. It asserts:

* every view of the v2 page runs (13/10/5 markdown blocks, 2 tables each on views 1–2,
  3 metrics, the notebook call, both walkthrough languages including the ES iframe);
* **no fault string is ever emitted by the v2 page** — checked on every `markdown` call;
* **no green among the tokens the page paints with**, checked NUMERICALLY (`POS`
  `#e66767`, `SERIES1` `#3987e5`, `SERIES2` `#d95926`, `AXIS_INK` `#8a8a85`);
* the legacy page still runs and fires exactly one warning banner.

**The first version of this test failed for the wrong reason** — it banned the literal
word "green", and the page legitimately *says* "nothing here is green" in the prose
explaining the rule. A test that bans a word cannot check a colour; it now parses the
hex and compares channels. **Kept in the repo, not a scratchpad** — evidence outside the
tree cannot be re-run or diffed.

**The bundled snapshot is refreshed to v2** (`Heat_Pump_Failure_Prediction/physical_baseline/`):
v2 export, `SCHEMA_v2.md`, the rebuilt notebook, the walkthrough `.md`/`.html`/ES and its
three figures, **with v1 kept** because the legacy page still reads it. Both resolution
roots — the live model tree and the bundled fallback — were verified to satisfy every
path the new page opens, so a fresh clone runs it.

**DO NOT retire v1 yet.** Deleting the v1 export or the legacy page would undo the very
division Miguel asked for: the old page is what keeps working while v2 is demonstrated.
Retire it *after* the demo.

## Layout and conventions

**`history/` (2026-09-11) holds every superseded stage** — scripts P2–P9, P12, P14–P18,
the P20/P21 scenario scripts, their outputs, and P13 v1 (`history/outputs/p13_v1`). See
`history/README.md`. **Any `outputs/pN` path above for those stages now lives under
`history/outputs/pN`.** Nothing there is live or reproduces unchanged. Live at root: the
physics, three adapters, `p_pipeline_test`, P0, P1, P10, P11, P13, P22 registry, P23,
the notebook drivers (P19/P21/P22) and their evidence in `outputs/p19`–`p22`.
`p_notebook.py` still loads P5/P7/P8/P9 and will show them as missing until the closing
rebuild.

Scripts at this directory's root, `pN_*.py`. Outputs to `outputs/<stage>/<kind>/`.

* **`<stage>`** — `p0` `p1` `p2` … A new rung slots in without renaming anything.
* **`<kind>`** — `data` / `figures` / `logs` / `reports`. The executed notebook
  sits at `outputs/<stage>/PN_*.ipynb`, beside the kind directories.
* **Every stage carries all four kinds plus a notebook.** A run that exists only
  to inform a decision is still a run — S4 next door shipped without one, and that
  was the run that overturned a recommendation.
* Notebooks are **built and executed by `pN_notebook.py`** via `nbformat` +
  `nbclient`. Use `%matplotlib inline`, **never** `matplotlib.use("Agg")` — Agg
  writes PNGs and embeds nothing.
* **Always run `../venv_viz/Scripts/python.exe`.** `../.venv` is empty of packages.
  Available: pandas 3.0.5, numpy 2.5.2, matplotlib 3.11.1, scipy 1.18.1, seaborn.
* **numpy + pandas only for computation**, by choice, as next door. scipy is
  installed and unused.
* **Tests live in the repo, never in a session scratchpad.** `p_pipeline_test.py`
  at this root, transcript under the owning stage's `logs/`. Evidence outside the
  tree cannot be re-run, diffed or trusted later.

### Inputs

| what | where |
|---|---|
| audit data | `../heapo_data/reports/protocols.csv` |
| daily kWh | `../outputs/daily_states.parquet` (953,007 rows, 1,407 households) |
| daily weather / HDD | `../outputs/household_weather.parquet` (joins 1:1 on `(Household_ID, date)`, 0 mismatches) |
| raw weather | `../outputs/weather_daily.parquet` |

**Usable day** = `state_total in {NORMAL, MIXED_ZERO}` AND `kwh_total` not null
AND HDD not null. Inherited from next door and re-derived here, not imported.

## Traps specific to here

1. **`protocols.csv` reads with `sep=None, engine="python"`** — it is
   semicolon-delimited. `Household_ID` is float64 with 193 NaN rows; cast to
   `Int64` before any join (parent trap 5).
2. **A "tick the one that applies" column is not a boolean.** True/NaN with no
   False level. `Building_ElectricVehicle_Available`: 33 True, 0 False — unusable.
   `DHW_Production_*` is recoverable because 1,341 of 1,358 mark exactly one.
   **Check the False count before treating any flag as boolean.**
3. **Visit dates come from `protocols.csv` directly**, never reconstructed from
   `first_date + DaysBeforeVisit` — that matches for only 31 of 89 households
   (parent trap 7).
4. **A physics constant that reproduces the data is a red flag, not a success.**
   If your U-values make `E_expected` track the meter closely on the first try,
   check whether someone chose them by looking. The calibration rule is violated
   by convenience far more often than by intent.
5. **`exclusion_register.csv` may finally be the RIGHT tool here.** Next door it is
   barred, because its `pre_usable` / `post_usable` columns exist only for the 214
   inspected and gating on it collapses the fleet to 78. **This workstream IS the
   214.** Evaluate it as a pre/post window gate at P0 — but measure what it costs
   before adopting it, and do not import next door's rejection unexamined.
6. **The band is not a confidence interval on a fitted parameter.** It is
   propagated uncertainty on a computed quantity. Do not describe it as a
   regression CI, and do not let a reader read it as one.
7. **Category letters collide with the S-series.** Prefix every column and figure
   label so a pasted table cannot be misread: `phys_status`, not `status`. And
   **no single letters on the physical axis** — letters belong to
   `combined_category`'s 2x2 alone. See P11.

## Open — decide with a measurement, not a preference

* **PV households.** 183/214 have the flag. Self-consumption is unobservable, so
  their grid import understates true consumption and `E_expected` will over-predict
  them systematically. Exclude, or report as a separate group with the bias
  declared? **Measure the size of the bias at P0 first.**
* **Sub-metered households.** Where `kwh_hp` exists, the physical model can be
  compared against the heat pump channel directly rather than total household draw
  — a much cleaner test of the physics, on a smaller n. Worth a rung.
*(The HDD definition was on this list and is now settled — see below.)*

## Settled by measurement — HDD_12, P0, 2026-09-10

**`HDD_12` = `max(0, 12 − T)`. Fixed permanently. The spec's SIA 20/12 is
rejected.** Full evidence in `outputs/p0/reports/p0_findings.md`.

**The identity:** `HDD_SIA = HDD_12 + 8 · 1{T < 12}`, exact on **878,128 /
878,128** usable household-days (100.0000%). SIA is **not a rescaled `HDD_12`** —
it bundles a step function in with the slope, welded at exactly 8× the slope.
Coefficients between the two are **not convertible**.

**Fit**, paired, same households and same days:

| population | n | median R² `HDD_12` | median R² SIA | mean ΔR² (SIA − 12) |
|---|---:|---:|---:|---|
| protocol cohort, all days | 193 | **0.7299** | 0.7226 | −0.0064 [−0.0132, +0.0003] |
| fleet-wide, all days | 1,313 | 0.6773 | 0.6782 | −0.0002 [−0.0026, +0.0024] |
| protocol cohort, post-visit | 154 | 0.7315 | 0.7315 | −0.0025 [−0.0102, +0.0052] |

Dead heat fleet-wide, `HDD_12` ahead on this cohort, and SIA worse on RMSE by
0.10 kWh/day. **No population gives SIA a case.**

**THE DECIDING REASON, and it is specific to this workstream: there is no free
intercept here.** The S-series *fits* a per-household intercept, which silently
absorbs SIA's fixed 8-degree-day offset — that is why the parent could discard the
reference temperature at no cost. **This model computes `mu_floor` and `beta_H`
and fits nothing.** Under SIA it would **predict a discontinuous jump of
8 · beta_H in daily kWh** the moment mean temperature crosses 12 °C, with nothing
free to absorb it. No building does that.

> **A degree-day definition whose offset needs a fitted intercept to hide it
> cannot be used in a model that has no fitted intercept.**

**The step itself is real and is NOT rejected.** Decomposed on the cohort: step
indicator alone R² 0.5048; `HDD_SIA` alone 0.7226; **`HDD_12` + a FREE step
0.7587**. Welding the step to 8× the slope costs **−0.0263 R²**. So if a later
rung needs a heating-season term, it takes it as a **free parameter**, never
smuggled in through the degree-day definition.

**This confirms an existing instruction rather than making a new choice** — `BASE`
= 12 °C is declared and permanent (Prof. Mehta, 2026-08-27). A move to 8 or 10 °C
is Abdul's call. **Trap 13 stands: never fit the base per household.**

**Logged for the parent, not for here:** our recomputed `HDD_SIA` uses a **strict**
`T < 12` boundary where the archive rule documented in `../CLAUDE.md` is
**inclusive** at exactly 12.0 °C. 96 household-days, 0.011%, immaterial to every
result. Flagged, not fixed; it belongs in the parent's tree.

## Next step — NOT Aaditya's fault flags. REVERSED 2026-09-12 by Miguel.

**Superseded. Aaditya's fault prediction is OUT of this workstream**, and the
earlier wording below is kept only for the audit trail.

His model keeps **its own section** of the project and the dashboard. **The two
models do not combine until a final end-section target overview**, each keeping
its own column. There is **no fault column in `physical_baseline_v2`** (asserted
on write: no column name contains "fault"), the visit axis no longer carries a
fault probability, and `p13_visit_queue.py` v2 is fault-free.

**So there is no integration slot to fill here and nothing to hold in
consideration.** A fault percentage may appear beside this model's columns in the
end section; it may not enter this model's scoring, its ranking, or its two pages.

> *Superseded wording, for the audit trail:* "Named and expected, pending only the
> model's arrival. A says a household is materially above what physics predicts and
> nothing in the audit explains it; Aaditya's model says which fault it is. The two
> compose; neither substitutes for the other. Nothing in this workstream moves in
> anticipation of it."

## Decision log

The parent's `../outputs/decision_log.md` is append-only and shared. **Decisions
made here go there**, dated, with the reason and what the decision rules out.
Read it before proposing a design choice it already settles.
