# P8 — what the oversizing costs. A bounded scenario, not a measurement.

Run 2026-09-10. `p8_capacity_price.py`, transcript `outputs/p8/logs/p8_run.txt`.
**160 households carrying both a deficiency and an installed capacity.**

**Nothing here is measured. It answers a conditional, and the shape of the
assumption is stated so anyone can disagree with it.**

---

## 1. What was and was not supplied

FHNW field analyses and the EU BEYOND project put the seasonal penalty from
unmitigated soft faults and short-cycling at 10–25%; Brudermueller et al. (2023)
map cycling frequency to a derating of roughly **0.05–0.15**.

**That is a range for the penalty. Nothing supplied maps SIZING RATIO to a
penalty.** So the shape is assumed and declared:

```
d(ratio) = clip((ratio − 1.0) / (2.0 − 1.0), 0, 1) × d_max
```

zero at ratio 1.0, rising linearly to the full penalty at 2.0, flat above.
**An assumed shape is not a finding.** A different shape gives a different answer
and this run cannot say which is right.

## 2. The sizing ratio, on our own physics

| | |
|---|---|
| median | **1.00** |
| IQR | 0.79 – 1.29 |
| 5–95% | 0.49 – 1.88 |
| above 1.3 | 37 (23.1%) |
| above 2.0 | 4 (2.5%) |

**Half the fleet sits at or below its required capacity**, so half carries no
capacity penalty at all under any assumption.

Note this contradicts P1's median of 1.30 on the SIA 384.201 table. **Both cannot
be right, and the difference is the unexplained design-load offset.** Neither
settles the other and it is circular to claim otherwise.

## 3. The scenario

| d_max | fleet kWh/yr | median household | n > 100 kWh |
|---|---:|---:|---:|
| 5% | 3,825 | **0** | 11 |
| 10% | 7,650 | **0** | 31 |
| 15% | 11,476 | **0** | 38 |

Against the terms that **are** measured, on the same 160 households:

| term | kWh/yr | share of measured deficiency |
|---|---:|---:|
| envelope | 220,726 | 75.0% |
| DHW | 56,721 | 19.3% |
| emitter | 16,807 | 5.7% |
| **capacity (mid) — SCENARIO** | **7,650** | **2.6%** |

## 4. Rounding error or rival? Both, depending on where you look

**At fleet level capacity is small** — 2.6% of the deficiency, an eighth of DHW,
a thirtieth of the envelope. It does not rival the envelope at any `d_max` in the
supplied range.

**At household level it is concentrated, not uniform:**

* the **median household carries zero**, because half the fleet is at or below
  required capacity
* **52 of 160** carry a capacity term exceeding their own DHW term
* **17 of 160** carry one exceeding their own **envelope** term

**A fleet share hides that completely. Report capacity per household, never as a
percentage of the total.**

## 5. Validation here is CIRCULAR — stated so nobody quotes it

AUC of the capacity **cost** against the inspector's oversized flag:
**0.793 [0.656, 0.911]**, n 14 vs 136.

**This is not independent evidence.** The cost is a monotone function of the
sizing ratio, and P1/P4 already validated the *ratio* against this same flag
(0.772 and 0.786). The AUC is the same fact restated in different units, not a
second confirmation.

**What would be independent:** disaggregating actual cycling frequency from the
15-minute meter and checking it rises with the sizing ratio. Not done — that is
meter-based work and belongs on the A/C axis.

## 6. What ships

**Category B ships the MEASURED deficiency: envelope + emitter + DHW.**

**The capacity cost ships as a separate, labelled scenario column and is never
summed into the headline.** Its shape is assumed and its range is wide. On the
160 households the scenario would add 2.6% to the fleet figure — small enough
that adding it silently would be a misrepresentation rather than an improvement.
