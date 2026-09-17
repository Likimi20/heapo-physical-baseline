# P20 — the verified notebook, and the heating JAZ from its primary source

Script `p20_jaz_sourced.py`, transcript `outputs/p20/logs/p20_run.txt`, data
`outputs/p20/data/p20_scenarios.parquet`. Notebook queries: `p19_notebooklm_query.py`,
raw JSON answers with citations in `outputs/p19/data/notebooklm/`. 2026-09-11.

## How the notebook was queried

Root CLAUDE.md names notebook `b02e42f0` ("Fraunhofer ISE: AI-Driven Heat Pump
Innovation and Fault Diagnosis") as the source of record. The `notebooklm` MCP server
is configured but **not loaded in this session** (added after start), so it was driven
through the `notebooklm` CLI. Six questions, every answer saved as JSON with its
citations mapped to source titles.

**Sources 6, 7 and 8 of the 17 are NotebookLM-generated "Research report" documents,
not literature.** An answer that cites only them is circular and is treated as
unverified.

| question | what the notebook returned |
|---|---|
| U by era | **only** the AI report (source 7) — no primary source |
| JAZ by emitter | **primary:** OST P+I 11/12-2020 Tabelle 1 (source 15); FAWA Tagungsband 2004 (source 13) |
| DHW | primary: OST Abb. 3 (DHW JAZ air 2.8 / ground 3.3); FAWA 3,811 kWh/yr for 4 persons |
| thermal bridge, b-factor, EN 12831 n_min | **not in the sources** |
| HDD, T_design, T_set, n_air | HEAPO paper eq. 1 (HDD); everything else only the AI report |
| prior work | HEAPO paper; Weigert 2022 (−1,805 kWh, −15.2% after pre-selection); Brudermueller cycling 2023; FHNW ARX-FDD (Sawant 2026); BEYOND; NREL UMP ch. 8; **prebound effect not in the sources** |

## Correction to P19

**P19 marked the air-source JAZ as CITATION_MISMATCH. That was wrong.** It checked the
OST *Jahresbericht*; the spec's "OST 2020 Tabelle 1" is the article *Wie gut sind
aktuelle Wärmepumpen im Feld?* (Heizungsplaner + Installateur 11/12-2020), whose
Tabelle 1 is "Jahresarbeitszahl der gemessenen Wärmepumpen je nach Einsatzbereich".
The body text, read here, confirms air/water Altbau 2.8 and Sanierung 3.1. Our
2.8 / 3.1 / 3.5 are its **heating + DHW** column. Registry: now VERIFIED.

**CLAUDE.md's rejection of "GSHP + radiators = 4.4" is overturned.** The same table
gives ground-source Altbau/radiators **4.4** (heating) / 4.3 (heating + DHW), below
Neubau/floor **5.7** / 4.9, which is thermodynamically consistent. The spec's error was
in the **floor** value (4.10–4.40, found only in the AI report), not the radiator value.
The derived 3.40 under-credits every ground-source non-floor household. The pipeline
check "supplied GSHP+radiator JAZ of 4.4 is not used" encodes the overturned decision
and must change if S2 is adopted.

Registry after the notebook: **7 VERIFIED, 7 CITATION_MISMATCH** (five U, GSHP floor,
DHW JAZ), 6 SECOND_HAND, 2 DERIVED, 1 PHYSICAL. 115/115 green.

## The scenarios — fixed before the run, none chosen by fit

| | JAZ used | fleet deficiency | median | worst-quartile overlap | phys/meas | ρ per m² |
|---|---|---:|---:|---:|---:|---:|
| S0 live | air heat+DHW, ground 4.25 + derived | 321,330 | 1,609 | 45/45 | 0.946 | +0.534 |
| S1 | Tab 1 heat+DHW, both types | 304,337 | 1,462 | 42/45 | 0.882 | +0.573 |
| **S2** | **Tab 1 heating-only + DHW-alone by type** | **303,634 (−5.5%)** | **1,414** | **41/45** | **0.816** | **+0.579** |
| S3 | FAWA 1996–2003 means, flat | 336,585 | 1,792 | 40/45 | 1.112 | +0.551 |

The 22 ground-source non-floor households: median as-built JAZ 3.58 → **4.70** (S2),
median deficiency 2,517 → 2,174.

## What it means

1. **S2 is the principled choice, on system-boundary grounds, not fit.** The model
   carries DHW as a separate term, so space heating needs the heating-only JAZ and DHW
   needs the DHW JAZ. S0 used a combined column for a heating-only term.
2. **Rank agreement improves (0.534 → 0.579) while the level drops (0.946 → 0.816).**
   The level moving away from 1.0 is not evidence against S2, just as 0.946 was never
   evidence for S0 (trap 4). The rank gain comes mostly from the ground-source houses,
   which the live model got wrong relative to air-source.
3. **Vintage brackets the fleet.** New-system JAZ (S2, 2015+ installations) under-predicts
   the meter; 1996–2003 JAZ (S3) over-predicts it. HEAPO is a mixed-age fleet, so this is
   what it should look like. `HeatPump_Installation_Year` is recorded for **129 of 214**,
   so a vintage-aware JAZ is possible. **Flagged as scope, not started.**
4. **Category B barely moves:** −5.5% fleet, 41 of 45 worst-quartile households unchanged.

## Still unsourced after the notebook

**All five as-built U-values** (only the AI report holds them), GSHP-floor 4.25 (retired
under S1/S2), DHW JAZ 2.3, thermal-bridge surcharge, `b_ground` band, EN 12831 n_min.
The last three were read in primary documents *outside* the notebook (TABULA CCM, BFH
2013, secondary EN 12831). **They are sourced but not in the verified notebook.**
