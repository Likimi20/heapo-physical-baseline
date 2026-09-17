# Physical baseline model — HEAPO heat pumps

How much more electricity does a house use than **a code-compliant version of itself**?

Not "does this house use a lot" — a big house uses a lot and that says nothing. The model
builds each house twice, once as it is and once as the Swiss building code would have it,
on the same plot, in the same weather, with the same number of people. The answer is the
gap between the two.

Part of a research fellowship at Technology Campus Mainburg (THD) on the
[HEAPO](https://arxiv.org/abs/2503.16993) Swiss smart-meter dataset.

---

## The one thing that defines this model

**Nothing is calibrated to consumption.** No constant was chosen, tuned or selected by
looking at how much electricity these houses actually used. Every value comes from a
published source or is derived from published inputs, and the registry records which.
Where the physics and the meter disagree, **the disagreement is reported, never tuned
away** — a constant that happened to reproduce the data would be treated as a warning
sign, not a success.

The meter is read for **weather only**.

## Start here

| file | what it is |
|---|---|
| `outputs/p27/reports/p27_walkthrough.md` | **Read this first.** One house traced end to end, every number tagged by where it came from. The `.html` beside it prints to PDF |
| `outputs/export/SCHEMA_v2.md` | the export contract — every column, its unit, and how it must be displayed |
| `outputs/export/physical_baseline_v2.parquet` | the result: 214 audited households × 66 columns |
| `CLAUDE.md` | the full decision record, P0–P28, including every rejected option and why |
| `constants_ch.json` | the constants registry: value, band, unit, source, section and a status per constant |

## What it produces

Four states, and **none of them says "normal"** — confirming a house is fine would need
its whole uncertainty band at or below code, and not one household achieves that. The
model confirms an excess or says nothing.

| state | n | meaning |
|---|---:|---|
| `HIGH_EXCESS` | 40 | confirmed excess, worst 25% of the fleet — act |
| `EXCESS_CONFIRMED` | 118 | confirmed excess, below the action cut |
| `INCONCLUSIVE` | 14 | computed, but the band crosses zero — no claim |
| `INCOMPLETE_AUDIT` | 42 | never computed; mixed cause, per household |

The excess splits three ways, because **different people fix different parts**: the
**house** (envelope, emitters, hot-water cylinder → a builder), the **heat pump** (the
unit's technology generation → an installer), and the **total**, which is the two summed
and is what the list is ordered on.

Every figure travels with a band sampled from the **published spread of the constants**,
and the list is ordered on the **lower** bound — "at least this much" — so a household's
position survives the least favourable reading of the sources.

## Running it

Needs numpy + pandas only (matplotlib for the figures). In order:

```
p22_registry.py      # the sourced constants registry
p24_lifecycle.py     # the heat-pump keep/replace recommendation
p13_visit_queue.py   # the visit axis
p11_export.py        # the export; validates itself and refuses to write if a rule fails
p_notebook.py        # the deliverable notebook
p27_walkthrough.py   # the worked example
```

Then these must stay green:

```
p_pipeline_test.py   # 141 checks
p10_portability.py   # 23 checks — asserts the physics layer knows no HEAPO column names
p28_page_test.py     # executes the dashboard pages without installing Streamlit
```

`heapo_data/` is **not** in this repository — it is read from the parent directory and is
never modified.

## Portability

`p_physics.py` takes variable **roles**, never dataset column names; each dataset supplies
its own adapter (`p_adapter_*.py`). `p10_portability.py` asserts the separation by failing
if a HEAPO column name appears in the physics layer. **The method ports; the constants do
not** — another country means a new registry file, not new code.

## Known limits — stated, not hidden

* **The order leans old.** Per m² the physics under-predicts newer construction by
  24–53%, so a fleet-wide list tilts toward older houses. Era is therefore a filter, and
  the within-era rank is kept as a column.
* **Chart-read inputs.** The era U-values were read off bar charts in the source report.
  They pass the report's own text check but are approximate, and they are marked `DERIVED`
  rather than `VERIFIED`.
* **One envelope split**, from a single Swiss reference building, with a German typology
  as the band.
* **Air-source service life rests on 53 units**, 43 of them from one firm — the authors
  themselves call it less reliable. Ground-source rests on 223.
* **63 households have no recorded installation year**, so their heat-pump figure is a
  deliberate no-claim: the point estimate is 0 while the band sits above it. Show the
  band, never the zero.
* **Neither energy level is a bill.** Appliances are excluded from both baselines, so
  only the *difference* is meaningful.

## Scope

This model answers "above a code-compliant version of itself". It does **not** detect
heat-pump misconfiguration — that is a separate model with its own section — and it is
never merged with the peer-comparison model, which asks the different question "above
comparable houses". Two methods, two answers, never one combined number.
