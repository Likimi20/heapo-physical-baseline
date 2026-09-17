"""P1 - the capacity term: is the heat pump the right size for the building?

The lead signal for CATEGORY B. Miguel's example: "the heat pump is for small
houses and in the data it appears is a big one".

  required_kW  = design_load_W_per_m2(era, renovation) * heated_area / 1000
  installed_kW = HeatPump_Installation_HeatingCapacity
  sizing_ratio = installed / required

Design loads are SIA 384.201 / EN 12831 benchmarks at T_design = -10 C
(Zurich / Swiss plateau), supplied 2026-09-10. PENDING PAGE-LEVEL CITATION -
these are working constants and nothing ships on them until sourced properly.

VALIDATION, NOT INPUT. HeatPump_Installation_CorrectlyPlanned is the inspector's
verdict and is used ONLY to score. 212 of 214 answer it, 179 True / 33 False.
It is NOT one of Aaditya's top-three settings faults, so there is no collision,
and at a 15.6% base rate it is five times rarer than the 78.5% settings-fault
rate - rare enough that detecting it actually ranks something.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p1"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

NBOOT = 2000
RNG = np.random.default_rng(20260910)

# SIA 384.201 / EN 12831 specific design heat load, W/m2, T_design = -10 C.
# PENDING CITATION. Midpoint of the supplied band; band kept for the uncertainty
# propagation in a later rung.
DESIGN_LOAD = {
    "< 1975":    (50.0, 70.0),
    "1976 - 80": (40.0, 50.0),
    "1981 - 85": (40.0, 50.0),
    "1986 - 90": (40.0, 50.0),
    "1991 - 95": (30.0, 40.0),   # SIA 384.201 / SIA 380/1:1993, supplied v2
    "1995 - 00": (30.0, 40.0),
    "2000 - 10": (25.0, 40.0),
    "> 2010":    (20.0, 30.0),
}
INTERPOLATED = set()   # 1990s band resolved 2026-09-10 by spec v2

# A pre-1975 house with envelope work moves to the "partially renovated" band,
# which the source gives as 40-50 W/m2 - the same band as 1980s construction.
RENOVATED_BAND = (40.0, 50.0)


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


def auc(pos, neg):
    """Mann-Whitney AUC of pos over neg, ties at 0.5."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    d = pos[:, None] - neg[None, :]
    return ((d > 0).sum() + 0.5 * (d == 0).sum()) / (len(pos) * len(neg))


def auc_ci(pos, neg, nboot=NBOOT):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) < 2 or len(neg) < 2:
        return auc(pos, neg), np.nan, np.nan
    b = [auc(RNG.choice(pos, len(pos), True), RNG.choice(neg, len(neg), True))
         for _ in range(nboot)]
    return auc(pos, neg), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


sys.stdout = Tee(LOGS / "p1_run.txt")

head("1. POPULATION")

pr = pd.read_csv(ROOT / "heapo_data/reports/protocols.csv", sep=None,
                 engine="python")
pr["Household_ID"] = pr.Household_ID.astype("Int64")
hh = (pr[pr.Household_ID.notna()]
      .sort_values("Visit_Date")
      .drop_duplicates("Household_ID", keep="first")
      .copy())
print("  distinct protocol households : %d" % len(hh))

hh["area"] = pd.to_numeric(hh.Building_FloorAreaHeated_Total, errors="coerce")
hh["installed_kW"] = pd.to_numeric(hh.HeatPump_Installation_HeatingCapacity,
                                   errors="coerce")
hh["era"] = hh.Building_ConstructionYear_Interval
hh["n_renov"] = (hh.Building_Renovated_Windows.fillna(False).astype(bool).astype(int)
                 + hh.Building_Renovated_Walls.fillna(False).astype(bool).astype(int)
                 + hh.Building_Renovated_Roof.fillna(False).astype(bool).astype(int))

ok = hh.area.notna() & hh.installed_kW.notna() & hh.era.isin(DESIGN_LOAD)
W = hh[ok].copy()
print("  with area + capacity + era   : %d" % len(W))
print("  dropped: no area %d, no capacity %d, no era %d"
      % (int(hh.area.isna().sum()), int(hh.installed_kW.isna().sum()),
         int((~hh.era.isin(DESIGN_LOAD)).sum())))
print("\n  era distribution of the usable set:")
for e, n in W.era.value_counts().items():
    mark = "  <- INTERPOLATED design load" if e in INTERPOLATED else ""
    print("    %-12s %3d%s" % (e, n, mark))

head("2. REQUIRED VERSUS INSTALLED CAPACITY")


def band(row, renov_adjust):
    lo, hi = DESIGN_LOAD[row.era]
    if renov_adjust and row.era == "< 1975" and row.n_renov >= 1:
        lo, hi = RENOVATED_BAND
    return lo, hi


