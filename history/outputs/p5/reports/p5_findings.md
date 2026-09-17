# P5 — the uncertainty band, measured at last

Run 2026-09-10. `p5_bands.py` on `p_physics.py` + `p_adapter_heapo.py`.
Transcript `outputs/p5/logs/p5_run.txt`. **183 households × 400 Monte Carlo draws
over the published spread of every constant.**

**Headline: the band is usable — 90.2% of households are decisive — but P5 also
disproved a claim this project has been repeating since the design was settled.**

---

## 1. THE CORRECTION — variance does not cancel in the difference

**Claimed, repeatedly, in the CLAUDE.md and in P2/P3/P4:** *"a difference between
two baselines sharing the same constants is far better conditioned than either
level."*

**Measured median relative 95% width:**

| quantity | relative width |
|---|---:|
| `E_as_built` (a level) | 0.28 |
| `E_reference` (a level) | 0.18 |
| **`deficiency` (the difference)** | **0.94** |

**The difference is 3.4× WORSE in relative terms.** Catastrophic cancellation:
subtracting two large similar numbers leaves a small one whose absolute error
barely shrank while its denominator collapsed.

### The design survives, for a different reason

Two distinct error sources were conflated:

* **Systematic bias** — `E_as_built` omits all appliance electricity, because no
  SIA heating standard supplies it. It is **identical in both baselines and
  subtracts out exactly.** This is the real justification for two baselines, and
  P4 §3 measured the damage it does to the level (implied appliance load 897 to
  14,878 kWh/yr).
* **Propagated constant uncertainty** — amplified in relative terms, modestly
  reduced in absolute terms (median band 1,113 kWh).

**So the difference is the right quantity because it removes a bias, not because
it reduces variance. Every deficiency figure must travel with its band.**

## 2. Is the band narrower than the deficiency?

| | median | IQR |
|---|---:|---|
| deficiency | 1,686 kWh/yr | 961 – 2,720 |
| 95% band width | 1,113 kWh/yr | 634 – 2,262 |
| band ÷ \|deficiency\| | 0.94 | 0.54 – 1.26 |

**Decisive — entire 95% band above zero: 165 of 183 (90.2%).**
Band straddles zero → **unjudgeable: 18 (9.8%)**.

**90.2% is not a selective gate.** It answers "can we say anything at all", not
"is this house worth acting on". Confirms the earlier conclusion: **the B/D line
cannot be a statistical threshold.**

## 3. The tiers work

| tier | n | median band | band/\|def\| |
|---|---:|---:|---:|
| T1 published JAZ, no renovation ambiguity, full geometry | 100 (55%) | **698** | 0.58 |
| T2 one widening source | 68 (37%) | 1,723 | 1.01 |
| T3 two or more | 15 (8%) | **3,688** | 1.29 |

And **consistently within era**, which is the real test — e.g. 1976–1990: T1 848,
T2 1,510, T3 2,125 kWh. Better-documented houses get tighter answers. **The tier
system does what it was built for.**

Note T1's *decisive* rate (83.0%) is the **lowest**, which looks wrong and is not:
post-2010 houses are unrenovated, hence T1, and correctly have a deficiency near
zero. 17 of the 18 non-decisive households are post-2010.

## 4. By era

| era | n | median deficiency | median band | decisive |
|---|---:|---:|---:|---:|
| pre-1975 | 41 | 3,690 | **3,899** | 97.6% |
| 1976–1990 | 65 | 1,630 | 1,388 | 100% |
| 1991–2000 | 24 | 1,292 | 736 | 100% |
| 2001–2010 | 35 | 1,242 | 623 | 100% |
| post-2010 | 18 | **−100** | 442 | **5.6%** |

**Pre-1975 carries a band as large as its own deficiency** (3,899 vs 3,690),
because renovation widening bites hardest there. Its numbers are the largest in
the output *and* the least certain — both facts must travel together.

**Post-2010 correctly decides nothing**: those houses are at or better than the
SIA 380/1 reference, so 1 of 18 is decisive. That is the model working.

## 5. A relative gate remains unusable

| gate | selects |
|---|---:|
| > +15% of `E_reference` | **85.2%** |
| > +25% | 79.8% |
| > +50% | 65.6% |
| > +100% | 26.8% |

Reproduces the earlier check exactly. **A category holding most of the fleet ranks
nothing** — the S-series' central lesson.

## 6. Recommendation: rank by the LOWER BOUND

The ranked output now reads e.g. `779742 (13,801 ±8,224)` next to
`1137376 (4,012 ±679)`. The first has a bigger expected value and a band three
times as wide.

**Rank on `deficiency_lo` — the 2.5th percentile — not the point estimate.** It is
the honest "at least this much" figure and it automatically penalises
poorly-documented houses instead of rewarding them for being vague.

Measured impact: **9 of the top 10 are the same households**, but the order
changes (116121 takes first place from 779742). So the choice is low-risk and the
conservative version costs almost nothing.

## 7. Population, every exclusion declared

| | n |
|---|---:|
| households in `protocols.csv` | 214 |
| modellable | 189 |
| **unjudgeable — missing a required role** | **25** |
| of those: no footprint / no storeys | 19 |
| with usable consumption days | **183** |

Reasons are written to `p5_unjudgeable.csv` and reach the output.
**The dominant loss is missing per-storey geometry, not consumption data.**

## 8. Architecture

`p_physics.py` holds the formula, the constants with their bands and sources, and
the Monte Carlo sampler. It contains **no HEAPO column name**.
`p_adapter_heapo.py` is binding #1. A second dataset supplies
`p_adapter_<name>.py` and nothing in the physics changes.

**The portability requirement is now met in code, not only in intent.**
