"""P24 - turn term_vintage into a RECOMMENDATION tied to the unit's life cycle.

Miguel 2026-09-11: "instead of saying it is old, state a recommendation - replace the unit,
but only if it is out of its life cycle or close to it."

A unit that is older than the efficiency table but still mid-life is NOT a replacement
case: scrapping a working machine early is rarely justified, and this model does not price
replacement. term_vintage stays as information - the kWh a new unit would save - and the
ACTION comes from age versus a SOURCED service life (registry: hp_service_life_air /
hp_service_life_ground; ZHAW Hubbuch & Vecsei, Weibull fit of Swiss survey data:
value = expected life, lo = expected life - 1 SD, hi = + 1 SD).

  age >= expected life     -> REPLACE_END_OF_LIFE      about half such units have failed
                                                       by now; term_vintage is the saving
  expected - 1 SD <= age   -> PLAN_REPLACEMENT         entering the failure window: plan it
  younger                  -> KEEP_IN_LIFE             no replacement recommended
  year not recorded        -> RECORD_INSTALL_YEAR      fixable - go record it

CURVE FIRST (P23b): an old unit loses most at a high flow temperature, so where the visit
axis ALSO confirms heating the building does not justify (P13 v2 SLOPE_EXCESS), the order
is: adjust the heating curve first (free), then replace. Uses the model's own measurement,
never the inspector's verdict.

Age is counted to REF_YEAR, the analysis year. Nothing here changes p_physics.

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

# Unit age is counted to the END OF THE METER DATA (HEAPO: 2024-03-21), not to today.
# IF THE DATA IS UPDATED TO A NEWER PERIOD, CHANGE THIS NUMBER. The run prints the real
# last meter date so a mismatch is visible.
REF_YEAR = 2024
OUT = HERE / "outputs" / "p24"
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


def recommend(hp_type, year):
    if year != year:
        return "RECORD_INSTALL_YEAR"
    key = "hp_service_life_air" if hp_type == "air-source" else "hp_service_life_ground"
    life, lo = ph.value(key), ph.band(key)[0]
    age = REF_YEAR - year
    if age >= life:
        return "REPLACE_END_OF_LIFE"
    if age >= lo:
        return "PLAN_REPLACEMENT"
    return "KEEP_IN_LIFE"


sys.stdout = Tee(OUT / "logs" / "p24_run.txt")

last = pd.read_parquet(ROOT / "outputs/daily_states.parquet", columns=["date"]).date.max()
print("  age counted to REF_YEAR = %d   (last meter date in the data: %s)%s"
      % (REF_YEAR, last, "" if str(last)[:4] == str(REF_YEAR) else "  <-- MISMATCH, update REF_YEAR"))

head("1. THE SOURCED SERVICE LIFE")
for k in ["hp_service_life_air", "hp_service_life_ground"]:
    v, lo, hi = ph.C[k][:3]
    print("  %-24s %4.0f yr  [%.0f-%.0f]  %s | %s" % (k, v, lo, hi, ph.C[k][4], ph.C[k][5]))

head("2. RECOMMENDATION PER HOUSEHOLD (all 214; Category B terms where assessable)")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)]
obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
A = M.merge(obs[(obs.n_days >= 180) & (obs.n_warm >= 60) & (obs.n_cold >= 60)],
            on="Household_ID").merge(
    station_normals(ROOT / "outputs/weather_daily.parquet",
                    ROOT / "outputs/household_weather.parquet"),
    on="Household_ID", how="left")
ev = {r["Household_ID"]: ph.evaluate(r) for r in A.to_dict("records")}
R = H[["Household_ID", "hp_type", "hp_install_year", "era"]].copy()
R["unit_age_years"] = REF_YEAR - R.hp_install_year
R["unit_recommendation"] = [recommend(t, y) for t, y in zip(R.hp_type, R.hp_install_year)]
R["term_vintage_kwh"] = R.Household_ID.map(lambda i: ev[i]["term_vintage"] if i in ev else np.nan)
R["vintage_factor"] = R.Household_ID.map(lambda i: ev[i]["vintage_factor"] if i in ev else np.nan)
Q = pd.read_parquet(HERE / "outputs/p13/data/p13_visit_queue.parquet")[
    ["Household_ID", "visit_status"]]
R = R.merge(Q, on="Household_ID", how="left")
R["curve_first"] = (R.unit_recommendation.isin(["REPLACE_END_OF_LIFE", "PLAN_REPLACEMENT"])
                    & (R.visit_status == "SLOPE_EXCESS"))

print(pd.crosstab(R.unit_recommendation, R.hp_type, margins=True).to_string())
print("\n  term_vintage (kWh/yr, Category B households) by recommendation:")
print(R.groupby("unit_recommendation").term_vintage_kwh.agg(["count", "median", "sum"])
      .round(0).to_string())
print("\n  curve first, then replace (old unit AND confirmed slope excess): %d"
      % int(R.curve_first.sum()))
print(R[R.curve_first][["Household_ID", "hp_type", "unit_age_years", "unit_recommendation",
                        "term_vintage_kwh"]].to_string(index=False))
keep = R[R.unit_recommendation == "KEEP_IN_LIFE"]
print("\n  KEEP_IN_LIFE carrying a non-zero vintage term (older than the table, still mid-life): %d"
      % int((keep.term_vintage_kwh > 0).sum()))

R.to_parquet(OUT / "data" / "p24_unit_recommendation.parquet", index=False)
R.to_csv(OUT / "data" / "p24_unit_recommendation.csv", sep=";", index=False)
print("\n  written: p24_unit_recommendation")
