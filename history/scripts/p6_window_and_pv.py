"""P6 - Phase 2. Enforce the post-visit window, tag the PV subgroup.

TWO SETTLED DECISIONS FINALLY IMPLEMENTED.

  POST-VISIT WINDOW. Settled by Miguel 2026-09-10 and not applied in P0-P5, which
  all used the full record. The reason is RECENCY AND NON-CIRCULARITY, never
  repair: S10 measured that the visits did NOT move consumption (visited vs
  placebo AUC 0.474, median -0.0034 kWh/DD). Post-visit data is TODAY'S STATE,
  not a repaired state.

  PV SUBGROUP. Retained and reported separately, never excluded. 42 True,
  141 False, 31 NaN on the 214 - and ABSENCE IS NOT "no PV" (parent trap 3), so
  Unknown is its own level.

A day-sufficiency rule is applied to BOTH windows so the comparison is fair:
>=180 usable days, >=60 warm, >=60 cold. Without a summer the floor and the slope
cannot be separated, and visits cluster in Nov-Feb.

Uses p_physics.py + p_adapter_heapo.py. numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph
from p_adapter_heapo import (load_households, modellable, daily_observations)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p6"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

MIN_DAYS, MIN_WARM, MIN_COLD = 180, 60, 60
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


sys.stdout = Tee(LOGS / "p6_run.txt")

head("1. THE TWO WINDOWS")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)].copy()
print("  modellable households : %d of %d" % (len(M), len(H)))

obs_all = daily_observations(ROOT / "outputs/daily_states.parquet",
                             ROOT / "outputs/household_weather.parquet")
obs_post = daily_observations(ROOT / "outputs/daily_states.parquet",
                              ROOT / "outputs/household_weather.parquet",
                              post_visit_only=True, visits=H)


def suff(o):
    return o[(o.n_days >= MIN_DAYS) & (o.n_warm >= MIN_WARM)
             & (o.n_cold >= MIN_COLD)]


print("\n  %-22s %10s %10s" % ("", "all days", "post-visit"))
print("  %-22s %10d %10d" % ("households with any day",
                             len(obs_all), len(obs_post)))
sa, sp = suff(obs_all), suff(obs_post)
print("  %-22s %10d %10d" % ("clear >=180/60/60", len(sa), len(sp)))
A = M.merge(sa, on="Household_ID", how="inner")
P = M.merge(sp, on="Household_ID", how="inner")
print("  %-22s %10d %10d" % ("AND modellable", len(A), len(P)))
print("\n  COST OF THE POST-VISIT RULE: %d -> %d households  (-%.1f%%)"
      % (len(A), len(P), 100 * (1 - len(P) / len(A))))

lost = set(A.Household_ID) - set(P.Household_ID)
lo = obs_post[obs_post.Household_ID.isin(lost)]
print("  of the %d lost: %d have NO post-visit day at all, %d have too few"
      % (len(lost), len(lost) - len(lo), len(lo)))
if len(lo):
    print("    among those with some post-visit data, median n_days %.0f, "
          "n_warm %.0f, n_cold %.0f"
          % (lo.n_days.median(), lo.n_warm.median(), lo.n_cold.median()))
print("  Visits cluster Nov-Feb, so a short post-visit record often holds no")
print("  summer at all. That is what the attrition is.")

head("2. DOES THE WINDOW CHANGE THE ANSWER?")


def run(df, tag):
    recs = df.to_dict("records")
    keys = ["deficiency", "E_as_built", "E_reference"]
    acc = {k: np.zeros((len(recs), NDRAW)) for k in keys}
    for j in range(NDRAW):
        for i, r in enumerate(recs):
            o = ph.evaluate(r, RNG)
            for k in keys:
                acc[k][i, j] = o[k]
    pt = {k: np.array([ph.evaluate(r)[k] for r in recs]) for k in keys}
    out = pd.DataFrame({"Household_ID": df.Household_ID.values,
                        "era": df.era.values, "pv": df.pv.values,
                        "area_m2": df.area_m2.values,
                        "kwh_per_day": df.kwh_per_day.values,
                        "hdd_per_day": df.hdd_per_day.values,
                        "n_days": df.n_days.values})
    out["tier"] = [ph.completeness_tier(r) for r in recs]
    for k in keys:
        out[k] = pt[k]
        out[k + "_lo"] = np.percentile(acc[k], 2.5, axis=1)
        out[k + "_hi"] = np.percentile(acc[k], 97.5, axis=1)
    out["band"] = out.deficiency_hi - out.deficiency_lo
    out["decisive"] = out.deficiency_lo > 0
    out["window"] = tag
    return out


RA, RP = run(A, "all_days"), run(P, "post_visit")
for r, n in [(RA, "all days"), (RP, "post-visit")]:
    print("  %-12s n=%-4d median deficiency %6.0f   median band %6.0f   "
          "decisive %5.1f%%"
          % (n, len(r), r.deficiency.median(), r.band.median(),
             100 * r.decisive.mean()))

J = RA.merge(RP, on="Household_ID", suffixes=("_a", "_p"))
print("\n  on the %d households present in BOTH windows:" % len(J))
print("    hdd_per_day    all %.3f  post %.3f  (weather differs between windows)"
      % (J.hdd_per_day_a.mean(), J.hdd_per_day_p.mean()))
print("    deficiency     median ratio post/all %.3f"
      % (J.deficiency_p / J.deficiency_a).median())
print("    Spearman of the ranking: %.4f"
      % J[["deficiency_a", "deficiency_p"]].corr(method="spearman").iloc[0, 1])
print("  The deficiency is COMPUTED from geometry and constants; the only thing")
print("  the window changes is hdd_per_day. So a high rank correlation is")
print("  EXPECTED and is not evidence the window choice is unimportant.")

head("3. PV - AND WHY IT DOES NOT BIAS CATEGORY B")

print("  PV on the modellable, post-visit population:")
print("    %s" % dict(RP.pv.value_counts(dropna=False)))
print("  Absence is NOT 'no PV' - Unknown is its own level (parent trap 3).")

RP["pv_lvl"] = RP.pv.map({True: "PV", False: "no PV"}).fillna("Unknown")
print("\n  deficiency by PV level:")
for lvl, s in RP.groupby("pv_lvl"):
    print("    %-8s n=%-4d median deficiency %6.0f   decisive %5.1f%%"
          % (lvl, len(s), s.deficiency.median(), 100 * s.decisive.mean()))

print("\n  MEASURED CONCLUSION: Category B is computed from geometry, era, JAZ,")
print("  residents and HDD. IT NEVER TOUCHES THE METER. A PV household's grid")
print("  import under-states its true draw, but that number does not enter the")
print("  deficiency at all. So PV DOES NOT BIAS CATEGORY B.")
print()
print("  PV bites only on meter-based checks. Here is the damage, on the level:")
RP["kwh_yr"] = RP.kwh_per_day * 365
RP["implied_appliance"] = RP.kwh_yr - RP.E_as_built
for lvl, s in RP.groupby("pv_lvl"):
    print("    %-8s implied non-heating electricity: median %6.0f kWh/yr  "
          "5-95%% %7.0f - %7.0f"
          % (lvl, s.implied_appliance.median(),
             s.implied_appliance.quantile(.05), s.implied_appliance.quantile(.95)))
print("  If PV households sit LOWER, that is the invisible self-consumption, and")
print("  it is a reason to keep them out of any meter-based comparison - never")
print("  out of Category B.")

head("4. THE DELIVERABLE - post-visit, ranked within era on the LOWER BOUND")

F = RP.copy()
F["rank_in_era"] = F[F.decisive].groupby("era").deficiency_lo.rank(
    ascending=False, method="min")
F["n_decisive_in_era"] = F.groupby("era").decisive.transform("sum")
print("  %-10s %5s %9s %14s %10s" % ("era", "n", "decisive", "median def_lo", "median band"))
for e in ph.ERA_ORDER:
    s = F[F.era == e]
    if len(s):
        d = s[s.decisive]
        print("  %-10s %5d %9d %14.0f %10.0f"
              % (e, len(s), len(d), d.deficiency_lo.median() if len(d) else np.nan,
                 s.band.median()))

print("\n  TOP 10 OVERALL by lower bound (the honest 'at least this much'):")
t = F[F.decisive].nlargest(10, "deficiency_lo")
print("  %-12s %-10s %-5s %-6s %10s %10s %10s"
      % ("household", "era", "tier", "PV", "def_lo", "point", "band"))
for _, r in t.iterrows():
    print("  %-12d %-10s %-5s %-6s %10.0f %10.0f %10.0f"
          % (r.Household_ID, r.era, r.tier, r.pv_lvl, r.deficiency_lo,
             r.deficiency, r.band))

F.to_parquet(DATA / "p6_final.parquet", index=False)
F.to_csv(DATA / "p6_category_b.csv", index=False, sep=";")
pd.concat([RA, RP]).to_csv(DATA / "p6_window_comparison.csv", index=False, sep=";")
print("\n  written: p6_final.parquet, p6_category_b.csv, p6_window_comparison.csv")
print("\nP6 complete.")
