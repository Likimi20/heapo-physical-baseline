# P24 — from "the unit is old" to a life-cycle recommendation

2026-09-11. `p24_lifecycle.py`, transcript `outputs/p24/logs/p24_run.txt`, data
`outputs/p24/data/p24_unit_recommendation.*`. **141/141 tests.**

## Where the +2.1%/yr came from (question 1)

**Tested, not declared.** It is our own regression on the HEAPO meters (`p23_confound.py`,
n=92): log(measured/physics) on unit age gives +2.1% per year [+0.9, +3.4]. It is **not
a model constant** and must not become one (calibration rule). The model uses the
**sourced** vintage: FAWA 1996–2003 over OST 2015–19, ≈ +1.4%/yr. FAWA itself reports
+1.2% per installation year for ground-source. **Both sources sit inside the measured
interval**: the meter confirms the magnitude; the model stays sourced and slightly
conservative.

## The service life — sourced

Hubbuch & Vecsei, ZHAW Institut für Facility Management, *Lebenszykluskosten von
Wärmepumpen* (for SIG Genève). Weibull fit with a Kaplan-Meier check on a Swiss owner
survey; read in the primary PDF.

| | expected life | SD | N | registry (value / lo / hi) |
|---|---:|---:|---:|---|
| ground-source (Tab 4.7) | **26.7 ± 0.8 yr** | 4.7 yr | 223 | 26.7 / 22.0 / 31.4 |
| air-source (Tab 4.8) | **20 ± 2 yr** | 7 yr | 53 (43 from one firm) — authors: less reliable | 20 / 13 / 27 |

The borehole lasts 50 years (SIA 384/6), so replacing a ground-source unit keeps the
probe. **Now imported into notebook b02e42f0 and confirmed there** (q15,
`outputs/p24/data/q15_lifetime.json`, cited 11× as `Bericht_LCC_EWS_2`).

**The same report gives three life figures; the choice moves the list:**

| life basis (ZHAW) | air | ground | replace | plan | keep |
|---|---:|---:|---:|---:|---:|
| **measured failures, Weibull (used)** | **20 (SD 7)** | **26.7 (SD 4.7)** | **12** | **30** | **87** |
| expert opinion (Tab 4.16) | 18 ± 3 | 20 ± 4 | 25 | 15 | 89 |
| the report's own cost baseline | 16 | 23 | 27 | 29 | 73 |

The survey fit is used because it rests on measured failures, and the authors conclude
ground-source life is "höher als allgemein angenommen". **The replace list roughly
doubles under the other two figures, so the dashboard should show the basis.** Notebook,
also: **no source assesses whether replacing a working unit early pays off**, which
supports KEEP_IN_LIFE. Ground-source probes cool slowly over the years (ZHAW Abb. 4.8), a
small wear-like effect that is not modelled.

**The notebook itself changed during this session.** The three web-research runs imported
all 30 candidates, duplicated, including blogs, Wikipedia and errored items:
**105 sources** against 42 before. P21 and P22 answers predate the flood (35 and 39
sources asked). **`p21_notebook_research.allowed_sources()` now asks a vetted
whitelist only** (pre-session sources + argued imports + ZHAW; one copy per URL; ready
only; AI reports never). q15 cited only vetted sources.

**CLEANED 2026-09-12, authorised by Miguel** (`p24_notebook_cleanup.py --apply`):
**63 sources deleted, 42 remain** — duplicate copies, failed imports and unvetted
research results. The guard (never delete anything created before the research runs)
did not trigger. The three "Research report" files are KEPT as Miguel's own earlier
material and stay excluded from questions. Final list:
`outputs/p24/data/notebook_sources_after_cleanup.json`. The whitelist in
`allowed_sources()` stays in force, so a future flood cannot leak into an answer.

## The rule

**Age is counted to `REF_YEAR = 2024`, the end of the meter data** (last daily date
2024-02-28), not to today. **If the data is updated to a newer period, change
`REF_YEAR` in `p24_lifecycle.py`.** The run prints the real last meter date and flags a
mismatch.

| unit age (to REF_YEAR) | recommendation | meaning |
|---|---|---|
| ≥ expected life | **REPLACE_END_OF_LIFE** | about half such units have failed by now; `term_vintage` is the saving |
| ≥ expected − 1 SD | **PLAN_REPLACEMENT** | entering the failure window; plan it, choose an efficient unit |
| younger | **KEEP_IN_LIFE** | no replacement; the vintage kWh is information only |
| not recorded | **RECORD_INSTALL_YEAR** | fixable — go record it |

**Curve first:** where the unit is old AND P13 v2 confirms slope excess, the order is to
adjust the heating curve first (free), then replace. This uses the model's own
measurement, never the inspector's verdict.

## Result, 214 households

| | air | ground | all | term_vintage, Cat. B |
|---|---:|---:|---:|---:|
| REPLACE_END_OF_LIFE | 8 | 4 | **12** | 4,674 kWh/yr (median 433) |
| PLAN_REPLACEMENT | 27 | 3 | **30** | 5,414 (median 215) |
| KEEP_IN_LIFE | 51 | 36 | **87** | 3,850 (37 houses older than the table, still mid-life) |
| RECORD_INSTALL_YEAR | 44 | 40 (+1 water) | **85** | — |

**Curve first, then replace: 13 households** (e.g. 991118, ground-source, 41 years old
at the data end, confirmed slope excess). A first run to 2026 gave 21 / 31 / 77 / 16;
superseded.

## Does usage or operating age enter?

**No.** FAWA saw no efficiency loss over 9 operating years. `term_vintage` measures
**generation** (how efficient the unit was when built, against a new one). The service
life measures **failure risk**. They answer different questions, and the recommendation
joins them: efficiency says *how much* a new unit would save; life cycle says *whether
now is the time*.

## Did "act first" change? (`p24_actfirst.py`)

Vintage is not a defect of the building or its occupants: the reference house simply gets
a current unit, and a newer model works better. The only question is where that kWh
counts, and whether it may push a house onto the ACT-FIRST list (worst 25% of
Category B within its era; point estimate, declared).

| ranking | act first | vs P22 (no vintage) |
|---|---:|---|
| C — vintage everywhere (live now) | 45 | kept 40, **5 in / 5 out** |
| **A — vintage not ranked for KEEP_IN_LIFE units** | 45 | kept 42, **3 in / 3 out** |
| B — vintage a side column for KEEP units | 45 | ranks exactly like A |

**Under C, two post-2010 houses (121728, 512280) enter only because of vintage.** Their
10-year-old units are to be KEPT and their building excess is 78 kWh/yr. That is the
wrong reason to act first. **Under A the three newcomers all have units due or nearly due**
(7710511 plan, 858577 replace, 876790 plan): the right reason.

Headline totals: P22 268,271 · C = A 288,788 · B 284,938 kWh/yr.

**Recommended: A.** Keep the physical excess complete in the headline; never let a
mid-life unit's vintage decide who acts first. Closing-session item for `p11_export.py`,
together with `unit_recommendation`.
