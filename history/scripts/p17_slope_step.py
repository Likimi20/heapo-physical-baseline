"""P17 - limitation 4, the ~22% slope baseline. Step 1 and step 3 of the plan.

Spec v3 proposes subtracting the fleet-median slope excess. REJECTED: it is the
fleet-median correction CLAUDE.md already rejects, and 78.5% of the cohort carries a
recorded fault, so the fleet median is not a fault-free reference.

STEP 1 - the measurement, not a constant. beta_meas (P9/P13) is a plain OLS of kWh on
HDD_12. P0 measured a real heating-season step: HDD_12 + a FREE step lifts cohort R2
0.7299 -> 0.7587. A straight line through a step at HDD = 0 absorbs the step as extra
slope. Refit with the step FREE, as CLAUDE.md already permits ("a heating-season term
takes it as a free parameter"). No physics constant moves, so the calibration rule is
not engaged.

STEP 3 - a band on the slope excess. SLOPE_EXCESS is today a point estimate > 0.
Meter side: block bootstrap by calendar month (daily data are autocorrelated, so the
OLS standard error would be too narrow). Physics side: Monte Carlo over the published
constant spreads. Difference of independent draws -> 95% band.

Same households, same days, same sufficiency as P9/P13: all usable days, >=180/60/60.

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
OUT = HERE / "outputs" / "p17"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

MIN_DAYS, MIN_WARM, MIN_COLD = 180, 60, 60
NREP = 200
RNG_BOOT = np.random.default_rng(20260915)
RNG_MC = np.random.default_rng(20260916)
RNG_SP = np.random.default_rng(20260917)


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


def ols(X, y):
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef


def spear(a, b):
    s = pd.DataFrame({"a": a, "b": b}).dropna()
    r = s.corr(method="spearman").iloc[0, 1]
    bs = [pd.DataFrame(s.values[RNG_SP.integers(0, len(s), len(s))], columns=["a", "b"])
          .corr(method="spearman").iloc[0, 1] for _ in range(2000)]
    return r, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


sys.stdout = Tee(LOGS / "p17_run.txt")

head("1. REFIT - straight line versus line plus a free heating-season step")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)].copy()
ds = pd.read_parquet(ROOT / "outputs/daily_states.parquet",
                     columns=["Household_ID", "date", "state_total", "kwh_total"])
hw = pd.read_parquet(ROOT / "outputs/household_weather.parquet",
                     columns=["Household_ID", "date", "HDD_12"])
p = ds.merge(hw, on=["Household_ID", "date"], how="inner")
p = p[p.state_total.isin(["NORMAL", "MIXED_ZERO"]) & p.kwh_total.notna()
      & p.HDD_12.notna() & p.Household_ID.isin(M.Household_ID)]
p["month"] = pd.to_datetime(p.date).dt.to_period("M")

rows = []
for hid, g in p.groupby("Household_ID"):
    n, w, c = len(g), int((g.HDD_12 == 0).sum()), int((g.HDD_12 > 0).sum())
    if n < MIN_DAYS or w < MIN_WARM or c < MIN_COLD:
        continue
    x = g.HDD_12.to_numpy(float)
    y = g.kwh_total.to_numpy(float)
    s = (x > 0).astype(float)
    X2 = np.column_stack([np.ones(n), x])
    X3 = np.column_stack([np.ones(n), x, s])
    a2, b2 = ols(X2, y)
    a3, b3, c3 = ols(X3, y)
    r2_2 = 1 - ((y - X2 @ [a2, b2]) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    r2_3 = 1 - ((y - X3 @ [a3, b3, c3]) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    months = g.month.to_numpy()
    um = np.unique(months)
    idx = {m: np.flatnonzero(months == m) for m in um}
    bb2, bb3, cc3 = [], [], []
    for _ in range(NREP):
        take = np.concatenate([idx[m] for m in RNG_BOOT.choice(um, len(um), replace=True)])
        xs, ys = x[take], y[take]
        ss = (xs > 0).astype(float)
        if (ss == 0).sum() < 5 or (ss == 1).sum() < 5:
            continue
        bb2.append(ols(np.column_stack([np.ones(len(xs)), xs]), ys)[1])
        k = ols(np.column_stack([np.ones(len(xs)), xs, ss]), ys)
        bb3.append(k[1])
        cc3.append(k[2])
    rows.append({"Household_ID": hid, "n_days": n, "n_months": len(um),
                 "hdd_per_day": x.mean(), "b_line": b2, "b_step": b3, "step_kwh_day": c3,
                 "floor_line": a2, "floor_step": a3, "r2_line": r2_2, "r2_step": r2_3,
                 "boot_b_line": np.array(bb2), "boot_b_step": np.array(bb3),
                 "step_lo": np.percentile(cc3, 2.5), "step_hi": np.percentile(cc3, 97.5)})
F = pd.DataFrame(rows)
D = M.merge(F, on="Household_ID", how="inner")
print("  households: %d   (P9/P13: 172)" % len(D))
print("  median R2  line %.4f   line + free step %.4f   (P0 cohort: 0.7299 / 0.7587)"
      % (D.r2_line.median(), D.r2_step.median()))
print("  step, kWh/day: median %.2f  IQR %.2f - %.2f;  whole 95%% band above zero: %d / %d"
      % (D.step_kwh_day.median(), D.step_kwh_day.quantile(.25), D.step_kwh_day.quantile(.75),
         int((D.step_lo > 0).sum()), len(D)))
print("  step expressed in degree-days (step / slope): median %.2f K   (SIA welds it at 8)"
      % (D.step_kwh_day / D.b_step).median())
print("  slope, step model / line model: median %.3f  IQR %.3f - %.3f"
      % ((D.b_step / D.b_line).median(), (D.b_step / D.b_line).quantile(.25),
         (D.b_step / D.b_line).quantile(.75)))

head("2. THE PHYSICAL SLOPE, point and Monte Carlo band")

bp_draws = []
for h in D.to_dict("records"):
    e = ph.evaluate(h)
    dr = [ph.evaluate(h, RNG_MC) for _ in range(NREP)]
    bp_draws.append(np.array([d["H_as_built"] * 24 / 1000 / d["jaz_as_built"] for d in dr]))
    h["_bp"] = e["H_as_built"] * 24 / 1000 / e["jaz_as_built"]
    h["_hdd_c"] = e["hdd_corrected"]
D["beta_phys"] = [ph.evaluate(h)["H_as_built"] * 24 / 1000 / ph.evaluate(h)["jaz_as_built"]
                  for h in D.to_dict("records")]
D["hdd_corrected"] = [ph.evaluate(h)["hdd_corrected"] for h in D.to_dict("records")]
D["bp_lo"] = [np.percentile(b, 2.5) for b in bp_draws]
D["bp_hi"] = [np.percentile(b, 97.5) for b in bp_draws]
print("  physics band, median relative width %.0f%%"
      % (100 * ((D.bp_hi - D.bp_lo) / D.beta_phys).median()))

head("3. THE ~22% - how much of it was the missing step?")

for col, name in [("b_line", "line (P9/P13)"), ("b_step", "line + free step")]:
    ratio = (D.beta_phys / D[col]).median()
    print("  %-18s physics / measured median %.3f   -> measured runs %+.0f%% above physics"
          % (name, ratio, 100 * (1 / ratio - 1)))
print("\n  era ratio measured/physics (median/median, P9 method):")
print("  %-10s %4s %8s %8s" % ("era", "n", "line", "step"))
for e in ph.ERA_ORDER:
    q = D[D.era == e]
    bpm = (q.beta_phys / q.area_m2).median()
    print("  %-10s %4d %8.2f %8.2f" % (e, len(q), (q.b_line / q.area_m2).median() / bpm,
                                        (q.b_step / q.area_m2).median() / bpm))
for col in ["b_line", "b_step"]:
    r, lo, hi = spear(D.beta_phys / D.area_m2, D[col] / D.area_m2)
    print("  Spearman per m2, physics vs %-7s %+.3f [%+.3f, %+.3f]" % (col, r, lo, hi))

head("4. THE BAND ON THE SLOPE EXCESS - status from the band, not the point")

res = {}
for col in ["b_line", "b_step"]:
    lo_, hi_, st = [], [], []
    for (_, r), bpd in zip(D.iterrows(), bp_draws):
        bm = r["boot_" + col]
        k = min(len(bm), len(bpd))
        diff = (bm[:k] - bpd[:k]) * r.hdd_corrected * 365
        lo, hi = np.percentile(diff, [2.5, 97.5])
        lo_.append(lo)
        hi_.append(hi)
        st.append("SLOPE_EXCESS" if lo > 0 else ("BELOW_PHYSICS" if hi < 0 else "INCONCLUSIVE"))
    D["excess_" + col] = (D[col] - D.beta_phys) * D.hdd_corrected * 365
    D["excess_lo_" + col], D["excess_hi_" + col], D["status_" + col] = lo_, hi_, st
    point = int((D["excess_" + col] > 0).sum())
    vc = pd.Series(st).value_counts().to_dict()
    print("  %-7s point > 0: %3d   band: %s   excess median %.0f kWh/yr, band median %.0f"
          % (col, point, vc, D["excess_" + col].median(),
             (D["excess_hi_" + col] - D["excess_lo_" + col]).median()))
print("\n  P13 today: SLOPE_EXCESS 125 / NO_SLOPE_EXCESS 47, on the point estimate (line).")
print("\n  cross-tab, line point status vs step band status:")
print(pd.crosstab(np.where(D.excess_b_line > 0, "point>0 (P13)", "point<=0 (P13)"),
                  D.status_b_step).to_string())

head("5. LIMITATION 3 RE-READ - P16's thermal-bridge scenarios on the STEP slope")

T = D[["Household_ID", "era", "area_m2", "b_line", "b_step"]].merge(
    pd.read_parquet(HERE / "outputs/p16/data/p16_households.parquet")[
        ["Household_ID", "a_th", "H_live", "jaz_live"]], on="Household_ID")
print("  households joined to P16: %d" % len(T))
print("  %-6s %-5s | %s | %6s | %9s" % ("dU_tb", "slope", "  ".join("%9s" % e[:9]
                                        for e in ph.ERA_ORDER), "range", "phys/meas"))
for du in [0.0, 0.05, 0.10, 0.15]:
    bpm2 = (T.H_live + du * T.a_th) * 24 / 1000 / T.jaz_live / T.area_m2
    for col in ["b_line", "b_step"]:
        vals = [(T.loc[T.era == e, col] / T.loc[T.era == e, "area_m2"]).median()
                / bpm2[T.era == e].median() for e in ph.ERA_ORDER]
        print("  %-6.2f %-5s | %s | %6.2f | %9.3f"
              % (du, col[2:], "  ".join("%9.2f" % v for v in vals), max(vals) - min(vals),
                 (bpm2 * T.area_m2 / T[col]).median()))

out = D.drop(columns=["boot_b_line", "boot_b_step"])
keep = [c for c in out.columns if not c.startswith("label_")]
out[keep].to_parquet(DATA / "p17_slope_step.parquet", index=False)
out[keep].to_csv(DATA / "p17_slope_step.csv", sep=";", index=False)
print("\n  written: p17_slope_step")