for tag, adj in [("era_only", False), ("renov_adj", True)]:
    lohi = W.apply(lambda r: band(r, adj), axis=1)
    W["load_lo_" + tag] = [x[0] for x in lohi]
    W["load_hi_" + tag] = [x[1] for x in lohi]
    W["load_mid_" + tag] = (W["load_lo_" + tag] + W["load_hi_" + tag]) / 2
    W["required_kW_" + tag] = W["load_mid_" + tag] * W.area / 1000.0
    W["ratio_" + tag] = W.installed_kW / W["required_kW_" + tag]
    W["logratio_" + tag] = np.log(W["ratio_" + tag])

W["installed_W_m2"] = W.installed_kW * 1000.0 / W.area

print("  installed capacity per m2 heated (W/m2):")
print("    %s" % W.installed_W_m2.describe(
    percentiles=[.05, .25, .5, .75, .95]).round(2).to_string().replace("\n", "\n    "))

for tag, name in [("era_only", "era only"), ("renov_adj", "renovation-adjusted")]:
    r = W["ratio_" + tag]
    print("\n  sizing ratio (installed / required), %s:" % name)
    print("    median %.2f   IQR %.2f-%.2f   5-95%% %.2f-%.2f"
          % (r.median(), r.quantile(.25), r.quantile(.75),
             r.quantile(.05), r.quantile(.95)))
    print("    ratio > 1.3 (oversized-looking)  : %3d  (%.1f%%)"
          % (int((r > 1.3).sum()), 100 * (r > 1.3).mean()))
    print("    ratio < 0.8 (undersized-looking) : %3d  (%.1f%%)"
          % (int((r < 0.8).sum()), 100 * (r < 0.8).mean()))

head("3. VALIDATION AGAINST THE INSPECTOR - LABEL ONLY, NEVER AN INPUT")

W["correct"] = W.HeatPump_Installation_CorrectlyPlanned
W["cat"] = W.HeatPump_Installation_IncorrectlyPlanned_Categorization
lab = W[W.correct.notna()].copy()
print("  households carrying the verdict : %d" % len(lab))
print("    correctly planned   : %d" % int((lab.correct == True).sum()))
print("    INcorrectly planned : %d" % int((lab.correct == False).sum()))
print("    of those: %s" % dict(lab[lab.correct == False].cat.value_counts(dropna=False)))

for tag, name in [("era_only", "era only"), ("renov_adj", "renovation-adjusted")]:
    print("\n  --- %s ---" % name)
    bad = lab[lab.correct == False]
    good = lab[lab.correct == True]

    a, lo, hi = auc_ci(bad["logratio_" + tag].abs().dropna(),
                       good["logratio_" + tag].abs().dropna())
    print("    MISMATCH in either direction  |log ratio|")
    print("      AUC %.3f  [%.3f, %.3f]   n %d bad / %d good"
          % (a, lo, hi, len(bad), len(good)))

    ov = lab[lab.cat == "oversized"]
    a2, lo2, hi2 = auc_ci(ov["logratio_" + tag].dropna(),
                          good["logratio_" + tag].dropna())
    print("    OVERSIZED, signed log ratio (higher = bigger pump)")
    print("      AUC %.3f  [%.3f, %.3f]   n %d vs %d"
          % (a2, lo2, hi2, len(ov), len(good)))

    un = lab[lab.cat == "undersized"]
    a3, lo3, hi3 = auc_ci(good["logratio_" + tag].dropna(),
                          un["logratio_" + tag].dropna())
    print("    UNDERSIZED, direction reversed (lower = smaller pump)")
    print("      AUC %.3f  [%.3f, %.3f]   n %d vs %d   <- n=%d, underpowered"
          % (a3, lo3, hi3, len(un), len(good), len(un)))

    print("    group medians of the sizing ratio:")
    for g, sub in [("correctly planned", good), ("oversized", ov),
                   ("undersized", un)]:
        if len(sub):
            print("      %-20s n=%-4d median ratio %.2f"
                  % (g, len(sub), sub["ratio_" + tag].median()))

head("4. WHAT THE INSPECTOR CALLS OVERSIZED VERSUS WHAT THE PHYSICS DOES")

t = lab.groupby(lab.cat.fillna("(correctly planned)"))["ratio_era_only"].agg(
    ["count", "median", "min", "max"]).round(2)
print(t.to_string())

W.to_parquet(DATA / "p1_sizing.parquet", index=False)
lab.to_csv(DATA / "p1_sizing_validation.csv", index=False, sep=";")
print("\n  written: p1_sizing.parquet, p1_sizing_validation.csv")

print("\nP1 complete.")
