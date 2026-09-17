# P9 — validating `term_envelope`, which carries 75–80% of the deficiency

Run 2026-09-10. `p9_envelope_validation.py`, transcript `outputs/p9/logs/p9_run.txt`.
**172 households with both a physical prediction and a measured heating slope.**

**Result: the envelope term is VALIDATED ON RANK — Spearman +0.536 [+0.422,
+0.645] per m², interval nowhere near zero. The magnitude prediction is not
rejected but reveals a systematic error in the era gradient.**

This is the first result in the workstream that validates the term the headline
actually rests on. Oversizing (AUC 0.772/0.786) validated the *capacity* term,
which is 2.6% of the total and ships as a scenario.

---

## 1. Judging the proposed checks before running them

| proposed | verdict |
|---|---|
| slope correlation | **Correct, with a flaw.** Both the physical `U·A` and the measured slope scale with house size, so a raw correlation mostly measures *"big houses use more heat"* — impressive-looking and worthless. **Must be per m².** |
| sub-metered check | **Best in principle, likely too small.** Measured first rather than assumed. |
| consultant categorization | **Weaker than claimed.** It rates *consumption*, not envelope, conflating envelope with settings, occupancy and DHW — and the consultant had seen the bills. Coarse cross-check only. |
| *(added)* era-ratio magnitude | **The sharp one.** A rank correlation cannot fail; a ratio can. |

## 2. TEST 1 — rank, area-controlled

| | Spearman | 95% CI |
|---|---:|---|
| raw physical vs measured slope | +0.540 | [+0.419, +0.648] |
| **area alone** vs measured slope | **+0.292** | [+0.145, +0.432] |
| **per m² — THE TEST** | **+0.536** | **[+0.422, +0.645]** |

**The correlation survives area control essentially untouched** (+0.540 → +0.536)
while area on its own reaches only +0.292. So the agreement is **not** an artefact
of house size.

Per m², the physical prediction varies **only** through construction era,
renovation flags and the geometric Gebäudehüllzahl. There is nothing else left for
it to borrow from — and it still tracks the meter at ρ ≈ 0.54.

For scale: next door, the best statistical stratum key explained roughly 13–21% of
variance in the heating slope. ρ 0.536 is about 29% of rank variance, **from
published constants rather than fitted peer groups.**

## 3. TEST 2 — magnitude. Not rejected, but the era gradient is too steep

Median heating slope per m², kWh/(degree-day·m²):

| era | n | physics | measured | measured / physics |
|---|---:|---:|---:|---:|
| pre-1975 | 37 | 0.01964 | 0.01898 | **0.97** |
| 1976–1990 | 62 | 0.01271 | 0.01598 | 1.26 |
| 1991–2000 | 20 | 0.00988 | 0.01227 | 1.24 |
| 2001–2010 | 35 | 0.00852 | 0.01302 | **1.53** |
| post-2010 | 18 | 0.00582 | 0.00760 | 1.31 |

**The headline prediction:** pre-1975 over post-2010, slope per m².

* physics predicts **3.38×**
* the meter says **2.50×**, 95% CI **[1.68, 3.45]**

**The prediction sits inside the measured interval — but only just, at the top
edge.** Not rejected. Not comfortably confirmed either.

### The systematic finding

**Physics matches pre-1975 almost exactly (0.97) and under-predicts every newer
era by 24–53%.** That is not noise, it is a gradient error: **the U-value spread
across eras is too steep.** Modern buildings consume more than TABULA's U-values
imply.

Candidate explanations, none tested here: thermal bridging absent from a single
mean U; the well-documented design-versus-actual performance gap in new build;
mechanical ventilation not modelled; or occupants heating comfortable houses to
higher temperatures.

**The constants are NOT adjusted to close this.** That is the calibration rule.
It is recorded as a finding about the constants.

**Consequence for the deliverable:** if newer houses are under-predicted, their
deficiency is **understated** and the cross-era tilt toward pre-1975 is
exaggerated. This reinforces the standing rule — **rank within era, never across.**

## 4. TEST 3 — sub-meter. Measured ceiling, not a failure

| | n |
|---|---:|
| households with any `kwh_hp` day | 72 |
| clearing 180/60/60 on the HeatPump channel | 63 |
| **AND modellable here** | **18** |

At n=18: ρ **+0.342 [−0.133, +0.744]** — crosses zero, underpowered exactly as
predicted before running it. Physics / sub-metered slope ratio **0.83**, close to
the 0.78 on the total channel, which is at least consistent.

**The binding constraint is the overlap between sub-metering and the protocol
cohort, not our modelling.** Reported as a measured ceiling.

## 5. Coarse cross-check — and it comes out NULL

Consultant's `HeatPump_ElectricityConsumption_Categorization`, 171 of 172 answer:
129 normal, 26 rather low, 16 rather high.

| rating | n | median `term_envelope` | median measured slope/m² |
|---|---:|---:|---:|
| normal | 129 | 1,132 | 0.01523 |
| rather high | 16 | 1,188 | 0.01693 |
| rather low | 26 | 1,179 | 0.01259 |

**Our envelope term is flat across the ratings — no signal.** The *measured* slope
does order correctly, so the consultant's rating tracks consumption, as expected
from someone who had seen the bills.

**Reported as a null, and it is weak evidence either way** — the rating conflates
envelope with settings, occupancy and DHW. It was never envelope validation and is
not quoted as such.

## 6. Where this leaves the workstream

**`term_envelope` is no longer unvalidated.** Rank agreement with an independent
measurement, ρ +0.536, interval far from zero, surviving area control, on 172
households.

**Two honest qualifications:**

1. **Rank is not magnitude.** The era gradient is measurably too steep, and newer
   houses are under-predicted by 24–53%.
2. **Physics runs about 22% below the measured slope overall** (ratio 0.78). In
   the same direction as the sub-meter check (0.83). Unexplained, untuned.

**What would settle it:** a larger sub-metered-and-inspected overlap than 18, or
the same test through a second adapter on another dataset.
