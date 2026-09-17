"""P24b - did "act first" (HIGH_EXCESS, worst 25% of Category B within era) change with
vintage, and what do options A and B do?

Vintage is not a defect in the building or its occupants: a newer unit simply works
better, and the reference house gets one. So the question is only where that kWh is
counted and whether it may push a house into the ACT-FIRST list.

  P22    no vintage (before P23)
  C      vintage in the headline and in the ranking (current live model)
  A      vintage in the headline, EXCLUDED from the ranking for KEEP_IN_LIFE units
         (they are not replaced, so their vintage kWh is not actionable now)
  B      vintage shown only as a side column for KEEP_IN_LIFE units (headline without it)
         - ranks exactly like A; only the headline total differs

Ranking on the point estimate (the export ranks on the band's lower bound; declared).

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p24"
A_ = pd.read_parquet(HERE / "outputs/p23/data/p23_category_b.parquet")[
    ["Household_ID", "era", "def_off", "def_on", "term_vintage"]]
R = pd.read_parquet(OUT / "data" / "p24_unit_recommendation.parquet")[
    ["Household_ID", "unit_recommendation", "unit_age_years"]]
D = A_.merge(R, on="Household_ID", how="left")
keep = D.unit_recommendation == "KEEP_IN_LIFE"
D["rank_A"] = np.where(keep, D.def_on - D.term_vintage, D.def_on)
D["def_B"] = D.rank_A


def act_first(col):
    r = D.groupby("era")[col].rank(ascending=False)
    n = D.groupby("era")[col].transform("size")
    return set(D.loc[r <= np.ceil(n * 0.25), "Household_ID"])


sys.stdout = open(OUT / "logs" / "p24_actfirst_run.txt", "w", encoding="utf-8")
out = sys.stdout


def say(s=""):
    out.write(s + "\n")
    sys.__stdout__.write(s + "\n")


P22, C, A = act_first("def_off"), act_first("def_on"), act_first("rank_A")
say("ACT FIRST = worst 25%% within era, %d households in Category B" % len(D))
say("  P22 (no vintage) %d   C (vintage everywhere) %d   A/B (not for KEEP units) %d"
    % (len(P22), len(C), len(A)))
say("  C vs P22: kept %d, IN %d, OUT %d" % (len(C & P22), len(C - P22), len(P22 - C)))
say("  A vs P22: kept %d, IN %d, OUT %d" % (len(A & P22), len(A - P22), len(P22 - A)))
for name, s in [("C brings IN", C - P22), ("A brings IN", A - P22)]:
    t = D[D.Household_ID.isin(s)][["Household_ID", "era", "unit_recommendation",
                                    "unit_age_years", "def_off", "term_vintage"]]
    say("\n  %s:\n%s" % (name, t.round(0).to_string(index=False) if len(t) else "    none"))
say("\n  headline total  P22 %.0f   C=A %.0f   B %.0f kWh/yr"
    % (D.def_off.sum(), D.def_on.sum(), D.def_B.sum()))
say("  vintage kWh by recommendation: %s"
    % D.groupby("unit_recommendation").term_vintage.sum().round(0).to_dict())
