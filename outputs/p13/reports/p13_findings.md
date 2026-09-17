# P13 — the combined visit queue

Run 2026-09-11, revised the same day. `p13_visit_queue.py`, transcript
`outputs/p13/logs/p13_run.txt`, output `outputs/p13/data/p13_visit_queue.csv`.
**172 households.** Companion: `p13_filter_trap.md`.

**Design, settled with Miguel: one order, two kWh columns, and the fault shown as
information — never as a gate.**

| | |
|---|---|
| **sort on** | heating consumption the building does not justify |
| **show, never summed** | what a technician could plausibly recover · what they cannot |
| **show, never gate** | the fault model's suggestion and its probability |

**Revision history.** The first version *filtered* on the fault probability:
`UNJUSTIFIED_LOAD` required slope excess **and** a named fault. The filter was
then checked (`p13_filter_trap.md`) and found to pull **against** the sort, so
Miguel removed it the same day. This report describes the design as it now ships.

---

## 1. Why the slope, not the level

| on the same 172 households | median | 5–95% |
|---|---:|---|
| **level** excess, `actual − E_as_built` | **~6,000** kWh/yr | ~2,000 – ~15,800 |
| **slope** excess, `(β_meas − β_phys) × HDD × 365` | **719** kWh/yr | −1,498 – 3,502 |

**The level is dominated by appliance electricity** and is unusable as a fault
size. **Appliances are weather-independent** — a fridge does not run harder when it
is cold — so comparing the measured heating slope with the physical one cancels
them. A heating curve set too high raises exactly the slope.

**~22% slope excess is baseline for every household** (P9 measured the physics
running that far below the meter), not a fault. **Rank within era; never read the
absolute figure as recoverable energy.**

## 2. The fault suggestion — shown, never gated

**Model: `logistic`, read-only from Aaditya's bundle.** Chosen because its
probabilities spread; random forest and hist-GBM reach train AUC exactly 1.000 and
collapse to ~0/1. Suggests **heating curve** or **heating limit**. **Night setback
is advisory only** — logistic scores it at held-out AUC 0.230, inverted.

A fault is **named** on the row only above probability 0.50. **That threshold
affects only the label on the row — never the status, never the rank.**

### Why it no longer gates

| finding | measured |
|---|---|
| heating-curve probability vs slope excess | **ρ −0.39** — physics predicts positive |
| recorded curve flag vs our slope excess | **AUC 0.441** |
| recorded curve flag vs S-series peer slope | **AUC 0.386, "backwards"** |
| heating-limit fault rate, buffer-tank field filled in / blank | **0.45 / 0.16** |

The filter pulled against the sort, the inversion is a **replicated property of
the label**, and the heating-limit model is largely learning **which forms were
filled in**. A gate built on that ranks by documentation, not by controllers.

## 3. The queue

| status | n | meaning |
|---|---:|---|
| **`SLOPE_EXCESS`** | **125** | heating the building does not justify — **ranked within era** |
| `NO_SLOPE_EXCESS` | 47 | heating response fits the building |
| `NOT_ASSESSABLE` | 42 | in the export only — cannot compute |

Within `SLOPE_EXCESS`, the fault information carried alongside:

| | n |
|---|---:|
| fault model scored the house | 72 |
| ...and names a fault ≥ 0.50 | 40 |
| fault model never ran | 53 |

**None of these affects the rank.**

## 4. Top of the queue — slope excess alone

| house | era | recoverable | **not** recoverable | fault prob | model suggests | fitted on? |
|---|---|---:|---:|---:|---|---|
| **1114677** | post-2010 | **6,162** | 1,261 | — | — | **not scored** |
| 6981151 | pre-1975 | 5,660 | 2,722 | 0.98 | heating limit | held out |
| 680861 | 1991–2000 | 5,504 | 1,007 | 0.83 | heating curve | held out |
| 881223 | 1976–1990 | 5,435 | 3,340 | 0.20 | — | held out |
| 991118 | 1976–1990 | 5,004 | 2,581 | 0.22 | — | held out |
| 102766 | 2001–2010 | 4,493 | 1,678 | — | — | not scored |

**4 of the top 12 were never scored by the fault model** and reach the top on slope
excess alone. **The new #1 is one of them.** Under the gate it could not have
appeared.

**`881223` and `991118` are the removal working as intended.** Both are held out, so
their probabilities are honest, both carry a large slope excess, and the model
gives them only 0.20 and 0.22. The gate would have pushed them down on the strength
of a model that pulls against the sort. They now rank 4th and 5th.

**Two rows show why the kWh columns are never summed:**

* **`7374981`** — post-2010, **better than code** (−140), 3,752 recoverable: a
  **pure technician case**, nothing to insulate.
* **`7771161`** — 1,862 recoverable against **4,472 not recoverable**: the setting
  may be wrong, and fixing it leaves most of the problem in the walls.

## 5. What this queue is, and is not

**Is:** a ranked list of heating the building does not justify, with a separate
figure for what needs a builder, and the fault model's suggestion attached where it
exists.

**Is not gated on the fault** — measured to pull against the sort and removed,
Miguel 2026-09-11.

**Is not an expected saving.** No probability was multiplied by any kWh.

**Is not free of the ~22% baseline offset** (P9). Rank within era.

**Read-only on Aaditya's tree.** Nothing here writes to it or re-fits anything.
