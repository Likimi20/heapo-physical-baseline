# P28 — the dashboard page, and what only a browser could tell us

Run: `p28_page_test.py` · log `outputs/p28/logs/p28_page_test.txt`
Page: `../Heat_Pump_Failure_Prediction/pages/3_Physical_baseline.py`

---

## The page

One tab, reading `physical_baseline_v2`, three views:

| view | what it does |
|---|---|
| **What the rank means** | the excess split house / heat pump / total with an owner each, the four states, what decides the order, and the model's own notebook |
| **Ranking** | every household in one fleet-wide order on the lower bound, orderable by total / house / heat pump / over code |
| **Walkthrough** | one house traced end to end, every number tagged by where it came from |

The v1-era page was **replaced, not patched**: it read `physical_baseline_v1` and
displayed `visit_fault_probability` and `visit_named_fault` by direct indexing, so on v2
it would have raised `KeyError` rather than degraded. It briefly lived alongside as a
legacy tab; once this test proved the replacement runs, the legacy tab was removed.
**Build the replacement, prove it runs, then delete the original** — the division was not
wasted work, it was what made the removal safe.

## The test, and why it exists

**Streamlit is installed in no environment in this repo.** Rather than ship unexecuted
code, the test stubs the Streamlit API and **runs the page once per view against the real
export**, plus once per sort option. It asserts:

* every view executes — 16 / 7 / 5 markdown blocks, 3 tables on view 1, both remaining;
* **no fault string is ever emitted**, checked on every `markdown` call;
* **no green among the colour tokens**, checked by parsing the hex and comparing channels
  (`POS` `#e66767`, `SERIES1` `#3987e5`, `SERIES2` `#d95926`, `AXIS_INK` `#8a8a85`);
* **`st.metric` is banned** and the stub raises if called — see below;
* all four sort branches render;
* 158 ranked + 56 unranked = **214**, so nothing is unreachable.

It does **not** execute the other three dashboard pages. They belong to other people and
may be mid-rewrite. It does statically parse them with `ast` for green deltas.

## Three faults only the browser found

**Streamlit installed into `.venv`, served on 8501, page opened and driven.** None of
these was a code error, so no amount of executing the page would have caught them.

**1. `st.metric` painted the headline numbers green with up arrows.** "↑ 215,121 kWh/yr
at least" rendered as a green positive-delta badge — 215 MWh of wasted electricity shown
as good news, on the page whose first rule is that nothing may read as green. **The colour
came from the widget, not from any token**, which is precisely why the colour check passed
it. `st.metric` is now banned, the tiles are hand-built HTML, and the test raises if it
reappears.

**2. The table was squished and the headers overlapped.** `.num` sets
`white-space:nowrap`, which `th.num` inherited, so "House, at least (kWh/yr)" could not
wrap and ran over its neighbour. The v1 page had a `th.num { white-space: normal }` rule
for exactly this and it was dropped when the new CSS was written.

**3. "Rank" showed position-in-view, not the model's rank.** Under a filter, numbering
1..n relabels a household sitting 20th in the fleet as "5" beneath a header saying Rank.
Ordered by total it now prints `phys_rank_fleet`; on any other sort the header becomes
`#`, because there is no model rank to show.

## The order was running on a number that was not in the table

Asked whether the explainer covers how households are differentiated in order, it did
not — and the gap was substantive. Option A takes a `KEEP_IN_LIFE` unit's vintage back
out of the ranking value, so `phys_rank_value_lo_kwh_yr` differs from the displayed total
on **31 of the 158** ranked rows: household `120701` shows 1,306 and is ranked on 1,125.
Sorted by total, those rows simply look mis-sorted.

Fixed with a **What decides the order** section — the lower bound rather than the middle,
one order for the whole fleet, healthy heat pumps discounted, and no ties since all 158
positions are distinct — and a **‡** marker on the affected rows.

## Filter defaults, and what they cost

The page opens on what someone can act on. Off by default: `No era recorded`,
`No finding`, `Never computed`, `Record the installation year`.

**`Keep` is deliberately ON, and this was measured rather than assumed.** The unit
recommendation describes the *heat pump*, so switching it off also hid houses with bad
fabric and a healthy unit — which is where the energy is, the house side being ~95% of the
total:

| default | shown | house kWh/yr hidden |
|---|---:|---:|
| `Keep` off | 33 | **150,263 of 197,851**, ranks 2–7 among them |
| `Keep` on (shipped) | 97 | 92,094, all `RECORD_INSTALL_YEAR`, rank 2 among them |

**Nothing is hidden silently**: the page always prints how many households the filters are
holding back and which filter is doing it.

## Two factual errors fixed in the notebook, which the page embeds

It called `INCOMPLETE_AUDIT` "building data missing — fixable" for all 42 when that is
true for 24, and it printed the unit recommendation over all 214 audited households beside
a list covering the 172 scored — the same column with two unlabelled populations.

## What remains untested

Layout at other window sizes, and whether a *different* Streamlit build has every API the
page calls. `requirements.txt` pins `>=1.40`; 1.64 is what was verified. It also omits
`pyarrow`, which the dashboard needs to read parquet at all — flagged, not changed, as
that file belongs to the combined dashboard rather than this workstream.
