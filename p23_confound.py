"""P23b - is the vintage gradient really vintage, or heating-curve settings in disguise?

An old, less efficient unit and a heating curve set too high both raise the measured
slope. The meter cannot separate them. If old units also carry higher curve settings or
more curve faults, part of P23's installation-year gradient (measured/physics 1.47 ->
1.05) would be settings, and term_vintage would be taking a technician's kWh.

Inputs:
  * HeatPump_HeatingCurveSetting_Outside0_BeforeVisit - an INSTRUMENT READING (flow
    temperature at 0 C outdoor), permitted (CLAUDE.md, Validation)
  * the inspector's curve / limit verdicts - LABELS, used here only to describe, never
    as model inputs
  * measured slope = P13 v2 (post-visit days, free step); physics vintage OFF (P23)

Tests:
  1  Do fault rates and curve settings differ by installation-year group?
  2  Does the age gradient survive WITHIN equal curve settings and WITHIN equal labels?
  3  log(measured/physics) ~ age + curve setting: does age keep its coefficient once the
     setting is in? Bootstrap 95% CI.

numpy + pandas only.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p23"
RNG = np.random.default_rng(20260918)


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


def grp(y):
    return "unknown" if y != y else ("<2008" if y < 2008 else ("2008-2014" if y < 2015 else ">=2015"))


G = ["<2008", "2008-2014", ">=2015", "unknown"]
sys.stdout = Tee(OUT / "logs" / "p23_confound_run.txt")

pr = pd.read_csv(ROOT / "heapo_data/reports/protocols.csv", sep=None, engine="python")
pr["Household_ID"] = pr.Household_ID.astype("Int64")
hh = (pr[pr.Household_ID.notna()].sort_values("Visit_Date")
      .drop_duplicates("Household_ID", keep="first").set_index("Household_ID"))
curve_cols = [c for c in hh.columns if re.search("HeatingCurve|HeatingLimit", c)]
print("  curve / limit columns in protocols.csv:")
for c in curve_cols:
    print("    %-60s n=%d" % (c, hh[c].notna().sum()))

M = pd.read_parquet(OUT / "data" / "p23_meter_check.parquet").set_index("Household_ID")
M.index = M.index.astype("Int64")
M["gap"] = np.log(M.beta_meas / M.bp_off)
S0 = "HeatPump_HeatingCurveSetting_Outside0_BeforeVisit"
M["curve0"] = pd.to_numeric(hh[S0], errors="coerce").reindex(M.index)
M["curve_high"] = hh["HeatPump_HeatingCurveSetting_TooHigh_BeforeVisit"].reindex(M.index)
M["limit_high"] = hh["HeatPump_HeatingLimitSetting_TooHigh_BeforeVisit"].reindex(M.index)
M["curve_changed"] = hh["HeatPump_HeatingCurveSetting_Changed"].reindex(M.index)
after = [c for c in curve_cols if "Outside0" in c and "After" in c]
if after:
    M["curve0_after"] = pd.to_numeric(hh[after[0]], errors="coerce").reindex(M.index)

head("1. DO SETTINGS AND FAULTS DIFFER BY INSTALLATION YEAR? (145 assessed, P13 v2)")
rate = lambda s: "%.0f%% (%d)" % (100 * (s == True).sum() / s.notna().sum(), s.notna().sum()) \
    if s.notna().sum() else "-"
print("  %-10s %4s | %16s | %14s %14s %14s" % ("group", "n", "curve@0C median", "curve too high",
                                              "limit too high", "curve changed"))
for g in G:
    s = M[M.grp == g]
    print("  %-10s %4d | %16s | %14s %14s %14s"
          % (g, len(s), "%.1f C (n=%d)" % (s.curve0.median(), s.curve0.notna().sum()),
             rate(s.curve_high), rate(s.limit_high), rate(s.curve_changed)))
if "curve0_after" in M:
    print("  curve@0C after the visit, median by group: %s"
          % {g: round(M[M.grp == g].curve0_after.median(), 1) for g in G})

head("2. DOES THE AGE GRADIENT SURVIVE WITHIN EQUAL SETTINGS / LABELS?")
k = M[M.grp != "unknown"].copy()
med = k.curve0.median()
k["setting"] = np.where(k.curve0.isna(), "unknown", np.where(k.curve0 > med, "high curve", "low curve"))
print("  median measured/physics (vintage OFF) by group, split at curve@0C median %.1f C:" % med)
print((np.exp(k.groupby(["setting", "grp"]).gap.median())).unstack().reindex(columns=G[:3]).round(2).to_string())
print(k.groupby(["setting", "grp"]).size().unstack().reindex(columns=G[:3]).to_string())
print("\n  ... split by the inspector's curve label (description only):")
print((np.exp(k.groupby([k.curve_high.astype(str), "grp"]).gap.median())).unstack()
      .reindex(columns=G[:3]).round(2).to_string())

head("3. log(measured/physics) ~ age + curve setting, bootstrap 95% CI")
r = k[k.curve0.notna()].copy()
r["age"] = 2020 - r.hp_install_year
X = lambda d, cols: np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in cols])
for cols in (["age"], ["curve0"], ["age", "curve0"]):
    coef = np.linalg.lstsq(X(r, cols), r.gap.to_numpy(), rcond=None)[0]
    bs = []
    for _ in range(2000):
        b = r.iloc[RNG.integers(0, len(r), len(r))]
        bs.append(np.linalg.lstsq(X(b, cols), b.gap.to_numpy(), rcond=None)[0])
    bs = np.array(bs)
    print("  model %-16s n=%d" % ("+".join(cols), len(r)))
    for i, c in enumerate(cols, start=1):
        lo, hi = np.percentile(bs[:, i], [2.5, 97.5])
        print("    %-7s %+.4f per unit  [%+.4f, %+.4f]  -> %s" % (
            c, coef[i], lo, hi, "per year of age: %+.1f%%" % (100 * (np.exp(coef[i]) - 1))
            if c == "age" else "per K of curve: %+.1f%%" % (100 * (np.exp(coef[i]) - 1))))
print("\n  corr(age, curve@0C) = %.3f  (n=%d)" % (r[["age", "curve0"]].corr().iloc[0, 1], len(r)))
print("  vintage model's own slope, 1999-2017 (air/ground avg): about %+.1f%% per year of age"
      % (100 * ((1 / 0.7775) ** (1 / 18) - 1)))
