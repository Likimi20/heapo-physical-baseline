# Handoff — physical baseline model into the dashboard

**To:** a new chat, driven by Miguel
**From:** the physical baseline model workstream (`PHYSICAL-BASELINE MODEL/`)
**Date:** 2026-09-17 (revised: adds the P27 worked example and a corrected
`phys_no_result_*` cause; replaces the 2026-09-12 note, which described a 65-column export)
**Status:** model revised, **`physical_baseline_v2` built and valid at 66 columns**,
notebook rebuilt, worked example generated, **and the dashboard page is BUILT** —
see §0. What is left is to render-test it and retire v1.

---

## 0. READ THIS FIRST — the page already exists (2026-09-17)

**The integration is done as a SEPARATE v2 page, not as an edit to the old one**
(Miguel, 2026-09-17: keep a clean division between v1 and v2).

**`pages/3_Physical_baseline.py` IS the v2 page** — three views: what the rank means ·
the one list · the worked example. **One tab per workstream, four in total.**

The v1-era page was built against `physical_baseline_v1` and displayed a fault
probability and named fault by direct indexing; v2 removed both columns and replaced
per-era ranking with a single fleet-wide order, so it was **replaced, not patched**. It
is in git history if it is ever needed, and the bundle no longer carries
`physical_baseline_v1.parquet` or the old `SCHEMA.md` because nothing reads them.

Why a new file rather than a conversion: v2 deleted the two columns the old page
displays (`visit_fault_probability`, `visit_named_fault` — direct indexing, so it would
raise `KeyError`, not degrade) and replaced per-era tables with one **fleet-wide** order.
Both are structural.

**Verified against the real export** (pandas, no Streamlit): 158 ranked + 56 not ranked
= **214, none dropped**; every ranked row carries a unit recommendation; every unranked
row names both a reason and a fix; the three walkthrough figures inline with 0
unresolved references. Both pages byte-compile.

**NOT verified: neither page has been RENDERED.** Streamlit is not installed in
`venv_viz` or `.venv`, so nothing here was opened in a browser. `requirements.txt` pins
`streamlit>=1.40`, which covers the `st.pills` calls the pages rely on (page 3 already
used them). **Run it once before demonstrating it.**

### Already done since

* **`PHYSICAL-BASELINE MODEL/p28_page_test.py`** stubs the Streamlit API and **executes
  both pages, every view**, against the real export — so the code is run, not just
  compiled. `../venv_viz/Scripts/python.exe p28_page_test.py`, exit 0, transcript in
  `outputs/p28/logs/`. It asserts no fault string reaches the v2 page and no green among
  its colour tokens (checked as hex, not as a word).
* **The bundled snapshot is refreshed to v2**, v1 retained for the legacy page. Both
  resolution roots verified to satisfy every path the page opens, so a fresh clone runs.

### The page, as it now behaves

**Rendered and driven in a browser on 2026-09-17** (Streamlit 1.64 installed into
`.venv`, which had nothing; `pyarrow` too, which `requirements.txt` omits although the
dashboard reads parquet). 97 rows render, zero green elements on the page.

* **Three views:** what the rank means · the one list · the worked example.
* **`Order the list by`** Total / House / Heat pump / Over code. **Only Total is the
  model's order** (the export ranks on `phys_rank_value_lo_kwh_yr`, which drops a
  `KEEP_IN_LIFE` unit's vintage), so the others show `#` instead of `Rank` and say so.
* **Filters that start OFF:** `No era recorded`, `No finding`, `Never computed`,
  `Record the installation year`. `Keep` starts **ON** on purpose — it describes the heat
  pump, so switching it off also hid houses with bad fabric and a healthy unit.
* **The page always states how many households the filters are hiding**, and which
  filter. Default view: 97 shown, 117 hidden, 92,094 kWh/yr of house-side excess among
  the hidden (all `RECORD_INSTALL_YEAR`, rank 2 included).
