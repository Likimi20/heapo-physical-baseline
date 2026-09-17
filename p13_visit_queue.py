"""P13 - the visit queue: heating the building does not justify. OUR AXIS ONLY.

REVISED 2026-09-11 (P22), applying Miguel's decisions:

  * the measured slope is fitted with a FREE heating-season step (P17). A straight line
    through the step absorbed it as extra slope and produced the '~22% baseline'.
  * status comes from a 95% BAND on the slope excess - month-block bootstrap on the meter
    (daily data are autocorrelated) x Monte Carlo over the published constants.
    SLOPE_EXCESS only when the whole band is above zero; INCONCLUSIVE when it straddles;
    USES_LESS_THAN_MODELLED when it is below. P13 v1 used the point estimate.
  * POST-VISIT days only for the meter fit - the CLAUDE.md rule for the meter axis
    (recency and non-circularity), which v1 did not apply.
  * annualised on the station NORMAL-YEAR HDD (P18), not on the household's record.
  * ranked within era on the band's LOWER bound - "at least this much".
  * physics from the P22 registry (TEP 2016 U, OST/RISE JAZ, thermal bridges, ...).

AADITYA'S FAULT MODEL IS OUT OF THIS STAGE (Miguel 2026-09-12). It belongs to his own
section of the project and dashboard. **The two models are not combined here at all** -
they meet only in a final target overview, at the end, where each keeps its own column.
Removed with it: the fault probability, the named fault, the night-setback advisory and
the training-set flag. Nothing in this workstream loads `models.joblib` any more.

The step absorbs a heating-curve OFFSET as well as the building's balance point, so the
slope excess here measures curve STEEPNESS; the step ships as a measured column, never
judged (P17). No probability x kWh anywhere; the two kWh columns are never summed.

v1 outputs are archived in history/outputs/p13_v1/.
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
from p_adapter_heapo import load_households, modellable, station_normals

OUT = HERE / "outputs" / "p13"
for d in [OUT / "data", OUT / "logs", OUT / "figures", OUT / "reports"]:
    d.mkdir(parents=True, exist_ok=True)

MIN_DAYS, MIN_WARM, MIN_COLD = 180, 60, 60
NREP = 200
RNG_BOOT = np.random.default_rng(20260915)
RNG_MC = np.random.default_rng(20260916)


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


def fit_step(x, y, months):
    """floor + slope * HDD + free step * 1{HDD > 0}; month-block bootstrap on the slope."""
    s = (x > 0).astype(float)
    a, b, c = ols(np.column_stack([np.ones(len(x)), x, s]), y)
    um = np.unique(months)
    idx = {m: np.flatnonzero(months == m) for m in um}
    boot = []
    for _ in range(NREP):
        take = np.concatenate([idx[m] for m in RNG_BOOT.choice(um, len(um), replace=True)])
        xs, ys = x[take], y[take]
        ss = (xs > 0).astype(float)
        if (ss == 0).sum() < 5 or (ss == 1).sum() < 5:
            continue
        boot.append(ols(np.column_stack([np.ones(len(xs)), xs, ss]), ys)[1])
    return a, b, c, np.array(boot)


sys.stdout = Tee(OUT / "logs" / "p13_run.txt")

head("1. THE MEASURED SLOPE - post-visit days, free heating-season step")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)].copy()
ds = pd.read_parquet(ROOT / "outputs/daily_states.parquet",
                     columns=["Household_ID", "date", "state_total", "kwh_total"])
hw = pd.read_parquet(ROOT / "outputs/household_weather.parquet",
                     columns=["Household_ID", "date", "HDD_12"])
p = ds.merge(hw, on=["Household_ID", "date"], how="inner")
p = p[p.state_total.isin(["NORMAL", "MIXED_ZERO"]) & p.kwh_total.notna()
      & p.HDD_12.notna()]
p = p.merge(M[["Household_ID", "visit_date"]], on="Household_ID", how="inner")
n_all = p.groupby("Household_ID").size()
p = p[p.visit_date.notna() & (pd.to_datetime(p.date) > p.visit_date)].copy()
p["month"] = pd.to_datetime(p.date).dt.to_period("M")

rows, boots = [], {}
for hid, g in p.groupby("Household_ID"):
    n, w, c = len(g), int((g.HDD_12 == 0).sum()), int((g.HDD_12 > 0).sum())
    if n < MIN_DAYS or w < MIN_WARM or c < MIN_COLD:
        continue
    a, b, st, bt = fit_step(g.HDD_12.to_numpy(float), g.kwh_total.to_numpy(float),
                            g.month.to_numpy())
    rows.append({"Household_ID": hid, "n_days": n, "beta_meas": b, "step_kwh_day": st,
                 "floor_meas": a})
    boots[hid] = bt
F = pd.DataFrame(rows)
print("  modellable households with any usable day      : %d" % len(n_all))
print("  ... sufficient on POST-VISIT days (>=%d/%d/%d)   : %d   (v1, all days: 172)"
      % (MIN_DAYS, MIN_WARM, MIN_COLD, len(F)))

head("2. THE PHYSICAL SLOPE - P22 registry, station normal-year HDD")

NRM = station_normals(ROOT / "outputs/weather_daily.parquet",
                      ROOT / "outputs/household_weather.parquet")
D = M.merge(F, on="Household_ID", how="inner").merge(NRM, on="Household_ID", how="left")
print("  households with both slopes: %d   without a station normal: %d"
      % (len(D), int(D.hdd_normal_per_day.isna().sum())))
recs = D.to_dict("records")
ev = [ph.evaluate(r) for r in recs]
D["beta_phys"] = [e["H_as_built"] * 24 / 1000 / e["jaz_as_built"] for e in ev]
D["hdd_annual"] = [e["hdd_corrected"] * 365 for e in ev]
D["deficiency"] = [e["deficiency"] for e in ev]
D["E_as_built"] = [e["E_as_built"] for e in ev]
lo_, hi_ = [], []
for r in recs:
    bp = np.array([(lambda e: e["H_as_built"] * 24 / 1000 / e["jaz_as_built"])(
        ph.evaluate(r, RNG_MC)) for _ in range(NREP)])
    bm = boots[r["Household_ID"]]
    k = min(len(bm), len(bp))
    ha = ph.evaluate(r)["hdd_corrected"] * 365
    diff = (bm[:k] - bp[:k]) * ha
    lo, hi = np.percentile(diff, [2.5, 97.5])
    lo_.append(lo)
    hi_.append(hi)
D["slope_excess_kwh"] = (D.beta_meas - D.beta_phys) * D.hdd_annual
D["slope_excess_lo_kwh"], D["slope_excess_hi_kwh"] = lo_, hi_
D["slope_excess_pct"] = 100 * (D.beta_meas - D.beta_phys) / D.beta_phys
print("  physics / measured slope, median: %.3f" % (D.beta_phys / D.beta_meas).median())
print("  slope excess kWh/yr: median %.0f   band width median %.0f"
      % (D.slope_excess_kwh.median(), (D.slope_excess_hi_kwh - D.slope_excess_lo_kwh).median()))

head("3. THE VISIT QUEUE")

Q = D.copy()
Q["technician_recoverable_envelope_kwh"] = Q.slope_excess_kwh.round(0)
Q["not_recoverable_by_visit_kwh"] = Q.deficiency.round(0)
Q["visit_status"] = np.select(
    [Q.slope_excess_lo_kwh.isna(), Q.slope_excess_lo_kwh > 0, Q.slope_excess_hi_kwh < 0],
    ["NOT_ASSESSABLE", "SLOPE_EXCESS", "USES_LESS_THAN_MODELLED"], default="INCONCLUSIVE")
Q["rank_in_era"] = Q[Q.visit_status == "SLOPE_EXCESS"].groupby(
    "era").slope_excess_lo_kwh.rank(ascending=False, method="min")

print("  %s" % dict(Q.visit_status.value_counts()))
print("\n  SLOPE_EXCESS   whole band above physics -> ranked within era on the LOWER bound")
print("  INCONCLUSIVE   band straddles zero. NO CLAIM.")
print("  USES_LESS_THAN_MODELLED  whole band below physics")
V1 = pd.read_parquet(HERE / "history/outputs/p13_v1/p13_visit_queue.parquet")
s1 = set(V1[V1.visit_status == "SLOPE_EXCESS"].Household_ID)
s2 = set(Q[Q.visit_status == "SLOPE_EXCESS"].Household_ID)
print("\n  v1 SLOPE_EXCESS %d (point, all days)  ->  v2 %d (band, post-visit)   kept %d, new %d"
      % (len(s1), len(s2), len(s1 & s2), len(s2 - s1)))

se = Q[Q.visit_status == "SLOPE_EXCESS"]
print("\n  TOP OF THE QUEUE - lower bound of the slope excess (n=%d ranked):" % len(se))
top = se.nlargest(12, "slope_excess_lo_kwh")
print("  %-9s %-10s %9s %8s %10s %9s"
      % ("house", "era", "at least", "point", "band hi", "NOT rec"))
for _, r in top.iterrows():
    print("  %-9d %-10s %9.0f %8.0f %10.0f %9.0f"
          % (r.Household_ID, r.era, r.slope_excess_lo_kwh,
             r.technician_recoverable_envelope_kwh, r.slope_excess_hi_kwh,
             r.not_recoverable_by_visit_kwh))
print("  THE TWO kWh COLUMNS ARE NEVER SUMMED.")

head("4. WHAT THIS QUEUE IS AND IS NOT")

print("  IS      heating the building does not justify, confirmed by a band, on post-visit")
print("          days, with the builder's figure alongside.")
print("  IS NOT  a fault verdict - Aaditya's model is not loaded here at all (2026-09-12).")
print("          The two models meet only in a final target overview, each in its own column.")
print("  IS NOT  an expected saving - no probability x kWh anywhere.")
print("  IS NOT  a verdict on a curve OFFSET - that sits in the step column, unjudged.")

keep = ["Household_ID", "era", "visit_status", "technician_recoverable_envelope_kwh",
        "slope_excess_lo_kwh", "slope_excess_hi_kwh", "not_recoverable_by_visit_kwh",
        "slope_excess_pct", "step_kwh_day", "rank_in_era", "beta_meas", "beta_phys",
        "n_days"]
Q[keep].to_csv(OUT / "data" / "p13_visit_queue.csv", index=False, sep=";")
Q.to_parquet(OUT / "data" / "p13_visit_queue.parquet", index=False)
print("\n  written: p13_visit_queue.csv / .parquet")
print("\nP13 complete.")
