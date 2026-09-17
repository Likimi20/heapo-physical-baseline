# P19 — limitations 6 and 7: the registry, and what the sources actually say

2026-09-11. No new script: the registry is `constants_ch.json` at this root, loaded by
`p_physics.py` and tested in `p_pipeline_test.py` section K.

## What changed

* **`constants_ch.json` is both the regional config and the standards registry.** One
  file, so the two cannot drift. `p_physics` loads `C` and `ERA_ORDER` from it and
  exposes `STATUS` per constant. **Reproduction: deficiency and H_as_built identical on
  all 172 households (max |diff| 0.0); tests 115/115; P10 23/23.**
* **`b_ground` value sourced:** TABULA Common Calculation Method, eq. 4, worked example
  floor b_tr = 0.50 (read). **Its band 0.40–1.00 is NOT sourced.** SIA 380/1 simplified
  b, as reproduced in BFH 2013 Tab 2: cellar fully in ground 0.7, partly above 0.8.
* **The test "b_ground is sourced" had `or True` and could never fail.** It is now a
  real check.
* **`dhw_known` role** (adapter), counted by `completeness_tier`. **1** household ticks
  no DHW source. An earlier count of 27 used only two of four DHW columns. The other 26
  are 23 separate heat-pump water heaters (correctly heat-pump DHW) and 3 solar-only,
  whose DHW electricity is overstated. Declared, not changed.

## Status of all 23 constants

| status | n | constants |
|---|---:|---|
| VERIFIED (read here) | 4 | 3 appliance constants, `b_ground` value |
| SECOND_HAND (named, not read) | 7 | `u_reference`, `storey_height`, `n_air`, `t_set`, `t_design`, `jaz_dhw_hp`, `dhw_kwh_person_day` |
| **CITATION_MISMATCH** | **9** | **all five as-built U-values, all four heating JAZ** |
| DERIVED | 2 | `perimeter_factor`, `v_net_per_m2` |
| PHYSICAL | 1 | `rho_c` |

**The nine mismatches are exactly the terms that carry the deficiency.**

## What the documents say

**As-built U-values** — cited "TABULA/EPISCOPE CH 2013, Tab 4 Sec 3.2". **Switzerland is
not a TABULA/EPISCOPE country.** The episcope.eu country list (23 countries) was checked
2026-09-11, and no CH typology was found. TABULA's own method document (read) does confirm
one thing: element U-values exclude thermal bridges (eq. 4).

**ASHP JAZ by emitter** — cited "OST WPZ Buchs 2020, Tabelle 1, N=25". The report (read)
is *Feldmessungen von Wärmepumpen-Anlagen Heizsaison 2019/20*. Its **Tabelle 1 is
"Kurzbeschreibung der Objekte"**, a list of the systems. It covers **23** systems (12
air, 11 ground), all new, mostly single-family houses. It reports **fleet averages only**:

> Wärmenutzungsgrad (WNG) … Luft/Wasser … 3.3 (von 3.0 bis 4.1), Sole/Wasser …
> durchschnittlich 4.2 (von 3.1 bis 5.1) — 2019/20
> Luft/Wasser 3.0 (2.2 bis 3.9); Sole/Wasser 4.5 (3.1 bis 5.2) — 2020/21

There is **no split by emitter or flow temperature.**

**GSHP floor JAZ** — cited "FAWA 2004 S. 331". FAWA (read) runs to **99 pages**. It
covers 221 installations from 1996–2003:

> Die Sole/Wasser-Anlagen liegen mit einer mittleren JAZ von 3.5 um 32% über dem Wert von
> Luft/Wasser-Anlagen

It also gives one usable relation: renovation installations run **+5 K flow, −9% JAZ**.

## What survives the citations

* **Magnitudes are consistent with the documents that were read.** OST air/water WNG
  3.0–3.3 against our ASHP 2.8–3.5; ground/water 4.2–4.5 against our 4.25. Those are
  new-system figures. FAWA's 1996–2003 systems sit lower (ground 3.5, air ~2.65), so
  **installation vintage matters** and is not modelled.
* **The emitter split (floor → radiators −20%) is unsourced.** FAWA's ~1.8%/K implies
  −27 to −36% for radiators 15–20 K hotter, so ours may be *mild*.
* **U-values:** no documentary check is possible. P9 (rank, ρ 0.54 per m²) and P17 (level
  0.946) say the magnitudes are not badly wrong. **That is validation against the meter,
  not a source, and under the calibration rule it can never become one.**

## Limitation 6 — portability

* **Done:** constants live in a region file. A new region is a new file; the interface
  already travels (P10).
* **Not done, deliberately:** a DE config. Building a second region before the first is
  sourced would repeat the citation problem. `HDD_SAMPLING` stays in `p_physics`: it is a
  property of the HEAPO weather record, not of Switzerland, and P18 may retire it.
* **Defaulting:** `dhw_known` is wired into the tier. Unknown renovation or basement is
  not, because HEAPO has no missing renovation flags. Basement NaN (141) means "no
  basement area recorded", and 0 is never recorded. That is an adapter convention,
  declared here.

## CORRECTION, same day — see P20

**The ASHP JAZ finding above is wrong.** It checked the OST *Jahresbericht*. The spec's
"OST 2020 Tabelle 1" is the article *Wie gut sind aktuelle Wärmepumpen im Feld?*
(Heizungsplaner + Installateur 11/12-2020), found through the verified notebook. Its
Tabelle 1 gives JAZ by application, and our 2.8 / 3.1 / 3.5 are its heating + DHW column.
The ASHP JAZ are now VERIFIED. That same table overturns the old rejection of GSHP +
radiators = 4.4. Registry now: 7 VERIFIED / 7 CITATION_MISMATCH / 6 SECOND_HAND /
2 DERIVED / 1 PHYSICAL. The U-value finding stands, and got stronger: in the notebook
they exist only in an AI-generated report.

## Verdict

**Limitation 6: SOLVED for the interface and the file structure.** Constants still do not
travel. **Limitation 7: NOT SOLVED, and worse than recorded.** "Second-hand" was
optimistic: the headline terms cite documents that do not contain them. Every artefact
built on them must carry that, not merely "pending page citation".
