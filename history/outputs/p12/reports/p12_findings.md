# P12 — integrating the fault models. The 2×2 works; the models do not generalise.

Run 2026-09-11. `p12_integration.py`, transcript `outputs/p12/logs/p12_run.txt`.
Bundle: `../Heat_Pump_Failure_Prediction/artifacts/models.joblib`, trained
2026-09-10, 89 train / 30 test, 38 features, base rate 0.854.

**Two results, pointing opposite ways.**

1. **The 2×2 is populated and usable — on the recorded protocol flags.**
2. **The fault models do not survive held-out data**, so the axis cannot yet be
   extended to households without an audit.

---

## 1. The axes are NOT independent

**8 of the 38 fault-model features are fields the physical model also requires:**
`Building_ConstructionYear`, `Building_FloorAreaHeated_Total`,
`Building_Residents`, `HeatPump_Installation_Type`,
`HeatPump_Installation_HeatingCapacity`, both `HeatDistribution_System_*` flags,
`DHW_Production_ByHeatPump`.

Agreement between the axes is therefore **partly mechanical**. Still
operationally meaningful — the cells imply different interventions — but
**never present it as "two independent methods agreeing".**

**Measured mitigation:** the models' scores correlate with the physical excess at
only **−0.145 to +0.185** (Spearman). The shared inputs are *not* dominating their
predictions. That is a point in the models' favour, and the strongest thing this
run found for them.

## 2. The 2×2, on 97 households where both axes exist

|  | no physical excess | physical excess confirmed |
|---|---:|---:|
| **no setting fault** | **D** 3 | **B** 18 |
| **setting fault recorded** | **A** 10 | **C** 66 |

**C is 68% of the cohort.** Two thirds of audited households carry *both* a
controller fault and a building that materially exceeds code. The cell this
workstream was built to expose is **the common case, not the corner**.

**A is only 10 households** — a setting fault with no physical excess, the case
where turning the curve down is cheap and should stick.

**Built on the RECORDED protocol flags, not on model predictions.** All 214
audited households carry the inspector's verdict; the model exists to reach
households *without* an audit. On this cohort no model is needed.

## 3. THE MODELS DO NOT GENERALISE

AUC against the recorded flag, train versus held-out test:

| target | base rate | model | **train** | **test** |
|---|---:|---|---:|---|
| heating curve too high | 0.496 | logistic | 0.841 | 0.560 [0.329, 0.773] |
| | | random_forest | **1.000** | 0.454 [0.259, 0.667] |
| | | hist_gbm | **1.000** | 0.477 [0.273, 0.690] |
| night setback active | 0.387 | logistic | 0.843 | **0.230 [0.060, 0.460]** |
| | | random_forest | **1.000** | 0.400 [0.195, 0.630] |
| | | hist_gbm | **1.000** | 0.520 [0.305, 0.740] |
| heating limit too high | 0.277 | logistic | 0.959 | 0.560 [0.343, 0.759] |
| | | random_forest | **1.000** | 0.486 [0.269, 0.704] |
| | | hist_gbm | **1.000** | 0.468 [0.250, 0.681] |
| DHW descaling overdue | 0.193 | logistic | 0.918 | 0.552 [0.296, 0.792] |
| | | random_forest | **1.000** | 0.728 [0.424, 0.960] |
| | | hist_gbm | **1.000** | **0.752 [0.536, 0.944]** |

**Train AUC is exactly 1.000 for random forest and hist-GBM on all four targets.**
Perfect in-sample separation on 89 households × 38 features is memorisation — it
is what those hyperparameters do at that sample size, and it means the train
column carries no information.

**On held-out data, eleven of twelve model-target pairs sit at or near chance.
Six are below 0.5.**

**One is significantly worse than chance:** night setback, logistic,
**AUC 0.230 [0.060, 0.460]** — the interval excludes 0.5 from below. On the test
set that model is systematically anti-correlated with the truth.

**One shows genuine signal:** DHW descaling, hist-GBM, **0.752 [0.536, 0.944]**,
interval excluding 0.5. But **n = 5 test positives**, and DHW descaling is the one
target that is *not* a controller setting.

### Not a coding error, and not a surprise

The S-series measured the same ceiling from the other direction: largest fault
class 43 positives, 58.8% of visits carrying two or more faults, no inter-rater
signal, **and a supervised fault classifier already tested on this data and
rejected**. These figures are consistent with that, not in conflict with it.

**The binding constraint is the label, not the algorithm.** 119 households, four
targets, base rate 0.854, and inspector judgements that no second inspector ever
checked. No hyperparameter fixes that.

## 4. Consequences

**The 2×2 ships as built — on the protocol record.** It needs no model, it is the
inspector's own verdict, and it exists for every audited household.

**The fault axis is scoped to audited households.** Extending it to un-audited
ones was the model's purpose, and held-out performance does not support it yet.

**Do not report train AUC anywhere.** At exactly 1.000 it will be read as accuracy
by anyone who does not know the split.

**The bundle is not self-contained.** Its pickle references `heapo_core`, so that
directory must be importable or `joblib.load` raises `ModuleNotFoundError`.
Matters for any deployment away from the source tree.

## 5. Category C is populated but its split is a PLACEHOLDER

66 households carry both. The compensating/compounding split came out
**63 compounding / 3 compensating**, on a threshold of `actual / E_as_built > 1.5`
that is **declared and arbitrary**.

`E_as_built` excludes appliance electricity, so the ratio exceeds 1 for every
household and **no principled cut exists** (P4 §3). The lopsided split is an
artefact of the threshold, not a finding. **Not usable. Do not display it.**

P7 tested the compensation mechanism directly and returned *not shown* — the
predicted pattern appeared on the right parameter, and the falsification arm
showed nearly the same thing where nothing had been changed.

## 6. What would move this

* **More labelled households.** 119 is the constraint. The protocol cohort is 214,
  so ~95 more exist that the fault models have never seen.
* **A second inspector on a subsample**, to establish whether the labels are
  reproducible at all. Without that, no model can be shown to beat the label noise.
* **Cross-validation instead of a single 30-household split**, which would at
  least narrow intervals that currently span 0.26 to 0.94.
