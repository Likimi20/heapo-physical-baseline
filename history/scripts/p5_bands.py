"""P5 - how wide is the uncertainty band, actually?

The CLAUDE.md has promised a per-household band since the design was settled and
nothing has ever measured one. This run answers the question that decides whether
the whole approach can categorise anything:

  IF THE BAND IS WIDER THAN THE DEFICIENCY, THE MODEL DECIDES NOTHING.

Method: Monte Carlo over the PUBLISHED SPREAD of every constant. Not invented
error bars - the bands in p_physics.C are the ranges the standards themselves
give. Each draw samples every constant, recomputes the household end to end, and
the spread of the draws IS the band.

Renovation is handled by WIDENING, not by an unsourced modifier: no source gives
renovated-state U, so a renovated house's U band stretches toward the next-newer
era. That is what the completeness tier records.

Correlated by construction: the same constant draw is shared between E_as_built
and E_reference within a draw, so errors common to both CANCEL in the difference -
exactly the property the two-baseline design was chosen for. This run measures
how much of it actually cancels.

Uses p_physics.py + p_adapter_heapo.py. numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph
from p_adapter_heapo import (load_households, modellable, drop_reasons,
                             daily_observations)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p5"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

NDRAW = 400
RNG = np.random.default_rng(20260910)


class Tee:
    def __init__(self, p):
        self.f = open(p, "w", encoding="utf-8")

    def write(self, s):
        sys.__stdout__.write(s)
        self.f.write(s)

    def flush(self):
        sys.__stdout__.flush()
        self.f.flush()


def head(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


sys.stdout = Tee(LOGS / "p5_run.txt")

head("1. POPULATION, AND EVERY DROPPED HOUSEHOLD DECLARED")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
ok = modellable(H)
H["drop_reason"] = drop_reasons(H)
print("  households in protocols.csv : %d" % len(H))
print("  modellable                  : %d" % int(ok.sum()))
print("  UNJUDGEABLE                 : %d" % int((~ok).sum()))
for r, n in H.loc[~ok, "drop_reason"].value_counts().items():
    print("      %-40s %d" % (r, n))

obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
D = H[ok].merge(obs, on="Household_ID", how="left")
D = D[D.hdd_per_day.notna()].copy()
print("  with usable consumption days: %d" % len(D))

D["tier"] = [ph.completeness_tier(r) for r in D.to_dict("records")]
print("\n  completeness tiers:")
for t, n in D.tier.value_counts().sort_index().items():
    print("      %-4s %3d  (%.0f%%)" % (t, n, 100 * n / len(D)))
print("      T1 published JAZ, no renovation ambiguity, full geometry")
print("      T2 one widening source     T3 two or more")

head("2. MONTE CARLO OVER THE PUBLISHED SPREAD")

recs = D.to_dict("records")
print("  %d households x %d draws" % (len(recs), NDRAW))
keys = ["E_as_built", "E_reference", "deficiency", "term_envelope",
        "term_emitter", "term_dhw", "H_as_built", "design_kw", "huellzahl"]
acc = {k: np.zeros((len(recs), NDRAW)) for k in keys}
for j in range(NDRAW):
    for i, r in enumerate(recs):
        out = ph.evaluate(r, RNG)
        for k in keys:
            acc[k][i, j] = out[k]

point = {k: np.array([ph.evaluate(r)[k] for r in recs]) for k in keys}
res = pd.DataFrame({"Household_ID": D.Household_ID.values, "era": D.era.values,
                    "era_raw": D.era_raw.values, "tier": D.tier.values,
                    "area_m2": D.area_m2.values})
for k in keys:
    res[k] = point[k]
    res[k + "_lo"] = np.percentile(acc[k], 2.5, axis=1)
    res[k + "_hi"] = np.percentile(acc[k], 97.5, axis=1)

res["band_abs"] = res.deficiency_hi - res.deficiency_lo
res["band_rel"] = res.band_abs / res.deficiency.abs()
res["decisive"] = res.deficiency_lo > 0     # whole band above zero

head("3. THE QUESTION - IS THE BAND NARROWER THAN THE DEFICIENCY?")

print("  deficiency, kWh/yr : median %6.0f   IQR %6.0f - %6.0f"
      % (res.deficiency.median(), res.deficiency.quantile(.25),
         res.deficiency.quantile(.75)))
print("  95%% band width      : median %6.0f   IQR %6.0f - %6.0f"
      % (res.band_abs.median(), res.band_abs.quantile(.25),
         res.band_abs.quantile(.75)))
print("  band / |deficiency| : median %6.2f   IQR %6.2f - %6.2f"
      % (res.band_rel.median(), res.band_rel.quantile(.25),
         res.band_rel.quantile(.75)))
print()
print("  DECISIVE (entire 95%% band above zero) : %d of %d  (%.1f%%)"
      % (int(res.decisive.sum()), len(res), 100 * res.decisive.mean()))
print("  band straddles zero -> UNJUDGEABLE     : %d  (%.1f%%)"
      % (int((~res.decisive).sum()), 100 * (~res.decisive).mean()))

print("\n  by completeness tier:")
for t in ["T1", "T2", "T3"]:
    s = res[res.tier == t]
    if len(s):
        print("    %-4s n=%-4d median band %6.0f kWh   band/|def| %5.2f   decisive %5.1f%%"
              % (t, len(s), s.band_abs.median(), s.band_rel.median(),
                 100 * s.decisive.mean()))
print("  A tighter band on better-documented houses is the whole point of the")
print("  tier system. If T1 is not tighter than T3, the tiers do nothing.")

print("\n  by era:")
for e in ph.ERA_ORDER:
    s = res[res.era == e]
    if len(s) >= 5:
        print("    %-10s n=%-4d deficiency %7.0f   band %6.0f   decisive %5.1f%%"
              % (e, len(s), s.deficiency.median(), s.band_abs.median(),
                 100 * s.decisive.mean()))

head("4. HOW MUCH ERROR ACTUALLY CANCELS IN THE DIFFERENCE?")

for k, name in [("E_as_built", "E_as_built (a LEVEL)"),
                ("E_reference", "E_reference (a LEVEL)"),
                ("deficiency", "deficiency (a DIFFERENCE)")]:
    rel = (res[k + "_hi"] - res[k + "_lo"]) / res[k].abs()
    print("  %-26s median relative 95%% width %.2f" % (name, rel.median()))
print()
print("  The two-baseline design was chosen because errors common to both levels")
print("  cancel in their difference. If the difference's relative width is NOT")
print("  smaller than the levels', that argument fails and must be withdrawn.")

head("5. WHAT A RELATIVE GATE WOULD SELECT")

res["def_pct_of_ref"] = 100 * res.deficiency / res.E_reference
for g in [15, 25, 50, 100]:
    print("    gate > +%3d%% of E_reference : selects %5.1f%% of the fleet"
          % (g, 100 * (res.def_pct_of_ref > g).mean()))
print("  A category holding most of the fleet ranks nothing - the S-series'")
print("  central lesson, and the reason a relative gate is NOT the B/D line.")

head("6. RANKED WITHIN ERA - decisive households only")

dec = res[res.decisive].copy()
dec["rank_in_era"] = dec.groupby("era").deficiency.rank(ascending=False,
                                                        method="min")
print("  decisive households by era, and their top 3:")
for e in ph.ERA_ORDER:
    s = dec[dec.era == e]
    if len(s):
        top = s.nsmallest(3, "rank_in_era")
        ids = ", ".join("%d (%.0f +/-%.0f)" % (i, d, b / 2)
                        for i, d, b in zip(top.Household_ID, top.deficiency,
                                           top.band_abs))
        print("    %-10s n=%-4d  %s" % (e, len(s), ids))

res.to_parquet(DATA / "p5_bands.parquet", index=False)
res.to_csv(DATA / "p5_bands.csv", index=False, sep=";")
H.loc[~ok, ["Household_ID", "drop_reason"]].to_csv(
    DATA / "p5_unjudgeable.csv", index=False, sep=";")
print("\n  written: p5_bands.parquet, p5_bands.csv, p5_unjudgeable.csv")
print("\nP5 complete.")
