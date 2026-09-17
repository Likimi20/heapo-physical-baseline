# P22 — Miguel's decisions applied to the live model

2026-09-11. Decisions: 1–6 yes, 7 yes as European standard method, one more notebook
search for the area split, carried-over corrections applied. **The dashboard export
(`p11_export.py` → `physical_baseline_v1`) was NOT regenerated — that is for the closing
session.**

## What changed in code

| file | change |
|---|---|
| `constants_ch.json` | written by `p22_registry.py` (deterministic). Published inputs under `inputs`; U-values DERIVED from them |
| `p22_registry.py` | TEP 2016 element U × Swiss area split → envelope means; band widened to cover the German TABULA split |
| `p_physics.py` | JAZ from a full published table, none derived (`JAZ_KEYS`); DHW JAZ by pump type (`JAZ_HOTWATER_KEYS`); thermal-bridge surcharge with one draw on both baselines; optional `hdd_normal_per_day` role; `u_as_built` point = registry value when unrenovated; ground-source radiator tier penalty removed; `GSHP_DERIVE_SPREAD` removed |
| `p_adapter_heapo.py` | `station_normals()` — station normal-year HDD and its relative SE (weather only) |
| `p13_visit_queue.py` | v2: post-visit days, free heating-season step, band status, ranked on the lower bound, normal-year annualisation. v1 archived in `outputs/p13/data/archive_v1_2026-09-11/` |
| `p_pipeline_test.py` | C: every JAZ published and ordered (4.4 ban retired); D: reference within post-2010 band, U non-increasing; H: normal-year route, record length asserted absent, new pins; K: registry inputs' statuses and derivation reproduced exactly |

**127/127 tests, P10 23/23.**

## The area split — the last fake receipt, replaced

Notebook q14 (`outputs/p22/data/q14_area_split.json`) returned it **without machine
citations**, so the value was **read in the primary PDF**: TEP Energy / INSPIRE
International Final Report (2015), Table 15, Swiss reference SFH. Façade (excluding
windows) 206 m², pitched roof 120, cellar ceiling 80, windows 3.3 + 8.3 + 13.2 + 8.3 =
33.1, on 210 m² heated floor area (form factor 2.09). Shares: **wall 46.9 / roof 27.3 /
floor 18.2 / window 7.5 %**. The German TABULA SFH I split (39.5 / 29.0 / 24.0 / 7.5)
widens the bands. The split moves the envelope means by only 2–4%.

The same table gives a Swiss reference SFH with element U-values (façade 1.0, roof 0.85,
window 3.0, cellar ceiling 0.9), which is **≈1.09 on the envelope**. Swiss pre-1975-type
estimates now span **0.90 (TEP) – 1.09 (INSPIRE) – 1.10 (Jakob)**, all far below the old
1.35. Table 15 also gives Swiss SFH non-heating electricity of 22 kWh/m²·a, ≈4,600 kWh/yr,
a cross-check on the BFE appliance value (4,048 for 4 persons).

## The registry

| era | old (dead citation) | **P22** [band] |
|---|---:|---:|
| pre-1975 | 1.35 [1.20–1.50] | **0.903** [0.824–0.982] |
| 1976–1990 | 0.80 | **0.709** [0.630–0.788] |
| 1991–2000 | 0.55 | **0.364** [0.323–0.405] |
| 2001–2010 | 0.40 | **0.364** [0.323–0.405] (TEP pools 1991–2009) |
| post-2010 | 0.24 | **0.269** [0.247 MuKEn 2014 – 0.291 MuKEn 2008] |
| reference | 0.269 | **0.247** [0.247–0.252] (MuKEn 2014) |

Heating JAZ air 3.7 / 3.3 / 2.9, ground 5.7 / 5.0 / 4.4 (lower band edge = heating + DHW
column); DHW JAZ air 2.8, ground 3.3; b 0.5 [0.5–0.8]; ΔU_tb 0.10 [0.05–0.10]; DHW 2.61
[2.33–3.20] kWh/p/d; T_design −8 °C; n_air 0.6 (TABULA, European standard method).

**Status: 17 VERIFIED, 8 DERIVED (all from verified inputs), 1 PHYSICAL, 1 SECOND_HAND
(`storey_height`, SIA 416), 0 CITATION_MISMATCH; every input VERIFIED.**

## Building axis (Category B), 172 households, normal-year HDD

| | v1 export | **P22** |
|---|---:|---:|
| fleet deficiency | 321,326 | **268,271 kWh/yr (−16.5%)** |
| median | 1,609 | **1,286** |
| envelope / emitter / DHW | 74 / 6 / 20 % | **61 / 8 / 31 %** |

Era medians: pre-1975 2,388, 1976–90 1,131, 1991–2000 537, 2001–10 933, post-2010 72.
Rank vs v1: Spearman **0.928**. Within-era worst quartile: **35 of v1's 41
HIGH_EXCESS households remain.**

DHW grows in share because the sourced DHW demand (2.61 vs 2.33) and DHW JAZ (2.8/3.3 vs
2.3) raise the electric-cylinder term. That is a real, sourced change, not an artefact.

## Visit axis (P13 v2)

| | v1 | **v2** |
|---|---:|---:|
| window | all days | **post-visit** |
| slope fit | straight line | **line + free heating-season step** |
| status from | point estimate | **95% band** (month-block bootstrap × physics MC) |
| assessed | 172 | **145** |
| SLOPE_EXCESS | 125 | **51** (49 were in v1) |
| INCONCLUSIVE / BELOW_PHYSICS | — | 73 / 21 |
| physics / measured | 0.78 | 0.808 |
| median excess | 719 | 593 kWh/yr, median band 1,584 |

Top of the queue on the lower bound: 1114677 (post-2010, never scored by the fault model),
991118, 816910, 881223, 7374981.

## Not done — by instruction or scope

* **Export and dashboard:** closing session. At that point `p11_export.py` needs the
  `station_normals` merge and the new `visit_status` levels (INCONCLUSIVE, BELOW_PHYSICS)
  in its rules. That is a schema change → v2.
* **Vintage-aware JAZ** (installation year 129/214): flagged, later.
* **Diagnostic scripts P14–P21** ran on the old registry and are records, not live;
  P20/P21 patch keys that have since changed.
