# P21 — a real Swiss typology, and every other open value, from the verified notebook

2026-09-11. Scripts `p21_notebook_research.py` (import + restricted questions) and
`p21_u_sourced.py` (U scenarios). Evidence: `outputs/p21/data/` — research candidates
(`research/*.json`), import log, raw answers with citations (`q7`–`q13`), scenarios.

## Method

1. **Search.** NotebookLM web research, three queries, 30 candidates, nothing auto-imported.
2. **Argue the candidates.** Import only primary Swiss or standards documents: BFE, TEP
   Energy, SIA, ETH/CEPE, FHNW, EnFK/EnDK, cantonal law, OST, IEA HPT. Plus the primary
   documents read outside the notebook in P14–P20. **20 imported.** Real-estate
   handbooks, lecture notes and blogs were skipped. Purdue failed twice (the URL serves
   HTML) and was dropped; RISE covers the same data.
3. **Ask with the AI reports excluded.** Every question was restricted to the 35
   non-AI sources, so no answer can cite a NotebookLM-generated report.
4. **Verify.** Check each answer against its citations and, where possible, against
   text read directly.

Caveats: q7 failed (network timeout; q13 covers it). q9 and q11 returned no machine
citations; their numbers match cited answers (q8, P20-q2) and are used only where they
agree.

## Findings, value by value — for, against, verdict

### As-built U-values — the core of the deficiency

**Source found:** TEP Energy (2016), *Erweiterung des Gebäudeparkmodells gemäss
SIA-Effizienzpfad Energie*, BFE Schlussbericht, §3.2.1, Abb. 30–33, **EFH**, mean ± SD
by construction period. It is Switzerland's national building-stock model, grounded in
Jakob (2002/2008) and GWR.

| envelope mean (split .50/.22/.18/.10) | registry | **TEP 2016** | Jakob 2002 walls pre-1975 |
|---|---:|---:|---:|
| pre-1975 (pooled by EFH stock share 13/20/27 %) | 1.35 [1.20–1.50] | **0.943 ± 0.081** | 1.103 ± 0.107 |
| 1976–1990 | 0.80 | **0.740 ± 0.083** | |
| 1991–2000 | 0.55 | **0.393 ± 0.044** (TEP pools 1991–2009) | |
| 2001–2010 | 0.40 | **0.393 ± 0.044** | |
| post-2010 | 0.24 | **0.319** (MuKEn 2008 legal limit), lo 0.267 (MuKEn 2014) | |

* **For.** It is a real, Swiss, EFH-specific, BFE-funded source. The chart readings pass
  a check against the report's own text: roof −58% and cellar ceiling −42% from 1976–90
  to 1991–2009, against the text's "~60%" and "~40%". A second Swiss source (Jakob 2002)
  also lands below the registry. **The registry's pre-1975 band does not overlap either
  of them.**
* **Against.** The values are read off a chart (±~0.05). TEP pools 1991–2009. Post-2010
  is only a legal ceiling, not a measured stock. **The element-area split still carries
  the dead TABULA-CH citation.**
* **What the meter and the table say (validation only, trap 4 applies):**

| | S0 live | S1 TEP | S3 TEP + P20 JAZ |
|---|---:|---:|---:|
| fleet deficiency | 321,330 | **256,161 (−20%)** | 244,906 (−24%) |
| pre-1975 median | 3,303 | 2,303 | 1,990 |
| worst quartile kept | 45/45 | 38/45 | 37/45 |
| pre-1975 measured/physics (step slope) | **0.80** (over-predicted) | **1.07** | 1.14 |
| era range | 0.52 | 0.46 | **0.39** |
| ρ per m² | 0.534 | 0.543 | **0.595** |
| pre-1975 design load / SIA table | **1.27** | **0.96** | 0.96 |

