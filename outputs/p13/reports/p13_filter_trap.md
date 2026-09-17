# P13 addendum — the filter trap

Checked 2026-09-11 at Miguel's prompt: *"confirm the heating curve and limit by the
models is not 100% related to heat slope and we are targeting the same variable —
possible trap."*

**Verdict: the trap as posed is RULED OUT. A worse one was found underneath.**

---

## 1. Not the same variable twice

| | heating curve | heating limit |
|---|---:|---:|
| Spearman, fault probability vs slope excess | **−0.392** | **−0.234** |
| share of logistic \|coef\| on slope/weather features | **24%** | **22%** |

The filter and the sort are genuinely different signals. (Aaditya's `hdd_slope`
feature and our measured slope agree at ρ **+0.790** — same meter, different
fitting window — so the slope *is* an input to his model, just not a dominant one.)

## 2. The real trap — the filter pulls AGAINST the sort

**The heating-curve probability is NEGATIVELY correlated with slope excess (−0.39).**
Physics predicts the opposite: a curve set too high delivers more heat per degree of
cold, which *raises* the slope.

So `UNJUSTIFIED_LOAD` — high slope excess **and** high fault probability — is the
intersection of two quantities that move in **opposite directions**. It is not a
principled intersection, which is why it comes out shrunken and idiosyncratic.

### The recorded label shows the same inversion — replicated

| slope measure | against the inspector's heating-curve flag |
|---|---:|
| **our physics-based slope excess** (this check, n=97) | **AUC 0.441** |
| **S-series peer slope score** (`STRATUM_TRACEABILITY.md` §3, 43 positives) | **AUC 0.386, "backwards"** |

**Two independent slope measures, the same inversion.** This is a finding about the
*label*, not a quirk of Aaditya's model. The recorded "heating curve too high" flag
does not track the heating slope on this data.

**Candidate mechanism — untested:** in a well-insulated house an over-high curve
barely raises consumption, so an inspector sees a high setting and flags it on a
house with a low slope. In a leaky house a high curve may be *needed* and go
unflagged. That produces exactly this inversion, and it is the **compensation
hypothesis** (P7) seen from the other side.

## 3. The heating-limit model is learning documentation thoroughness

Its largest coefficients sit on **missingness indicators**:

| feature | True | False | **missing** |
|---|---:|---:|---:|
| `HeatDistribution_System_BufferTankAvailable` | 30 | 19 | **70** |
| `Building_ElectricVehicle_Available` | 18 | **0** | **101** |

| buffer-tank field | n | heating-limit fault rate |
|---|---:|---:|
| **recorded** | 49 | **0.45** |
| **left blank** | 70 | **0.16** |

**A 2.8× difference driven only by whether a form field was completed.** A thorough
inspector records more of everything, faults included — so the model learns *who
filled in the form*, not *which controller is misconfigured*.

`ElectricVehicle_Available` is True/NaN with **zero False** — the column this
workstream flagged unusable from the start (parent trap 3). It should never have
been a feature.

## 4. The model adds nothing beyond the slope

AUC against the recorded fault:

| | model (held-out 30) | slope alone (same 30) | slope alone (all 97) |
|---|---:|---:|---:|
| heating curve | 0.567 | 0.617 | 0.441 |
| heating limit | 0.527 | 0.670 | 0.516 |

On the held-out 30 the bare slope beats the model — but on all 97 the bare slope is
at chance too. **Nothing robustly predicts the recorded fault.** The 30-household
figures are too narrow a sample to rank the two against each other.

## 5. On the claimed slope range

An external summary claimed relative slope deviations of −0.87 to +2.65. **Ours:**
min −0.65, p5 −0.35, **median +0.29**, p95 +1.33, max +2.42 (n=172). Same order of
magnitude, not the same numbers. Our median matches the ~22% baseline offset P9
measured, which is the expected centre.

## 6. Consequence — decided

**The `UNJUSTIFIED_LOAD` fault filter was not principled as built.** Heating curve is
anti-correlated with the sort key; heating limit is driven by blank form fields.
Neither is a clean gate. **Miguel's decision, 2026-09-11: the fault is shown as
information and never gates status or rank.** See `p13_findings.md`.

Aaditya's model is used read-only; nothing in this workstream changes it.