* **`st.metric` is banned on this page** and `p28_page_test.py` fails if it appears: its
  `delta` renders green with an up arrow, which turned 215,121 kWh/yr of waste into what
  looked like good news.

### What is left
2. **The v1 export** still sits in the model tree under its own one-cycle rule. Delete
   `outputs/export/physical_baseline_v1.*` and `SCHEMA.md` whenever you like —
   `p11_export.py`'s `PREVIOUS_VERSION` constant is the only code that names them, and
   that is deliberate bookkeeping. Nothing in the dashboard reads v1 any more.

The sections below describe the contract the new page implements; they are still the
reference for *what* it shows and why.

---

Your job **was** to add ONE section to the Streamlit dashboard at
`../Heat_Pump_Failure_Prediction/`. **That is built — read §0 before doing anything.**
The decision record is `PHYSICAL-BASELINE MODEL/CLAUDE.md`, sections **P26** and **P27**.

---

## 1. What you are adding — files that already exist

| file | what it is |
|---|---|
| `outputs/export/physical_baseline_v2.parquet` | the data — **214 rows × 66 columns**, one row per audited household |
| `outputs/export/SCHEMA_v2.md` | **the contract** — every column, its unit, how to display it |
| `outputs/deliverable/DELIVERABLE_physical_baseline.ipynb` | the executed notebook, figures embedded |
| `outputs/p27/reports/p27_walkthrough.md` | **the worked example** — one house traced end to end, every number tagged by where it came from. **Goes in this section** (Miguel, 2026-09-17) |
| `outputs/p27/reports/p27_walkthrough.html` | the same content, print-ready. For the report, **not** for the dashboard — render the `.md` instead |

`physical_baseline_v1.*` is still on disk **for one cycle and is stale** — ignore it.

**The pages read these files. They never re-run the model**, and they load **no other
model**: Aaditya's fault output is not in this export and not on these pages.

## 2. Copy the dashboard's existing pattern

* `pages/1_Forecast_cycle.py` — reads its export through an env override,
  `Path(os.getenv("F6_EXPORT", ...))`. **Do the same.**
* `pages/2_Peer_comparison.py` — embeds a notebook with
  `notebook_render.render(ANALYSIS_NOTEBOOK, show_code=show_code)`. **Do the same.**

```python
PB_DIR   = Path(os.getenv("PHYS_BASELINE_DIR",
                          DASHBOARD_DIR.parent / "PHYSICAL-BASELINE MODEL"))
EXPORT   = PB_DIR / "outputs" / "export" / "physical_baseline_v2.parquet"
NOTEBOOK = PB_DIR / "outputs" / "deliverable" / "DELIVERABLE_physical_baseline.ipynb"
```

## 3. Page 1 — explain the rank, name the owner

What the number means and **who fixes it**. Three groups, three owners:

| group | columns | owner |
|---|---|---|
| **house** | `phys_group_house_lo_kwh_yr` (+ point, hi) | a **builder** — insulation, emitters, cylinder |
| **heat pump** | `phys_group_heat_pump_lo_kwh_yr` + `phys_unit_recommendation` | an **installer** — replace, plan, or keep |
| **total** | `phys_deficiency_lo_kwh_yr` | the rank |

Say on this page: the excess is measured **against a code-compliant version of the same
house**; ages are **as of the data end, 2024** (`phys_unit_age_reference_year`); the
service-life basis is `phys_unit_service_life_basis`; and the order is **fleet-wide**,
carrying `phys_rank_bias_note`. Embed the notebook here.

**Also render `outputs/p27/reports/p27_walkthrough.md` in this section** (Miguel,
2026-09-17) — one house traced from its floor area to rank 1, with every number tagged
`DATABASE` / `VERIFIED` / `DERIVED` / `GENERATED` so a reader can see which figures are
referenced, which come from HEAPO and which are ours. It is a **fixed worked example**,
not a per-household trace: the intermediates it shows (`H_as_built`, the U-value drawn,
each JAZ) are deliberately **not** in the export, because these pages never re-run the
model. It is long — whether it sits collapsed under page 1 or gets its own tab inside the
section is your layout call. **Render the `.md`; the `.html` is for the printed report.**

