# P15 — limitation 2, the design-load offset

Script `p15_design_load.py`, transcript `outputs/p15/logs/p15_run.txt`, data
`outputs/p15/data/p15_design_load.*`. 2026-09-11. **190 modellable households.**
No consumption is read; nothing in `p_physics` changed.

## Spec v3's fix is rejected

v3 calls the offset an installer safety margin, α_oversize ≈ 1.25. **Category
error:** installer oversizing is *installed ÷ required*; this offset is *our required
÷ the table's required* — two calculations of the same quantity disagreeing. And
1.25 is the middle of our own measured range, so it would be a correction factor
read off our own result.

## The question P15 asks instead

Our design load is computed with **annual-energy** conventions (SIA 380/1: air change
0.7 h⁻¹, `b_ground` 0.5 unsourced). A design-load table is built with **EN 12831**
conventions. Cumulative steps, each fixed by a source before the run:

| step | change | source | status |
|---|---|---|---|
| S0 | live model, reproduces `evaluate()` design_kw to 7e-15 | — | — |
| S1 | ventilation at n_min **0.5 h⁻¹** | EN 12831, habitable rooms | secondary sources agree; norm not read |
| S2 | ground at f_g1 · f_g2, f_g1 **1.45**, f_g2 = (20 − T_me)/(20 + 10) | EN 12831 Annex D | **f_g1 PENDING VERIFICATION** — the one worked example found is scanned images |
| D1 | transmission only | diagnostic, not a correction | — |

T_me is each station's own annual mean over complete years (weather only): 8.1 °C
(`MqO`) to 11.0 °C. EN 12831 `b_ground` median **0.443** (range 0.435–0.574) against
the live 0.50.

## Results

| era | n | table W/m² | S0 | S1 | S2 | D1 |
|---|---:|---:|---:|---:|---:|---:|
| pre-1975 | 42 | 60 | 1.26 | 1.19 | **1.18** | 1.00 |
| 1976–1990 | 66 | 45 | 1.30 | 1.21 | **1.18** | 0.95 |
| 1991–2000 | 25 | 35 | 1.31 | 1.19 | **1.19** | 0.89 |
| 2001–2010 | 38 | 32.5 | 1.17 | 1.04 | **1.03** | 0.71 |
| post-2010 | 19 | 25 | 1.13 | 0.96 | **0.96** | 0.54 |
| **range across eras** | | | 0.18 | 0.25 | **0.23** | 0.47 |

Fleet median: **1.23 → 1.13 → 1.12.** Ventilation is 22% of the S2 load. The
unrenovated-only table tells the same story (S2 0.95–1.23).

**Correction of record:** CLAUDE.md quotes "1.13–1.49, range 0.36" from P4. The live
model, after P6's footprint fix, sits at **1.13–1.31**. The old figure is superseded.

## What it means

1. **About half the offset is a convention mismatch.** The energy model's air change
   is not a design-load air change. Moving to EN 12831 conventions removes ~0.11 of
   the 0.23.
2. **The remainder is no longer uniform.** Post-2000 houses now match the table
   (0.96–1.03); pre-2000 houses sit **~18% above it**. Before, the offset was flatter
   and "largely cancels" held better. **This weakens the P3/P4 argument that the
   offset cancels in the difference.** It still cancels in the envelope *difference*
   (same geometry both sides) but not in the capacity scenario.
3. **The two external checks disagree with each other, by era, in opposite
   directions.** For pre-1975, physics matches the **meter** slope (P9 0.97) and sits
   18% above the **table**. For post-2000, physics matches the **table** and sits
   24–53% below the **meter**. Neither reference can anchor the other, so **the
   design-load table is not a validation target for the energy model.** It stays a
   cross-check.
4. **What would close the last 1.12 is not identifiable from the data.** SIA tables
   are per m² of Energiebezugsfläche (gross). If HEAPO's heated area is net, our
   W/m² is inflated by EBF/net. That is *what it would take*, not a correction.

## Verdict — PARTLY EXPLAINED

Nothing was tuned. **Open decision (Miguel):** should `p_physics` compute `design_kw`
with EN 12831 conventions (n_min 0.5, f_g1·f_g2) while annual energy keeps SIA 380/1?
It is methodologically right, since design load and annual energy are different
calculations, but f_g1 is unverified. It changes `design_kw` only, and so the P8
capacity scenario. The deficiency does not change.
