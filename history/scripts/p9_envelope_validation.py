"""P9 - validating term_envelope, which carries 75-80% of the deficiency.

Until now the only result clearing 0.5 was OVERSIZING (AUC 0.772 / 0.786), which
validates the CAPACITY term - 2.6% of the total, shipped as a scenario. The term
that carries the headline has never been checked against anything.

protocols.csv has no envelope-condition verdict, so there is no inspector label to
score against. But the METER is an independent measurement, and the physics makes
predictions about it that can be wrong.

  TEST 1  RANK.  Does the physical heat loss coefficient rank households the way
          the measured heating slope does? MUST BE DONE PER m2 - both quantities
          scale with house size, so a raw correlation would mostly measure "big
          houses use more heat" and look impressive while proving nothing.

  TEST 2  MAGNITUDE, and this is the sharp one. TABULA plus our geometry predicts
          a SPECIFIC RATIO between eras - roughly 3x on the slope per m2 between
          pre-1975 and post-2010. A rank correlation cannot fail that; a ratio
          can. If the meter says 1.5x or 6x, the U-values are wrong.

  TEST 3  SUB-METER. Where kWh_hp exists the heat pump is measured directly,
          without household baseload. The cleanest possible check. n is measured
          first - the parent records kwh_hp for 72 of 1,387 households.

NOT DONE, and why: the consultant's ElectricityConsumption_Categorization rates
CONSUMPTION, not envelope. It conflates envelope with settings, occupancy and DHW,
and a consultant who has seen the bills is not independent of them. Reported as a
coarse cross-check in section 5, never as envelope validation.

NOTHING HERE IS TUNED. The constants stay as they are whatever this run says.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph
from p_adapter_heapo import load_households, modellable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p9"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

MIN_DAYS, MIN_WARM, MIN_COLD = 180, 60, 60
NBOOT = 2000
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


def fit(x, y):
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    if len(x) < 3 or sxx <= 0:
        return np.nan, np.nan
    b = ((x - xm) * (y - ym)).sum() / sxx
    return ym - b * xm, b


def spear(a, b):
    s = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(s) < 4:
        return np.nan, np.nan, np.nan, 0
    r = s.corr(method="spearman").iloc[0, 1]
    boot = [pd.DataFrame(s.values[RNG.integers(0, len(s), len(s))],
                         columns=["a", "b"]).corr(method="spearman").iloc[0, 1]
            for _ in range(NBOOT)]
    return r, float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)), len(s)


sys.stdout = Tee(LOGS / "p9_run.txt")

head("1. THE PHYSICAL PREDICTION AND THE MEASURED SLOPE")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)].copy()

ds = pd.read_parquet(ROOT / "outputs/daily_states.parquet",
                     columns=["Household_ID", "date", "state_total",
                              "kwh_total", "kwh_hp"])
hw = pd.read_parquet(ROOT / "outputs/household_weather.parquet",
                     columns=["Household_ID", "date", "HDD_12"])
p = ds.merge(hw, on=["Household_ID", "date"], how="inner")
p = p[p.state_total.isin(["NORMAL", "MIXED_ZERO"]) & p.HDD_12.notna()]

rows = []
for hid, g in p[p.kwh_total.notna()].groupby("Household_ID"):
    n, w, c = len(g), int((g.HDD_12 == 0).sum()), int((g.HDD_12 > 0).sum())
    if n < MIN_DAYS or w < MIN_WARM or c < MIN_COLD:
        continue
    a, b = fit(g.HDD_12.to_numpy(float), g.kwh_total.to_numpy(float))
    rows.append({"Household_ID": hid, "n_days": n, "hdd_per_day": g.HDD_12.mean(),
                 "kwh_per_day": g.kwh_total.mean(), "beta_meas": b, "floor_meas": a})
E = pd.DataFrame(rows)
D = M.merge(E, on="Household_ID", how="inner")

ev = [ph.evaluate(r) for r in D.to_dict("records")]
D["H_as_built"] = [e["H_as_built"] for e in ev]
D["jaz"] = [e["jaz_as_built"] for e in ev]
D["term_envelope"] = [e["term_envelope"] for e in ev]
D["beta_phys"] = D.H_as_built * 24 / 1000 / D.jaz          # kWh per degree-day
D["beta_phys_m2"] = D.beta_phys / D.area_m2
D["beta_meas_m2"] = D.beta_meas / D.area_m2
D = D[D.beta_meas.notna() & (D.beta_meas > 0)]
print("  households with a physical prediction and a measured slope : %d" % len(D))
print("  measured slope  kWh/degree-day : median %.3f  IQR %.3f-%.3f"
      % (D.beta_meas.median(), D.beta_meas.quantile(.25), D.beta_meas.quantile(.75)))
print("  physical slope  kWh/degree-day : median %.3f  IQR %.3f-%.3f"
      % (D.beta_phys.median(), D.beta_phys.quantile(.25), D.beta_phys.quantile(.75)))
print("  physical / measured            : median %.2f"
      % (D.beta_phys / D.beta_meas).median())

head("2. TEST 1 - RANK. Raw, then AREA-CONTROLLED, which is the real test")

r, lo, hi, n = spear(D.beta_phys, D.beta_meas)
print("  RAW      rho %+.3f [%+.3f, %+.3f]  n=%d" % (r, lo, hi, n))
r2, lo2, hi2, _ = spear(D.area_m2, D.beta_meas)
print("  AREA alone vs measured slope: rho %+.3f [%+.3f, %+.3f]" % (r2, lo2, hi2))
print("  -> both quantities scale with house size, so the RAW figure is inflated")
print("     by area and is NOT the test.")
r3, lo3, hi3, n3 = spear(D.beta_phys_m2, D.beta_meas_m2)
print("\n  PER m2  rho %+.3f [%+.3f, %+.3f]  n=%d   <- THE TEST" % (r3, lo3, hi3, n3))
print("  Per m2 the physical prediction varies ONLY through era, renovation and")
print("  the geometric huellzahl. Nothing else is left for it to borrow from.")

head("3. TEST 2 - MAGNITUDE. The sharp one a rank correlation cannot fail")

t = D.groupby("era").agg(n=("beta_meas_m2", "size"),
                         phys=("beta_phys_m2", "median"),
                         meas=("beta_meas_m2", "median")).reindex(ph.ERA_ORDER)
t = t[t.n >= 5]
print("  median heating slope per m2, kWh/(degree-day*m2):")
print("  %-10s %5s %10s %10s %8s" % ("era", "n", "physics", "measured", "meas/phys"))
for e, r_ in t.iterrows():
    print("  %-10s %5d %10.5f %10.5f %8.2f"
          % (e, r_.n, r_.phys, r_.meas, r_.meas / r_.phys))

if "pre1975" in t.index and "post2010" in t.index:
    pr_p = t.loc["pre1975", "phys"] / t.loc["post2010", "phys"]
    pr_m = t.loc["pre1975", "meas"] / t.loc["post2010", "meas"]
    print("\n  THE PREDICTION: pre-1975 over post-2010, slope per m2")
    print("    physics predicts %.2fx" % pr_p)
    print("    the meter says   %.2fx" % pr_m)
    print("    ratio of ratios  %.2f" % (pr_m / pr_p))
    b = []
    for _ in range(NBOOT):
        s1 = D[D.era == "pre1975"].beta_meas_m2.sample(frac=1, replace=True)
        s2 = D[D.era == "post2010"].beta_meas_m2.sample(frac=1, replace=True)
        b.append(s1.median() / s2.median())
    print("    measured ratio 95%% CI [%.2f, %.2f]"
          % (np.percentile(b, 2.5), np.percentile(b, 97.5)))
    print("\n  A rank correlation cannot fail this test. A ratio can. If the")
    print("  measured multiple sits far from the predicted one, the U-values are")
    print("  wrong even when the ordering is right.")

head("4. TEST 3 - SUB-METER. The cleanest check, if n allows")

hp = p[p.kwh_hp.notna()]
print("  households with ANY kwh_hp day in the panel : %d" % hp.Household_ID.nunique())
rows = []
for hid, g in hp.groupby("Household_ID"):
    n, w, c = len(g), int((g.HDD_12 == 0).sum()), int((g.HDD_12 > 0).sum())
    if n < MIN_DAYS or w < MIN_WARM or c < MIN_COLD:
        continue
    a, b = fit(g.HDD_12.to_numpy(float), g.kwh_hp.to_numpy(float))
    rows.append({"Household_ID": hid, "beta_hp": b, "n_hp": n})
S = pd.DataFrame(rows)
print("  ...clearing %d/%d/%d on the HeatPump channel : %d"
      % (MIN_DAYS, MIN_WARM, MIN_COLD, len(S)))
J = D.merge(S, on="Household_ID", how="inner") if len(S) else pd.DataFrame()
print("  ...AND modellable here                     : %d" % len(J))
if len(J) >= 8:
    J["beta_hp_m2"] = J.beta_hp / J.area_m2
    r4, lo4, hi4, n4 = spear(J.beta_phys_m2, J.beta_hp_m2)
    print("\n  physical vs SUB-METERED slope, per m2: rho %+.3f [%+.3f, %+.3f] n=%d"
          % (r4, lo4, hi4, n4))
    print("  physics / sub-metered slope: median %.2f"
          % (J.beta_phys / J.beta_hp).median())
    print("  The sub-meter excludes household baseload, so this is the cleanest")
    print("  comparison available - and the smallest.")
else:
    print("\n  n = %d. TOO FEW TO TEST. The overlap between sub-metering and the" % len(J))
    print("  protocol cohort is the binding constraint, not our modelling.")
    print("  Reported as a measured ceiling, not attempted and failed.")

head("5. COARSE CROSS-CHECK - the consultant's consumption rating")

D["cat"] = D.get("label_consumption_cat")
raw = pd.read_csv(ROOT / "heapo_data/reports/protocols.csv", sep=None,
                  engine="python")
raw["Household_ID"] = raw.Household_ID.astype("Int64")
cat = (raw[raw.Household_ID.notna()].drop_duplicates("Household_ID", keep="first")
       [["Household_ID", "HeatPump_ElectricityConsumption_Categorization"]])
cat["Household_ID"] = cat.Household_ID.astype("int64")
K = D.merge(cat, on="Household_ID", how="left")
c = "HeatPump_ElectricityConsumption_Categorization"
print("  coverage: %d of %d" % (int(K[c].notna().sum()), len(K)))
print("  %s" % dict(K[c].value_counts(dropna=False)))
if K[c].notna().sum() >= 20:
    print("\n  median term_envelope by the consultant's rating:")
    for lvl, s in K[K[c].notna()].groupby(c):
        if len(s) >= 5:
            print("    %-14s n=%-4d envelope %7.0f kWh/yr   measured slope/m2 %.5f"
                  % (lvl, len(s), s.term_envelope.median(), s.beta_meas_m2.median()))
print("\n  THIS RATES CONSUMPTION, NOT ENVELOPE. It conflates envelope with")
print("  settings, occupancy and DHW, and the consultant had seen the bills.")
print("  A coarse cross-check. NEVER quote it as envelope validation.")

D.to_parquet(DATA / "p9_envelope_validation.parquet", index=False)
D.to_csv(DATA / "p9_envelope_validation.csv", index=False, sep=";")
print("\n  written: p9_envelope_validation.parquet/.csv")
print("\nP9 complete.")
