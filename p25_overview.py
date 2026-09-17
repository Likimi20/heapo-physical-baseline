"""P25 - the target overview in THREE GROUPS, as Miguel proposed 2026-09-12.

Instead of one ranked list per construction era, split what the model says into the three
things a reader can act on, each with its own owner:

  1 HOUSE        envelope + emitters + hot-water cylinder - the fabric, driven by era and
                 what was renovated. Owner: a builder.
  2 HEAT PUMP    term_vintage plus the life-cycle recommendation. Owner: an installer.
                 Replace or keep - never "it is old".
  3 TOTAL        the building excess over a code-compliant version of the same house,
                 which is exactly groups 1 + 2 (asserted).

Aaditya's fault model is NOT here and not in P13 any more: the two models meet only in a
final target overview, each in its own column.

Bands: Monte Carlo over the published constant spreads, per group, so each group can be
ranked on its own lower bound ("at least this much"), the P5 rule.

THE ERA QUESTION, measured rather than assumed: ranking fleet-wide instead of within era
is only safe if it does not collapse onto the oldest houses. This run reports the era
composition of both, per group, so the choice can be made on evidence. P9/P21 stand:
per m2 the physics still under-predicts newer eras, so a fleet-wide fabric ranking tilts
toward old buildings.

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

OUT = HERE / "outputs" / "p25"
for d in (OUT / "data", OUT / "logs", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)
NDRAW = 200
RNG = np.random.default_rng(20260919)
GROUPS = {"house": "envelope + emitter + DHW", "heat_pump": "vintage",
          "total": "house + heat pump"}


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


def quartile(s, by=None):
    """Worst 25% - within `by` if given, else fleet-wide."""
    if by is None:
        return set(s.nlargest(int(np.ceil(len(s) * 0.25))).index)
    r = s.groupby(by).rank(ascending=False)
    n = s.groupby(by).transform("size")
    return set(s[r <= np.ceil(n * 0.25)].index)


sys.stdout = Tee(OUT / "logs" / "p25_run.txt")

head("1. THE THREE GROUPS")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)]
obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
A = M.merge(obs[(obs.n_days >= 180) & (obs.n_warm >= 60) & (obs.n_cold >= 60)],
            on="Household_ID").merge(
    station_normals(ROOT / "outputs/weather_daily.parquet",
                    ROOT / "outputs/household_weather.parquet"),
    on="Household_ID", how="left").set_index("Household_ID")
recs = A.reset_index().to_dict("records")
ev = [ph.evaluate(r) for r in recs]
A["house"] = [e["term_envelope"] + e["term_emitter"] + e["term_dhw"] for e in ev]
A["heat_pump"] = [e["term_vintage"] for e in ev]
A["total"] = [e["deficiency"] for e in ev]
gap = (A.house + A.heat_pump - A.total).abs().max()
print("  households: %d   house + heat_pump == total to %.2e kWh/yr" % (len(A), gap))

draws = {g: np.empty((len(A), NDRAW)) for g in GROUPS}
for j in range(NDRAW):
    for i, r in enumerate(recs):
        e = ph.evaluate(r, RNG)
        draws["house"][i, j] = e["term_envelope"] + e["term_emitter"] + e["term_dhw"]
        draws["heat_pump"][i, j] = e["term_vintage"]
        draws["total"][i, j] = e["deficiency"]
for g in GROUPS:
    A[g + "_lo"] = np.percentile(draws[g], 2.5, axis=1)
    A[g + "_hi"] = np.percentile(draws[g], 97.5, axis=1)

R = pd.read_parquet(HERE / "outputs/p24/data/p24_unit_recommendation.parquet").set_index(
    "Household_ID")
A["unit_recommendation"] = R.unit_recommendation.reindex(A.index)
A["unit_age_years"] = R.unit_age_years.reindex(A.index)
V = pd.read_parquet(HERE / "outputs/p13/data/p13_visit_queue.parquet").set_index(
    "Household_ID")
A["visit_status"] = V.visit_status.reindex(A.index)

print("\n  %-10s %-24s %10s %8s %9s %s"
      % ("group", "what", "fleet", "median", "median lo", "decisive (whole band > 0)"))
for g, what in GROUPS.items():
    dec = int((A[g + "_lo"] > 0).sum())
    print("  %-10s %-24s %10.0f %8.0f %9.0f %d of %d"
          % (g, what, A[g].sum(), A[g].median(), A[g + "_lo"].median(), dec, len(A)))

head("2. GROUP 1 - HOUSE (fabric): era and renovations")

print(A.groupby("era").agg(n=("house", "size"), median=("house", "median"),
                           median_lo=("house_lo", "median"),
                           renovated=("renovation_count", lambda s: float((s > 0).mean())))
      .reindex(ph.ERA_ORDER).round(2).to_string())

head("3. GROUP 2 - HEAT PUMP: replace or keep")

print(A.groupby("unit_recommendation").agg(n=("heat_pump", "size"),
                                           median_age=("unit_age_years", "median"),
                                           median=("heat_pump", "median"),
                                           fleet=("heat_pump", "sum")).round(0).to_string())
print("\n  the heat-pump group needs NO era ranking: a unit's vintage is equipment, and")
print("  its efficiency gap does not depend on the building's age.")
print("  median heat_pump kWh by era: %s"
      % A.groupby("era").heat_pump.median().reindex(ph.ERA_ORDER).round(0).to_dict())

head("4. THE ERA QUESTION - fleet-wide versus within-era worst quartile")

for g in GROUPS:
    fw, we = quartile(A[g + "_lo"]), quartile(A[g + "_lo"], A.era)
    comp = lambda s: A.loc[sorted(s)].era.value_counts().reindex(ph.ERA_ORDER).fillna(0).astype(int).to_dict()
    print("\n  %s: fleet-wide %d, within-era %d, shared %d" % (g, len(fw), len(we), len(fw & we)))
    print("    fleet-wide by era: %s" % comp(fw))
    print("    within-era      : %s" % comp(we))

head("5. WHAT A THREE-GROUP OVERVIEW WOULD SAY PER HOUSE")

top = A.sort_values("total_lo", ascending=False).head(12)
print("  %-9s %-10s %9s %9s %-20s %s"
      % ("house", "era", "house lo", "pump lo", "unit", "visit axis"))
for i, r in top.iterrows():
    print("  %-9d %-10s %9.0f %9.0f %-20s %s"
          % (i, r.era, r.house_lo, r.heat_pump_lo, str(r.unit_recommendation)[:20],
             str(r.visit_status)))

A.reset_index().to_parquet(OUT / "data" / "p25_overview.parquet", index=False)
A.reset_index().to_csv(OUT / "data" / "p25_overview.csv", sep=";", index=False)
print("\n  written: p25_overview")