**Four independent checks improve at once:** P2's F1 (the pre-1975 design-load clash),
the pre-1975 over-prediction, the era gradient, and rank. The level moves *away* from 1.0,
so this cannot be an accidental fit. **Verdict: adopt TEP 2016.** The middle eras
(1991–2010) remain under-predicted by 28–33%, which is expected because TEP pools
1991–2009 and the MuKEn 2000 ceiling (≈0.44) sits above its mean.

### Reference U — 0.269

MuKEn 2014 limits (EnDK/Energiehub 2014, Abb. 13: opaque 0.17, ground 0.25, window 1.0)
on the same split give **0.267**. The value holds; its citation changes from "SIA 380/1
targets" to the legal MuKEn 2014 limits. **Verdict: keep 0.269, re-cite.**

### Heating JAZ — P20 confirmed by a second paper

RISE (14th IEA HPC 2023, Paper 478, Table 1, N=26) reproduces the OST table:
SPF_SH air 3.7 / 3.3 / 2.9, ground 5.7 / 5.0 / 4.4; DHW 2.8 / 3.2. OST 2021/22: DHW JAZ
air 2.9, ground 3.3. FAWA: +5 K flow → −8% JAZ; ground-source +1.2% per installation
year; **no ageing loss over 9 years**. **Verdict: adopt P20-S2** (heating-only JAZ +
DHW JAZ by type, 2.8 / 3.3). A vintage-aware JAZ is possible (installation year
129/214) — flagged.

### Ground factor b — 0.50

Normative SIA 380/1:2015 gives 0.7 (cellar fully in ground) and 0.8 (partly).
**Measured** in Swiss basements (Hoffmann & Geissler, FHNW, Energy Procedia 122, 2017):
cellars run ~8 K warmer than the standard assumes. Measured b is **0.51**, and the
authors **recommend 0.5 for existing buildings with uninsulated cellar ceilings**. TABULA
also uses 0.5. **Verdict: keep 0.5, now doubly sourced; band 0.5–0.8** (measured →
normative), replacing the unsourced 0.40–1.00.

### Thermal bridges — ΔU_tb

TABULA CCM, now inside the notebook: **0.10** for the original state, 0.05 for advanced
refurbishment. Minergie/EnDK 2014: thermal bridges are ~10% (5–20%) of design heat load.
EnFK 2023 limits for new build: 0.15–0.30 W/mK. **Verdict: 0.10 on both baselines**
(deficiency unchanged); a better-junction reference (0.05) remains a policy option.

### Design outdoor temperature — −10 °C → −8 °C

EnDK/Energiehub 2014 (Klimastation Zürich, "Klima A, kalt": −8 °C) and CEPE 2002
(SIA 382/4: −8 °C) agree. −10 °C occurs only in the AI report. It affects `design_kw`
only (capacity scenario, P15): −6.7%. **Verdict: adopt −8 °C.**

### Air change — 0.7 → 0.6

SIA 380/1's 0.7 is not in the notebook. TABULA gives 0.4 use + 0.2 infiltration = 0.6.
It cancels in the deficiency and moves only the level, the slope and the design load.
**Verdict: adopt 0.6, declared generic (TABULA, not Swiss).**

### DHW demand — 2.33 → 2.61 kWh/person/day

SIA 385/2 via IEA HPT Annex 46 Table 1: EFH "normal" **45 L/p/d** average (simple 40,
high 55). FAWA measured 3,811 kWh/yr for a 4-person EFH, i.e. **2.61**. 45 L at ΔT 50 K
gives 2.62. Heim 2016 measured 40 L/p/d at 63.9 °C. ΔT 50 K is not stated in the
sources and is a physics assumption. **Verdict: adopt 2.61, band 2.33–3.20**
(simple–high standard).

### Setpoint — 20 °C

TABULA Table 1, RISE and the HEAPO paper all give 20 °C. **VERIFIED.**

### Still open

* **The element-area split** (.50/.22/.18/.10) is still unsourced. Every envelope mean
  above depends on it.
* **EN 12831 n_min** is not in the notebook; P15's step S1 stays unverified.
* **Prebound by building age**: not in the sources.
* **1991–2000 vs 2001–2010:** TEP does not separate them.