## 4. Page 2 — the one list

**A single fleet-wide list**, ordered by `phys_rank_fleet` (1 = act first), showing
`phys_group_house_lo_kwh_yr`, `phys_group_heat_pump_lo_kwh_yr` and
`phys_deficiency_lo_kwh_yr` side by side, plus `phys_unit_recommendation`.

* **All 214 rows present, visible and filterable** — filters on `phys_era`,
  `phys_status`, `phys_unit_recommendation`.
* **`phys_era` is a filter, not the order.** Keep `phys_rank_in_era` available.
* **No heating slope, no fault percentage on either page.**

| `phys_status` | n | show as |
|---|---:|---|
| `HIGH_EXCESS` | 40 | act — worst 25% of the fleet |
| `EXCESS_CONFIRMED` | 118 | confirmed, lower priority |
| `INCONCLUSIVE` | 14 | no finding — neutral |
| `INCOMPLETE_AUDIT` | 42 | never assessed — **mixed cause**: 21 building data, 18 short meter record, 3 both. **Show `phys_no_result_fix`** (24 an auditor can fix, 18 cannot) — neutral |

## 5. Display rules — enforce all of them

1. **No green anywhere.** There is no "normal" state and the model cannot confirm one.
2. **Show the lower bound**, labelled *"at least this much"*.
3. **Never sum** `phys_group_house_*` with `visit_*` kWh, and never add the capacity
   scenario into any total (`phys_scenario_never_sum_into_total`).
4. **Order fleet-wide, with the bias note visible** (`phys_rank_bias_note`).
5. **No fault probability on these pages.** It lives in Aaditya's own section; the two
   models meet only in the final target overview.
6. **Where `phys_heat_pump_point_is_no_claim` is `True` (63 houses), show the band, not
   the zero** — the installation year is unknown, so the point makes no claim.
7. **"Old" is never an action.** Show `phys_unit_recommendation` verbatim; a mid-life
   unit reads `KEEP_IN_LIFE`.
8. **Keep this section separate from the peer-comparison page.** Different model,
   different population, never one combined number.
9. **No model-performance metrics on these pages.**

## 6. Done when

Read these from the file, not from this note — **values move, columns do not.**

| check | expected today |
|---|---|
| rows × columns | 214 × 66 |
| `schema_version` | `physical_baseline_v2` |
| `phys_status` | HIGH_EXCESS 40 · EXCESS_CONFIRMED 118 · INCONCLUSIVE 14 · INCOMPLETE_AUDIT 42 |
| `phys_unit_recommendation` | keep 76 · record year 63 · plan 23 · replace 10 |
| any column containing "fault" | none |
| notebook | renders with its figures |
| green | appears nowhere |

## 7. Do not

* load `models.joblib` or anything under Aaditya's `artifacts/`
* show the visit-axis columns on these two pages (they are in the file for the **end
  section**, flagged `visit_hidden_from_building_pages`)
* rename or drop columns — `v2` is the contract; breaking changes ship as `v3` alongside
* re-run anything in `PHYSICAL-BASELINE MODEL/` from the dashboard
* total a column in a way that counts `INCONCLUSIVE` or `INCOMPLETE_AUDIT` rows as zero

## 8. If the export needs regenerating

From `PHYSICAL-BASELINE MODEL/`, with `../venv_viz/Scripts/python.exe`, **in order**:

```
p22_registry.py      # the sourced constants registry
p24_lifecycle.py     # the heat-pump recommendation
p13_visit_queue.py   # the visit axis (end section)
p11_export.py        # the export; validates itself and refuses to write if a rule fails
p_notebook.py        # the notebook
p27_walkthrough.py   # the worked example; asserts it still reproduces the export
p_pipeline_test.py   # 141 checks, all green
p10_portability.py   # 23 checks, all green
```
