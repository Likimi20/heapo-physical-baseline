# P7 — the compensation test

Run 2026-09-10. `p7_compensation.py`, transcript `outputs/p7/logs/p7_run.txt`.
**83 households with both sides sufficient at 180/60/60. 52 curve changed,
26 left alone, 5 not recorded.**

**Verdict: NOT SHOWN. The predicted pattern appears, on the right parameter, in
the right direction — and the falsification arm shows nearly the same thing where
nothing was changed. Both halves are required.**

---

## 1. The hypothesis

A setting fault can be a **rational response** to a physical deficiency. A badly
insulated house, or one with radiators sized for a 70 °C oil boiler, leaves the
occupants cold — so someone turns the heating curve up. The inspector writes
"heating curve too high", and it is too high, **and it is doing its job.** Turn it
down and the house gets cold and the occupant turns it back up.

**Prediction:** among households whose heating curve the consultant **actually
changed**, those with a large computed physical deficiency should show **less**
post-visit reduction.

Three independent sources: **deficiency** from the physics (never touches the
meter), **outcome** from the meter, **label** from the inspector. The moderator
cannot be contaminated by the outcome it moderates.

## 2. Design, and why the control arm is better than a placebo

| arm | n |
|---|---:|
| curve changed at the visit | 52 |
| curve left alone — visited, inspected, this setting untouched | 26 |
| not recorded | 5 |

**The control is visited households whose curve was not touched.** The visit
itself, its season, and the attention it brought are common to both arms — which
a pseudo-date placebo (S10's method) cannot achieve.

Sufficiency is **strict, 180 days / 60 warm / 60 cold on each side**. Relaxing to
120/30/30 buys three households (86 vs 83), so there is no case for loosening it
and it was not loosened.

## 3. Did the curve change do anything at all?

| outcome | changed (n=52) | unchanged (n=26) | AUC changed-over-unchanged |
|---|---|---|---|
| heating slope, % | −5.03 [−11.29, +1.20] | −3.16 [−9.36, −0.01] | **0.501 [0.368, 0.637]** |
| normalised level, % | −7.77 [−9.80, −5.76] | −4.69 [−7.34, −2.24] | **0.408 [0.276, 0.547]** |

**Neither interval excludes 0.5.** Consistent with S10's null (visited vs placebo
AUC 0.474). Both arms drifted downward; the change is not separable from the drift.

## 4. The compensation test

Among the 52 whose curve **was** turned down, split at the median computed
deficiency:

| outcome | low deficiency (n=26) | high deficiency (n=26) | AUC high-over-low |
|---|---|---|---|
| **heating slope, %** | **−11.74** [−15.04, +4.55] | **−0.65** [−6.80, +3.80] | **0.596 [0.436, 0.759]** |
| normalised level, % | −9.09 [−10.34, −4.59] | −6.19 [−12.61, −3.77] | 0.536 [0.382, 0.689] |

Continuous check, Spearman of deficiency against the change:
**slope +0.276**, level +0.117 (n=52).

**Three things point the right way:**

1. **The median gap is large** — houses with a small deficiency dropped 11.7% on
   the heating slope; houses with a large one dropped 0.65%, essentially nothing.
2. **It lands on the right parameter.** The heating curve controls the *slope* —
   how much heat per degree of cold. Compensation should show up there and not in
   the level, and that is exactly the pattern: slope AUC 0.596 and rho +0.276,
   level AUC 0.536 and rho +0.117.
3. Direction is as predicted in both outcomes and both statistics.

**And it is not enough:**

* **The interval crosses 0.5** (0.436 – 0.759).
* n = 26 per group.

## 5. The falsification arm — this is what stops the claim

The same split, on the 26 households whose curve was **left alone**:

| outcome | AUC high-over-low |
|---|---|
| heating slope, % | **0.562 [0.320, 0.775]** |
| normalised level, % | **0.627 [0.396, 0.840]** |

**Deficient houses drift upward relative to non-deficient ones even when nothing
was changed.** On the level the control arm's AUC (0.627) is *higher* than the
treatment arm's (0.536), which argues actively against a blunting interpretation
there.

On the slope the treatment arm (0.596) does exceed the control (0.562), which is
the direction compensation predicts — but the gap is 0.034 with intervals spanning
0.3 to 0.8. **At this n that difference is not measurable.**

**So section 4 may be measuring drift among deficient houses, not blunting of a
fix.** That is precisely what the falsification arm was built to detect, and it
did its job.

## 6. What this changes, and what it does not

**Does not change:** the C-class definition. It was always **defensible on
mechanism, unproven on evidence**, and it remains exactly that. The
compensating/compounding split stays a computation, and stays unvalidated.

**Does not rescue S10's null.** The compensation mechanism remains a *candidate*
explanation for why the visits did not move consumption. It has now been tested
once and not confirmed.

**Does add one thing worth keeping:** a possible drift effect. Households with a
large computed physical deficiency appear to trend upward relative to others
regardless of intervention (§5). Untested, unexplained, plausibly regression to
the mean or an age correlate. **Logged, not chased.**

**Honest summary: not shown to work, not shown to fail.** The project's standard
phrasing, and both halves are required. A larger inspected cohort — or the same
test on a second dataset through the adapter — is what would settle it.
