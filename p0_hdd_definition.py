"""P0 - HDD_12 versus HDD_SIA, head to head.

The spec uses SIA 381/3 degree days, HGT 20/12: max(0, 20 - T) when T <= 12.
This project's permanent standard is HDD_12: max(0, 12 - T). They are different
quantities and the CLAUDE.md requires both to be measured before either is
adopted.

STRUCTURAL IDENTITY, checked in section 2: on a heating day 20 - T = (12 - T) + 8,
so HDD_SIA = HDD_12 + 8 * 1{T < 12}. SIA is NOT a rescaled HDD_12 - it bundles a
STEP FUNCTION in with the slope. Any fit advantage it shows may therefore be the
step, not the degree days, and the decomposition separates the two.

This is a ONE-OFF, FLEET-WIDE, DECLARED model selection between two a-priori
definitions. It is NOT per-household base fitting, which stays barred.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p0"
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


sys.stdout = Tee(LOGS / "p0_run.txt")

head("1. THE PANEL")

ds = pd.read_parquet(ROOT / "outputs/daily_states.parquet",
                     columns=["Household_ID", "date", "state_total",
                              "kwh_total", "kwh_hp"])
hw = pd.read_parquet(ROOT / "outputs/household_weather.parquet",
                     columns=["Household_ID", "date", "temp_mean",
                              "HDD_12", "HDD_SIA"])
p = ds.merge(hw, on=["Household_ID", "date"], how="inner")
print("  daily_states rows            : %s" % f"{len(ds):,}")
print("  household_weather rows       : %s" % f"{len(hw):,}")
print("  joined                       : %s" % f"{len(p):,}")

usable = (p.state_total.isin(["NORMAL", "MIXED_ZERO"]) & p.kwh_total.notna()
          & p.HDD_12.notna() & p.HDD_SIA.notna())
p = p[usable].copy()
print("  usable household-days        : %s" % f"{len(p):,}")
print("  households present           : %s" % f"{p.Household_ID.nunique():,}")

pr = pd.read_csv(ROOT / "heapo_data/reports/protocols.csv", sep=None,
                 engine="python")
pr["Household_ID"] = pr.Household_ID.astype("Int64")
pr = pr[pr.Household_ID.notna()].copy()
pr["visit_date"] = pd.to_datetime(pr.Visit_Date, errors="coerce")
vis = (pr.sort_values("visit_date")
       .drop_duplicates("Household_ID", keep="first")[["Household_ID",
                                                       "visit_date"]])
vis["Household_ID"] = vis.Household_ID.astype("int64")
print("  protocol reports with an ID  : %d" % len(pr))
print("  distinct protocol households : %d" % len(vis))
print("  with a parsed visit date     : %d" % int(vis.visit_date.notna().sum()))

head("2. IS HDD_SIA THE SAME AS HDD_12 PLUS A STEP OF 8 ON HEATING DAYS (T < 12, strict)?")

heating = p.temp_mean < 12.0
pred = p.HDD_12.to_numpy() + 8.0 * heating.to_numpy()
act = p.HDD_SIA.to_numpy()
dev = np.abs(pred - act)
print("  rows tested                  : %s" % f"{len(p):,}")
print("  exact matches (< 1e-9)       : %s  (%.4f%%)"
      % (f"{int((dev < 1e-9).sum()):,}", 100 * (dev < 1e-9).mean()))
print("  max absolute deviation       : %.6g" % dev.max())
if dev.max() < 1e-6:
    print("  -> IDENTITY HOLDS. HDD_SIA carries a STEP of 8 on every heating day.")
else:
    print("  -> identity does NOT hold exactly; inspect before trusting the")
    print("     decomposition below.")

print("\n  correlation HDD_12 vs HDD_SIA, all days      : %.4f"
      % np.corrcoef(p.HDD_12, p.HDD_SIA)[0, 1])
h = p[heating]
print("  correlation on HEATING DAYS ONLY             : %.4f  (n=%s)"
      % (np.corrcoef(h.HDD_12, h.HDD_SIA)[0, 1], f"{len(h):,}"))
print("  On heating days the two differ by a constant, so within the heating")
print("  season they are the SAME regressor up to an intercept shift. All of")
print("  the SIA definition's extra information sits at the season boundary.")


def fit(x, y):
    n = len(x)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    if n < 3 or sxx <= 0:
        return np.nan, np.nan, np.nan, np.nan
    b = ((x - xm) * (y - ym)).sum() / sxx
    a = ym - b * xm
    res = y - (a + b * x)
    sse = (res ** 2).sum()
    sst = ((y - ym) ** 2).sum()
    r2 = 1.0 - sse / sst if sst > 0 else np.nan
    return a, b, r2, np.sqrt(sse / n)


def fit3(x1, x2, y):
    X = np.column_stack([np.ones(len(y)), x1, x2])
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return np.nan
    res = y - X @ beta
    sst = ((y - y.mean()) ** 2).sum()
    return 1.0 - (res ** 2).sum() / sst if sst > 0 else np.nan


def run(panel, label, tag):
    head(label)
    rows = []
    for hid, g in panel.groupby("Household_ID", sort=True):
        y = g.kwh_total.to_numpy(dtype=float)
        d12 = g.HDD_12.to_numpy(dtype=float)
        dsi = g.HDD_SIA.to_numpy(dtype=float)
        step = (g.temp_mean.to_numpy(dtype=float) < 12.0).astype(float)
        n = len(y)
        nwarm = int((d12 == 0).sum())
        ncold = int((d12 > 0).sum())
        if n < MIN_DAYS or nwarm < MIN_WARM or ncold < MIN_COLD:
            continue
        a12, b12, r12, e12 = fit(d12, y)
        asi, bsi, rsi, esi = fit(dsi, y)
        r_step = fit(step, y)[2]
        r_both = fit3(d12, step, y)
        rows.append(dict(Household_ID=hid, n_days=n, n_warm=nwarm, n_cold=ncold,
                         a_12=a12, b_12=b12, r2_12=r12, rmse_12=e12,
                         a_sia=asi, b_sia=bsi, r2_sia=rsi, rmse_sia=esi,
                         r2_steponly=r_step, r2_hdd12_plus_step=r_both))
    R = pd.DataFrame(rows)
    if R.empty:
        print("  no household clears the day requirements.")
        return R

    R["d_r2"] = R.r2_sia - R.r2_12
    R["d_rmse"] = R.rmse_sia - R.rmse_12
    print("  households fitted (>=%dd, >=%d warm, >=%d cold) : %d"
          % (MIN_DAYS, MIN_WARM, MIN_COLD, len(R)))
    print("\n  median R2   HDD_12  : %.4f" % R.r2_12.median())
    print("  median R2   HDD_SIA : %.4f" % R.r2_sia.median())
    print("  median RMSE HDD_12  : %.4f kWh/day" % R.rmse_12.median())
    print("  median RMSE HDD_SIA : %.4f kWh/day" % R.rmse_sia.median())

    d = R.d_r2.dropna().to_numpy()
    boot = np.array([RNG.choice(d, len(d), replace=True).mean()
                     for _ in range(NBOOT)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    wins_sia = int((R.d_r2 > 0).sum())
    print("\n  PAIRED, same households and same days:")
    print("    mean   dR2 (SIA - HDD_12) : %+.4f   95%% CI [%+.4f, %+.4f]"
          % (d.mean(), lo, hi))
    print("    median dR2                : %+.4f" % np.median(d))
    print("    SIA fits better in        : %d / %d  (%.1f%%)"
          % (wins_sia, len(R), 100 * wins_sia / len(R)))
    print("    median dRMSE              : %+.4f kWh/day" % R.d_rmse.median())

    print("\n  DECOMPOSITION - is any SIA advantage the degree days, or the step?")
    print("    median R2, step indicator alone      : %.4f" % R.r2_steponly.median())
    print("    median R2, HDD_12 + step (2 params)  : %.4f"
          % R.r2_hdd12_plus_step.median())
    print("    median R2, HDD_SIA alone (1 param)   : %.4f" % R.r2_sia.median())
    gap = (R.r2_hdd12_plus_step - R.r2_sia).median()
    print("    median R2 gap, (HDD_12+step) - SIA   : %+.4f" % gap)
    print("    HDD_SIA is the CONSTRAINED version of HDD_12 + step, with the step")
    print("    coefficient forced to exactly 8x the slope. A gap near zero means")
    print("    the constraint costs nothing; a large gap means SIA imposes a")
    print("    ratio the data does not support.")

    R.to_csv(DATA / ("p0_hdd_fits_%s.csv" % tag), index=False, sep=";")
    print("\n  written: p0_hdd_fits_%s.csv" % tag)
    return R


prot_ids = set(vis.Household_ID)
cohort = p[p.Household_ID.isin(prot_ids)].copy()
R_cohort = run(cohort,
               "3. PROTOCOL COHORT (this workstream's population), all usable days",
               "cohort_all")
R_fleet = run(p, "4. FLEET-WIDE, all usable days (robustness check)", "fleet_all")

post = cohort.merge(vis, on="Household_ID", how="left")
post = post[post.visit_date.notna()
            & (pd.to_datetime(post.date) > post.visit_date)].copy()
R_post = run(post,
             "5. PROTOCOL COHORT, POST-VISIT DAYS ONLY (the production rule)",
             "cohort_post")

head("6. VERDICT")
for name, R in [("protocol cohort, all days", R_cohort),
                ("fleet-wide, all days", R_fleet),
                ("protocol cohort, post-visit", R_post)]:
    if R.empty:
        print("  %-32s : no households" % name)
        continue
    d = R.d_r2.dropna()
    win = "HDD_SIA" if d.mean() > 0 else "HDD_12"
    print("  %-32s : n=%-5d  median R2 %.4f (12) vs %.4f (SIA)   "
          "mean dR2 %+.4f  -> %s"
          % (name, len(R), R.r2_12.median(), R.r2_sia.median(), d.mean(), win))

print("\nP0 complete.")
