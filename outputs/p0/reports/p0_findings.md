# P0 — HDD_12 versus HDD_SIA, head to head

Run 2026-09-10. Script `p0_hdd_definition.py`, transcript
`outputs/p0/logs/p0_run.txt`, per-household fits in `outputs/p0/data/`.

**Verdict: `HDD_12`. Fixed permanently for this workstream.**

---

## 1. What was compared

| | definition |
|---|---|
| `HDD_12` | `max(0, 12 − T)` — the project's declared standard |
| `HDD_SIA` | `max(0, 20 − T)` when `T < 12`, else 0 — SIA 381/3, HGT 20/12, what the spec asks for |

Per household, `kwh_day = a + b · HDD`, ordinary least squares, **same household
and same days under both definitions**. Requirement ≥180 usable days, ≥60 warm,
≥60 cold. Paired comparison of R² and RMSE; bootstrap CI over households, 2,000
resamples.

## 2. The structural identity — reproduced, not discovered

On a heating day `20 − T = (12 − T) + 8`, so

> **`HDD_SIA = HDD_12 + 8 · 1{T < 12}`**

Measured over **878,128 / 878,128 usable household-days, 100.0000% exact**,
max absolute deviation 3.55e-15. Correlation on heating days: exactly **1.0000**
(n = 509,936). All-days correlation 0.9368.

**The parent project already derived this** (`../CLAUDE.md`, verified over 8,868
heating days). P0 is an independent reproduction on a 99× larger row count.

**Consequence: `HDD_SIA` is not a rescaled `HDD_12`. It bundles a step function
in with the slope, and the step coefficient is welded to exactly 8× the slope.**

### A divergence from the parent's account, logged

The parent states the SIA boundary is **inclusive** at exactly 12.0 °C ("46
archive days sit there, all carrying 8.0"). Our own recomputed `HDD_SIA` is
**strict**: every household-day at `temp_mean == 12.0` carries `HDD_SIA = 0`.
So `fix_weather_artefacts.py` recomputed with `T < 12` where the archive uses
`T <= 12`.

**96 household-days, 0.011% of the usable panel.** Immaterial to every result
below and it does not touch the verdict. But it is a real divergence between our
artefact and the documented archive rule, and by trap 19 the threshold is exactly
where such a thing gets amplified. **Belongs in the parent's tree, not this one.
Flagged, not fixed.**

## 3. Fit comparison

| population | n | median R² `HDD_12` | median R² `HDD_SIA` | mean ΔR² (SIA − 12), 95% CI | SIA wins |
|---|---:|---:|---:|---|---:|
| protocol cohort, all usable days | 193 | **0.7299** | 0.7226 | −0.0064 [−0.0132, +0.0003] | 84/193 (43.5%) |
| fleet-wide, all usable days | 1,313 | 0.6773 | **0.6782** | −0.0002 [−0.0026, +0.0024] | 665/1,313 (50.6%) |
| protocol cohort, post-visit only | 154 | 0.7315 | 0.7315 | −0.0025 [−0.0102, +0.0052] | 74/154 (48.1%) |

Median RMSE, protocol cohort: **7.4573** (`HDD_12`) vs **7.9319** kWh/day (SIA);
median paired ΔRMSE **+0.1017 kWh/day**, i.e. SIA is worse.

**Fleet-wide the two are a dead heat.** On this workstream's own cohort `HDD_12`
wins by a small but consistent margin. **No population produces a case for SIA.**

## 4. Decomposition — the step is real, the 8× weld is not

`HDD_SIA` is the constrained form of `HDD_12 + step`. Freeing the ratio, protocol
cohort, median R²:

| model | params | median R² |
|---|---:|---:|
| step indicator alone | 1 | 0.5048 |
| `HDD_SIA` alone | 1 | 0.7226 |
| `HDD_12` + **free** step | 2 | **0.7587** |

**Cost of welding the step to 8× the slope: −0.0263 R².**

So the heating-season on/off step carries half the variance by itself and is
worth having. **SIA's problem is not the step, it is the ratio.** If a future rung
wants a season term, it takes it as a **free** parameter — never smuggled in via
the degree-day definition.

## 5. The reason that decides it for THIS model

The three reasons, in increasing order of force:

1. **Fit.** `HDD_12` wins on the cohort, ties fleet-wide, and beats SIA on RMSE.
   Small, but never negative.
2. **Noise amplification (parent trap 19).** The SIA form is discontinuous at the
   threshold, so input noise there is amplified rather than averaged. Measured in
   the parent: a 1.6 °C temperature disagreement became a **9.5 degree-day**
   disagreement under SIA, and nothing under `max(0, 12 − T)`.
3. **No free intercept — decisive here, and specific to this workstream.**
   The S-series *fits* a per-household intercept, which silently absorbs the fixed
   8-degree-day offset. That is exactly why the parent could discard the reference
   temperature at no cost. **This model has no free intercept**: `mu_floor` is
   computed from residents, DHW and appliances, and `beta_H` is computed from
   U·A/COP. Under SIA the model would **predict a discontinuous jump of
   8 · beta_H in daily kWh** at the moment mean temperature crosses 12 °C — a claim
   no building makes, with nothing free to absorb it.

> **A degree-day definition whose offset needs a fitted intercept to hide it
> cannot be used in a model that has no fitted intercept.**

## 6. Standing already, independent of this run

`BASE` = 12 °C is **declared, in production and permanent** — Prof. Mehta's
instruction of 2026-08-27, recorded in `../outputs/decision_log.md`. A move to
8 or 10 °C under the SIA 381/3 replacement is **Abdul's call**, and 15 °C is
closed and not a candidate.

**So P0 confirms an existing instruction rather than making a new choice.** Had it
come out the other way, the finding would have been escalated, not acted on.

## 7. What this does NOT license

* **Not per-household base fitting.** This was a one-off, fleet-wide, declared
  selection between two a-priori definitions. Trap 13 stands: the base is the
  heating limit, the limit is a target fault, and fitting it per household absorbs
  the fault into the parameter.
* **Not a coefficient conversion.** The two specifications are different models,
  not a rescaling. A `beta` fitted or computed against one is **not convertible**
  to the other.
* **Not a reason to drop the season term.** Section 4 says the opposite. If the
  physical model under-predicts at the shoulder of the heating season, a free
  season term is the sanctioned next move.
