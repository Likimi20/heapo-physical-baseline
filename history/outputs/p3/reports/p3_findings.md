# P3 — real geometry instead of an era lookup

Run 2026-09-10. Script `p3_geometry.py`, transcript `outputs/p3/logs/p3_run.txt`.
**191 households** with a usable footprint + era.

Miguel, 2026-09-10: *"the level means how much space they need to heat and also
that is not the same, a house with ground first second and top floor level than
one with only ground."*

**Correct, and it diagnosed P2's F2.** Verdict below is mixed: the premise is
confirmed, one of the two tests it should have fixed did not move, and the run
exposed a defect in my own geometry.

---

## 1. CONFIRMED — the era lookup destroys real per-household information

Geometric Gebäudehüllzahl, from audited per-storey areas:

* median **1.83**, IQR 1.63–2.00, 5–95% **1.24–2.33**
* the SIA era lookup has **3 distinct values** for 191 houses

Within-era spread, which the lookup collapses to a single number:

| era | n | geometric median | geometric 5–95% | SIA lookup |
|---|---:|---:|---|---:|
| < 1975 | 42 | 1.70 | **1.23 – 2.32** | 2.00 |
| 1976–80 | 26 | 1.87 | 1.27 – 2.37 | 1.65 |
| 1981–85 | 29 | 1.83 | 0.97 – 2.33 | 1.65 |
| 1986–90 | 12 | 1.90 | 1.66 – 2.37 | 1.65 |
| 1991–95 | 15 | 1.79 | 1.16 – 2.10 | 1.65 |
| 1995–00 | 10 | 1.84 | 1.54 – 2.33 | 1.65 |
| 2000–10 | 38 | 1.74 | 1.30 – 2.28 | 1.40 |
| > 2010 | 19 | 1.83 | 1.50 – 2.14 | 1.40 |

**Roughly a 2× range inside a single era.** Two houses of the same age and same
heated area can differ by 2× in envelope area. That is a first-order term and the
lookup cannot see it.

## 2. NEW FINDING — the Gebäudehüllzahl is NOT era-dependent in this fleet

Measured medians run **1.70 to 1.90 across every era, with no trend**. The SIA
lookup imposes a strong one: 2.00 pre-1975 falling to 1.40 post-2000.

**Building shape barely changed by era in this fleet. Insulation did.**

This matters directly for P2's failure F1. Assigning the Hüllzahl by era imports a
**spurious era trend** — it makes old houses look 43% less compact than new ones
when the audit says they are not — and that trend inflates the old-versus-new
difference on top of the genuine U-value difference. **Part of P2's pre-1975 1.59
gap is this artefact, not the U-values.**

## 3. TEST 1 — FAILED AGAIN. The balance-temperature route does not work

Against the fitted changepoints, 133 households with a qualifying fit
(fitted `tau` median 15.2 °C, 5–95% 12.8–18.5):

| balance temperature | median | median gap to `tau` | **corr(`tau`)** |
|---|---:|---:|---:|
| SIA era lookup (P2) | 17.2 | +1.7 | **−0.052** |
| real geometry, b=0.5 | 17.4 | +1.8 | **−0.066** |
| real geometry, b=1.0 | 17.6 | +2.0 | **−0.057** |

Real geometry gave `T_bal` **45 distinct values instead of 5** — and the
correlation with the fitted changepoint **did not move off zero**. It got very
slightly worse.

**Conclusion: the balance-temperature route fails for a reason other than
geometry.** Candidates, none tested: the fitted `tau` is itself noisy (the parent
measured ICC 0.59 even after filtering); or the real balance point is driven by
occupant behaviour — setpoint, window opening, which rooms are actually heated —
far more than by envelope.

**The fixed `HDD_12` settled in P0 stands. Do not ship a computed per-household
base.** The +1.8 °C offset remains consistent with omitting solar gains, but that
explains the level, not the absent correlation.

## 4. TEST 2 — the disagreement did not vanish, but it became UNIFORM

Physics design load versus SIA 384.201:

| era | SIA lookup (P2) | real geometry | benchmark | ratio, geometry |
|---|---:|---:|---:|---:|
| < 1975 | 95.6 | 85.1 | 60.0 | **1.42** |
| 1976–80 | 54.2 | 59.2 | 45.0 | 1.31 |
| 1981–85 | 54.2 | 57.0 | 45.0 | 1.27 |
| 1986–90 | 54.2 | 61.9 | 45.0 | 1.38 |
| 1991–95 | 41.9 | 42.8 | 35.0 | 1.22 |
| 1995–00 | 41.9 | 46.3 | 35.0 | 1.32 |
| 2000–10 | 31.4 | 35.9 | 32.5 | 1.10 |
| > 2010 | 24.7 | 27.7 | 25.0 | 1.11 |

Pre-1975 improved **1.59 → 1.42**. But the modern eras got **worse** — 0.97 → 1.10
and 0.99 → 1.11 — because the audit says modern houses are far less compact (1.74–1.83)
than the SIA band assumes (1.40).

**Read the spread, not the individual ratios.** Era lookup: 0.97–1.59, **range
0.62**. Real geometry: 1.10–1.42, **range 0.32**. **The disagreement halved and
became roughly uniform.**

That is a genuine improvement and the right way to read it. **A uniform offset
largely cancels in the two-baseline difference; an era-varying one does not.** The
previous "perfect agreement" at 0.97 and 0.99 was partly coincidence — two errors
of opposite sign cancelling in the modern eras only.

A residual uniform ~1.2–1.3 remains and is unexplained. Candidates: the square-plan
wall area is a lower bound so this should bias *low*, not high; missing
temperature-reduction factors on elements other than the ground; or the SIA
384.201 figures assuming something we do not model.

## 5. DEFECT FOUND IN THIS RUN — the basement handling is wrong

By storey count:

| storeys above ground | n | median Hüllzahl |
|---|---:|---:|
| 1 | 28 | **1.64** |
| 2 | 114 | 1.83 |
| 3 | 49 | 1.89 |

**This reads backwards** — a bungalow should carry *more* envelope per heated m²,
not less. The cause is my own code:

* `n_above` counts only above-ground storeys, but `Building_FloorAreaHeated_Total`
  **includes the heated basement**. So a bungalow-with-heated-basement is counted
  as 1 storey while carrying two storeys of heated area, which deflates its
  Hüllzahl.
* **Basement walls against earth are ignored entirely** — no area, no b-factor.

**73 of 214 households have a heated basement.** The within-era spread finding
(§1) and the era-independence finding (§2) both survive this — they concern
variation and trend, not level — but **the storey-count table must not be quoted**
and the level carries this defect. Fix before P4.

## 6. Within-era versus across-era ranking

Miguel, 2026-09-10: the pre-1975 inconsistency matters less because we are
comparing, and those buildings are past their life cycle anyway.

**True within an era. False across eras.** If every pre-1975 house is inflated by
the same factor, their order among themselves is untouched — a common factor
cannot reorder a list. But a **single fleet-wide ranked list** puts inflated
pre-1975 houses above correctly-scaled modern ones that may waste more.

**So: rank within era is safe under P2's F1. One fleet-wide list is not, until the
residual offset is resolved.** §4 improves this materially by making the offset
uniform, which is much closer to safe than an era-varying one.
