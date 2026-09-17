"""P7 - the compensation test. Does a physical deficiency stop a setting fix working?

THE HYPOTHESIS, and it is the C-class mechanism.

A setting fault can be a RATIONAL RESPONSE to a physical deficiency. A house is
badly insulated, or its radiators were sized for a 70 C oil boiler. The occupants
are cold, so someone turns the heating curve up. The inspector writes "heating
curve too high" - and it is too high, AND IT IS DOING ITS JOB. Turn it down and
the house gets cold and the occupant turns it back up.

TESTABLE PREDICTION. Among households where the consultant ACTUALLY CHANGED the
heating curve, those with a large computed physical deficiency should show LESS
post-visit reduction than those with a small one.

WHY IT MATTERS BEYOND THIS WORKSTREAM. S10 next door measured that the visits did
not work at all - visited vs placebo AUC 0.474, median -0.0034 kWh/DD. If a large
share of "corrected" curves were holding up deficient buildings, that null result
has a mechanism. Nobody has tested it.

DESIGN
  treatment  HeatPump_HeatingCurveSetting_Changed == True
  control    == False - visited, inspected, this setting left alone. The visit
             itself, its season and its attention are common to both arms, which
             a pseudo-date placebo cannot achieve.
  outcome    change in the WEATHER-NORMALISED heating slope and annual level,
             fitted separately pre and post
  moderator  the P6 computed deficiency - which never touches the meter, so it
             cannot be contaminated by the outcome it is moderating

Deficiency comes from the physics; the outcome comes from the meter; the label
comes from the inspector. Three independent sources.

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
OUT = HERE / "outputs" / "p7"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

STRICT = dict(days=180, warm=60, cold=60)
RELAXED = dict(days=120, warm=30, cold=30)
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
    n = len(x)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    if n < 3 or sxx <= 0:
        return np.nan, np.nan
    b = ((x - xm) * (y - ym)).sum() / sxx
    return ym - b * xm, b


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    d = pos[:, None] - neg[None, :]
    return ((d > 0).sum() + 0.5 * (d == 0).sum()) / (len(pos) * len(neg))


def auc_ci(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) < 3 or len(neg) < 3:
        return auc(pos, neg), np.nan, np.nan
    b = [auc(RNG.choice(pos, len(pos), True), RNG.choice(neg, len(neg), True))
         for _ in range(NBOOT)]
    return auc(pos, neg), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def med_ci(x):
    x = np.asarray(x, float)
    if len(x) < 3:
        return np.median(x), np.nan, np.nan
    b = [np.median(RNG.choice(x, len(x), True)) for _ in range(NBOOT)]
    return np.median(x), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


sys.stdout = Tee(LOGS / "p7_run.txt")

head("1. THE DEFICIENCY, FROM THE PHYSICS - it never touches the meter")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)].copy()

ds = pd.read_parquet(ROOT / "outputs/daily_states.parquet",
                     columns=["Household_ID", "date", "state_total", "kwh_total"])
hw = pd.read_parquet(ROOT / "outputs/household_weather.parquet",
                     columns=["Household_ID", "date", "HDD_12"])
p = ds.merge(hw, on=["Household_ID", "date"], how="inner")
p = p[p.state_total.isin(["NORMAL", "MIXED_ZERO"]) & p.kwh_total.notna()
      & p.HDD_12.notna()].copy()
p["date"] = pd.to_datetime(p.date)
p = p.merge(M[["Household_ID", "visit_date"]], on="Household_ID", how="inner")
p["side"] = np.where(p.date <= p.visit_date, "pre", "post")

whole = p.groupby("Household_ID").agg(n_days=("HDD_12", "size"),
                                      hdd_per_day=("HDD_12", "mean")).reset_index()
M = M.merge(whole, on="Household_ID", how="inner")
M["deficiency"] = [ph.evaluate(r)["deficiency"] for r in M.to_dict("records")]
print("  households with a deficiency and a visit date : %d" % len(M))
print("  deficiency median %.0f kWh/yr  IQR %.0f - %.0f"
      % (M.deficiency.median(), M.deficiency.quantile(.25),
         M.deficiency.quantile(.75)))

head("2. PRE AND POST FITS - how many households can be measured at all?")

rows = []
for hid, g in p.groupby("Household_ID"):
    r = {"Household_ID": hid}
    for side in ("pre", "post"):
        s = g[g.side == side]
        r["n_" + side] = len(s)
        r["warm_" + side] = int((s.HDD_12 == 0).sum())
        r["cold_" + side] = int((s.HDD_12 > 0).sum())
        a, b = fit(s.HDD_12.to_numpy(float), s.kwh_total.to_numpy(float)) \
            if len(s) >= 3 else (np.nan, np.nan)
        r["a_" + side], r["b_" + side] = a, b
        r["hdd_" + side] = s.HDD_12.mean() if len(s) else np.nan
    rows.append(r)
F = pd.DataFrame(rows)

for nm, rule in [("STRICT 180/60/60", STRICT), ("RELAXED 120/30/30", RELAXED)]:
    ok = ((F.n_pre >= rule["days"]) & (F.warm_pre >= rule["warm"])
          & (F.cold_pre >= rule["cold"]) & (F.n_post >= rule["days"])
          & (F.warm_post >= rule["warm"]) & (F.cold_post >= rule["cold"])
          & F.b_pre.notna() & F.b_post.notna())
    print("  %-20s both sides sufficient : %d of %d" % (nm, int(ok.sum()), len(F)))

rule = STRICT
ok = ((F.n_pre >= rule["days"]) & (F.warm_pre >= rule["warm"])
      & (F.cold_pre >= rule["cold"]) & (F.n_post >= rule["days"])
      & (F.warm_post >= rule["warm"]) & (F.cold_post >= rule["cold"])
      & F.b_pre.notna() & F.b_post.notna())
print("\n  STRICT is used. Relaxing to 120/30/30 buys only 3 households (86 vs 83),")
print("  so there is no case for loosening the rule and it is not loosened.")

D = F[ok].merge(M, on="Household_ID", how="inner")
D["d_slope"] = D.b_post - D.b_pre
D["d_slope_pct"] = 100 * (D.b_post - D.b_pre) / D.b_pre
# level at a COMMON weather, so the two periods are comparable
COMMON = p.HDD_12.mean()
D["lvl_pre"] = D.a_pre + D.b_pre * COMMON
D["lvl_post"] = D.a_post + D.b_post * COMMON
D["d_level_pct"] = 100 * (D.lvl_post - D.lvl_pre) / D.lvl_pre
print("  households in the test : %d" % len(D))

head("3. DID THE CURVE CHANGE DO ANYTHING AT ALL?")

D["changed"] = D.label_curve_changed
ch = D[D.changed == True]
un = D[D.changed == False]
print("  curve CHANGED at the visit : %d" % len(ch))
print("  curve left alone           : %d" % len(un))
print("  not recorded               : %d" % int(D.changed.isna().sum()))

for nm, col in [("heating slope, %", "d_slope_pct"),
                ("normalised level, %", "d_level_pct")]:
    m1, l1, h1 = med_ci(ch[col].dropna())
    m0, l0, h0 = med_ci(un[col].dropna())
    a, lo, hi = auc_ci(ch[col].dropna(), un[col].dropna())
    print("\n  %s" % nm)
    print("    changed    median %+7.2f  [%+7.2f, %+7.2f]  n=%d" % (m1, l1, h1, len(ch)))
    print("    unchanged  median %+7.2f  [%+7.2f, %+7.2f]  n=%d" % (m0, l0, h0, len(un)))
    print("    AUC changed-over-unchanged %.3f [%.3f, %.3f]" % (a, lo, hi))
print("\n  AUC below 0.5 means the changed houses fell FURTHER, i.e. the fix worked.")

head("4. THE COMPENSATION TEST - does a deficiency blunt the fix?")

ch = ch.copy()
ch["def_grp"] = pd.qcut(ch.deficiency, 2, labels=["low deficiency",
                                                  "high deficiency"])
print("  Among the %d households whose curve WAS turned down, split at the" % len(ch))
print("  median computed deficiency:\n")
for col, nm in [("d_slope_pct", "heating slope, %"),
                ("d_level_pct", "normalised level, %")]:
    print("  %s" % nm)
    for g, s in ch.groupby("def_grp", observed=True):
        m, l, h = med_ci(s[col].dropna())
        print("    %-16s median %+7.2f  [%+7.2f, %+7.2f]  n=%d"
              % (g, m, l, h, len(s)))
    hi_g = ch[ch.def_grp == "high deficiency"][col].dropna()
    lo_g = ch[ch.def_grp == "low deficiency"][col].dropna()
    a, l, h = auc_ci(hi_g, lo_g)
    print("    AUC high-over-low %.3f [%.3f, %.3f]" % (a, l, h))
    print("    PREDICTION: AUC > 0.5 - deficient houses fall LESS, i.e. the fix")
    print("    is blunted. AUC crossing 0.5 means not shown.\n")

print("  continuous check, Spearman of deficiency against the change:")
for col in ["d_slope_pct", "d_level_pct"]:
    s = ch[["deficiency", col]].dropna()
    rho = s.corr(method="spearman").iloc[0, 1] if len(s) > 3 else np.nan
    print("    deficiency vs %-14s rho %+.3f  n=%d" % (col, rho, len(s)))

head("5. THE SAME TEST ON THE HOUSES WHOSE CURVE WAS LEFT ALONE")

un = un.copy()
if len(un) >= 8:
    un["def_grp"] = pd.qcut(un.deficiency, 2, labels=["low", "high"])
    for col in ["d_slope_pct", "d_level_pct"]:
        hi_g = un[un.def_grp == "high"][col].dropna()
        lo_g = un[un.def_grp == "low"][col].dropna()
        a, l, h = auc_ci(hi_g, lo_g)
        print("    %-14s AUC high-over-low %.3f [%.3f, %.3f]" % (col, a, l, h))
    print("\n  This is the FALSIFICATION arm. If deficient houses drift upward even")
    print("  when NOTHING was changed, then section 4 measures drift, not blunting.")
else:
    print("    n=%d - too few to run the falsification arm." % len(un))

head("6. WHAT THIS CAN AND CANNOT SHOW")

print("  n is small and the intervals will be wide. Report both halves, always.")
print("  A confirmed result would give S10's null a MECHANISM and would justify")
print("  routing category C differently from A on the dashboard.")
print("  A null result leaves the C split defensible on mechanism and unproven")
print("  on evidence - which is exactly what the CLAUDE.md already claims.")

D.to_parquet(DATA / "p7_compensation.parquet", index=False)
D.to_csv(DATA / "p7_compensation.csv", index=False, sep=";")
print("\n  written: p7_compensation.parquet, p7_compensation.csv")
print("\nP7 complete.")
