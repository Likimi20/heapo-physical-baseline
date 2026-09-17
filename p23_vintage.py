"""P23 - quick try: heat-pump efficiency by installation year (vintage).

The JAZ table (OST P+I 2020 / RISE 2023) measures units installed ~2015-2019. FAWA 2004
measured the 1996-2003 fleet: air 2.7, ground 3.5, against the table's totals of air 3.4
and ground 4.6. So a 1999 unit delivers ~0.79 (air) / ~0.76 (ground) of a 2017 unit.
FAWA found no ageing loss over 9 operating years, so this is TECHNOLOGY VINTAGE, not wear.
`p_physics.vintage_factor` interpolates linearly between 1999 and 2017 and stays flat
outside - never extrapolated. The reference keeps a current unit, so an old unit becomes
its own deficiency term, `term_vintage` (intervention: replace the unit).
HEAPO records the year for 129/214; unknown = no claim on the point, band widened.

Checks, VALIDATION ONLY (nothing tuned):
  1  Category B: what the term adds, by installation-year group
  2  the meter: P13 v2's measured slope vs physics, by group, vintage OFF vs ON. If
     vintage is real, the old-unit group should move toward 1.0.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import p_physics as ph
from p_adapter_heapo import load_households, modellable, daily_observations, station_normals

OUT = HERE / "outputs" / "p23"
for d in (OUT / "data", OUT / "logs", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)


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


def group(y):
    return "unknown" if y != y else ("<2008" if y < 2008 else ("2008-2014" if y < 2015 else ">=2015"))


GROUPS = ["<2008", "2008-2014", ">=2015", "unknown"]
sys.stdout = Tee(OUT / "logs" / "p23_run.txt")

head("1. CATEGORY B - the vintage term, 172 households, normal-year HDD")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)]
obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
NRM = station_normals(ROOT / "outputs/weather_daily.parquet",
                      ROOT / "outputs/household_weather.parquet")
A = M.merge(obs[(obs.n_days >= 180) & (obs.n_warm >= 60) & (obs.n_cold >= 60)],
            on="Household_ID").merge(NRM, on="Household_ID", how="left")
A["grp"] = A.hp_install_year.map(group)
print("  installation year recorded: %d / %d" % (A.hp_install_year.notna().sum(), len(A)))
print(A.groupby(["grp", "hp_type"]).size().unstack(fill_value=0).reindex(GROUPS).to_string())
rec_on = A.to_dict("records")
rec_off = [{k: v for k, v in r.items() if k != "hp_install_year"} for r in rec_on]
on = [ph.evaluate(r) for r in rec_on]
off = [ph.evaluate(r) for r in rec_off]
A["def_off"] = [e["deficiency"] for e in off]
A["def_on"] = [e["deficiency"] for e in on]
A["term_vintage"] = [e["term_vintage"] for e in on]
A["vf"] = [e["vintage_factor"] for e in on]
print("\n  fleet deficiency: vintage OFF %.0f  ON %.0f  (+%.1f%%)   term_vintage %.0f"
      % (A.def_off.sum(), A.def_on.sum(), 100 * (A.def_on.sum() / A.def_off.sum() - 1),
         A.term_vintage.sum()))
print(A.groupby("grp").agg(n=("vf", "size"), factor=("vf", "median"),
                           term=("term_vintage", "median"),
                           deficiency=("def_on", "median")).reindex(GROUPS).round(2).to_string())

head("2. VALIDATION - P13 v2 measured slope (post-visit, free step) vs physics")

Q = pd.read_parquet(HERE / "outputs/p13/data/p13_visit_queue.parquet")
Q = Q.drop(columns=[c for c in ["hp_install_year"] if c in Q]).merge(
    H[["Household_ID", "hp_install_year"]], on="Household_ID", how="left")
Q["grp"] = Q.hp_install_year.map(group)
rq = Q.to_dict("records")
Q["bp_on"] = [(lambda e: e["H_as_built"] * 24 / 1000 / e["jaz_as_built"])(ph.evaluate(r)) for r in rq]
Q["bp_off"] = [(lambda e: e["H_as_built"] * 24 / 1000 / e["jaz_as_built"])(
    ph.evaluate({k: v for k, v in r.items() if k != "hp_install_year"})) for r in rq]
print("  median measured / physics slope, by installation-year group:")
print("  %-10s %4s %9s %9s" % ("group", "n", "OFF", "ON"))
for g in GROUPS:
    s = Q[Q.grp == g]
    print("  %-10s %4d %9.2f %9.2f" % (g, len(s), (s.beta_meas / s.bp_off).median(),
                                       (s.beta_meas / s.bp_on).median()))
for col in ["bp_off", "bp_on"]:
    r = pd.concat([Q[col] / Q.area_m2, Q.beta_meas / Q.area_m2], axis=1).corr(
        method="spearman").iloc[0, 1]
    print("  Spearman per m2, %s: %+.3f" % (col, r))
print("\n  current P13 v2 status by group (vintage not yet applied there):")
print(pd.crosstab(Q.grp, Q.visit_status).reindex(GROUPS).to_string())

A.to_parquet(OUT / "data" / "p23_category_b.parquet", index=False)
Q[["Household_ID", "grp", "hp_install_year", "beta_meas", "bp_off", "bp_on",
   "visit_status"]].to_parquet(OUT / "data" / "p23_meter_check.parquet", index=False)
print("\n  written: p23_category_b.parquet, p23_meter_check.parquet")
