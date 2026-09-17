"""P3 - real building geometry instead of an era lookup.

Miguel, 2026-09-10: "the level means how much space they need to heat and also
that is not the same, a house with ground first second and top floor level than
one with only ground."

Correct, and it diagnoses P2's failure F2. A 200 m2 bungalow and a 200 m2
four-storey house have the same heated area and NOT the same envelope: the
bungalow carries about four times the roof and four times the ground contact.
That ratio IS the Gebaeudehuellzahl, and P2 assigned it BY ERA - so it had no
within-era variation, so T_bal had none either, so T_bal correlated -0.016 with
the fitted changepoint.

Geometry is not an era property. protocols.csv records floor area PER STOREY and
it reconciles to the total at median ratio 1.000 (190 of 193 within 5%).

  footprint  = ground floor area
  n_above    = storeys above ground carrying heated area
  A_wall     = 4 * sqrt(footprint) * h_storey * n_above     (square plan =
               MINIMUM perimeter, so this is a LOWER BOUND on wall area)
  A_roof     = footprint
  A_ground   = footprint, weighted by b (reduced dT against ground)
  A_th       = A_wall + A_roof + b * A_ground
  huellzahl  = A_th / A_E

Then two tests P2 failed, re-run:
  (1) does T_bal now correlate with the fitted changepoint?
  (2) does the pre-1975 design-load gap of 1.59 close?

NOTHING IS TUNED. The geometry comes from the audit, the constants from the
standards, and both tests are validations against quantities never fed in.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p3"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

U_ERA = {"< 1975": 1.35, "1976 - 80": 0.80, "1981 - 85": 0.80, "1986 - 90": 0.80,
         "1991 - 95": 0.55, "1995 - 00": 0.55, "2000 - 10": 0.40, "> 2010": 0.24}
HUELL_SIA = {"< 1975": 2.00, "1976 - 80": 1.65, "1981 - 85": 1.65,
             "1986 - 90": 1.65, "1991 - 95": 1.65, "1995 - 00": 1.65,
             "2000 - 10": 1.40, "> 2010": 1.40}
BENCH = {"< 1975": 60, "1976 - 80": 45, "1981 - 85": 45, "1986 - 90": 45,
         "1991 - 95": 35, "1995 - 00": 35, "2000 - 10": 32.5, "> 2010": 25}

H_STOREY = 2.70          # SIA 416:2003 gross storey height
HV_PER_M2 = 0.34 * 0.7 * 2.05
Q_INT = 5.0
T_SET, T_DESIGN = 20.0, -10.0
B_GROUND = 0.5           # temperature-reduction factor against ground.
B_ALT = 1.0              # UNSOURCED - both are run.


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


sys.stdout = Tee(LOGS / "p3_run.txt")

head("1. GEOMETRY FROM THE AUDIT")

pr = pd.read_csv(ROOT / "heapo_data/reports/protocols.csv", sep=None,
                 engine="python")
pr["Household_ID"] = pr.Household_ID.astype("Int64")
hh = (pr[pr.Household_ID.notna()].sort_values("Visit_Date")
      .drop_duplicates("Household_ID", keep="first").copy())

S = {k: pd.to_numeric(hh["Building_FloorAreaHeated_" + k], errors="coerce")
     for k in ["Basement", "GroundFloor", "FirstFloor", "SecondFloor", "TopFloor"]}
hh["area"] = pd.to_numeric(hh.Building_FloorAreaHeated_Total, errors="coerce")
hh["footprint"] = S["GroundFloor"]
above = pd.concat([S["GroundFloor"], S["FirstFloor"], S["SecondFloor"],
                   S["TopFloor"]], axis=1)
hh["n_above"] = (above > 0).sum(axis=1)
hh["has_basement"] = (S["Basement"] > 0).fillna(False)
hh["era"] = hh.Building_ConstructionYear_Interval

G = hh[hh.footprint.notna() & (hh.footprint > 0) & hh.area.notna()
       & (hh.n_above > 0) & hh.era.isin(U_ERA)].copy()
print("  households with a usable footprint + era : %d of %d" % (len(G), len(hh)))
print("  storeys above ground: %s" % dict(G.n_above.value_counts().sort_index()))
print("  with a heated basement : %d" % int(G.has_basement.sum()))

G["A_wall"] = 4 * np.sqrt(G.footprint) * H_STOREY * G.n_above
G["A_roof"] = G.footprint
G["A_ground"] = G.footprint
for tag, b in [("b05", B_GROUND), ("b10", B_ALT)]:
    G["A_th_" + tag] = G.A_wall + G.A_roof + b * G.A_ground
    G["huell_" + tag] = G["A_th_" + tag] / G.area

print("\n  A_wall uses a SQUARE plan = MINIMUM perimeter, so wall area and every")
print("  quantity built on it is a LOWER BOUND. A real elongated plan has 5-15%")
print("  more wall. Declared, not corrected.")

head("2. GEOMETRIC HUELLZAHL VERSUS THE SIA ERA LOOKUP")

G["huell_sia"] = G.era.map(HUELL_SIA)
print("  geometric (b=0.5): median %.2f   IQR %.2f-%.2f   5-95%% %.2f-%.2f"
      % (G.huell_b05.median(), G.huell_b05.quantile(.25), G.huell_b05.quantile(.75),
         G.huell_b05.quantile(.05), G.huell_b05.quantile(.95)))
print("  SIA era lookup   : median %.2f   (only %d distinct values)"
      % (G.huell_sia.median(), G.huell_sia.nunique()))

print("\n  BY NUMBER OF STOREYS - this is Miguel's point, measured:")
for n in sorted(G.n_above.unique()):
    s = G[G.n_above == n]
    print("    %d storey  n=%-4d median huellzahl %.2f   median area %5.0f m2"
          % (n, len(s), s.huell_b05.median(), s.area.median()))
print("  A bungalow carries far more envelope per heated m2 than a stacked house.")
print("  An era lookup cannot see this at all.")

print("\n  WITHIN-ERA SPREAD of the geometric huellzahl - what the lookup destroys:")
for e in U_ERA:
    s = G[G.era == e]
    if len(s) >= 5:
        print("    %-12s n=%-4d median %.2f   5-95%% %.2f - %.2f   SIA says %.2f"
              % (e, len(s), s.huell_b05.median(), s.huell_b05.quantile(.05),
                 s.huell_b05.quantile(.95), HUELL_SIA[e]))

head("3. HEAT LOSS AND BALANCE TEMPERATURE, ON REAL GEOMETRY")

G["u"] = G.era.map(U_ERA)
for tag in ["b05", "b10", "sia"]:
    hz = G["huell_" + tag] if tag != "sia" else G.huell_sia
    G["H_" + tag] = G.u * hz * G.area + HV_PER_M2 * G.area
    G["Tbal_" + tag] = T_SET - (Q_INT * G.area) / G["H_" + tag]
    G["Pdes_" + tag] = G["H_" + tag] * (T_SET - T_DESIGN) / G.area

print("  T_bal, computed not fitted:")
for tag, name in [("sia", "SIA era lookup (P2)"), ("b05", "real geometry b=0.5"),
                  ("b10", "real geometry b=1.0")]:
    s = G["Tbal_" + tag]
    print("    %-24s median %.1f C   5-95%% %.1f - %.1f   distinct %d"
          % (name, s.median(), s.quantile(.05), s.quantile(.95),
             s.round(1).nunique()))

head("4. TEST 1 - DOES T_bal NOW TRACK THE FITTED CHANGEPOINT?")

cp = pd.read_parquet(ROOT / "outputs/changepoint_indicator.parquet")
cp = cp[cp.qualifies == True][["Household_ID", "tau"]]
M = G.merge(cp, on="Household_ID", how="inner")
print("  households with a qualifying fit : %d" % len(M))
print("  fitted tau: median %.1f C   5-95%% %.1f - %.1f"
      % (M.tau.median(), M.tau.quantile(.05), M.tau.quantile(.95)))
print("\n  %-24s %8s %8s %10s" % ("balance temperature", "median", "d median", "corr(tau)"))
for tag, name in [("sia", "SIA era lookup (P2)"), ("b05", "real geometry b=0.5"),
                  ("b10", "real geometry b=1.0")]:
    c = M["Tbal_" + tag].corr(M.tau)
    print("  %-24s %8.1f %8.1f %10.3f"
          % (name, M["Tbal_" + tag].median(),
             (M["Tbal_" + tag] - M.tau).median(), c))
print("\n  P2 measured -0.016 on the era lookup. If real geometry does not move")
print("  this, the balance-temperature route fails for a reason other than")
print("  geometry, and the fixed HDD_12 from P0 stands.")

head("5. TEST 2 - DOES THE PRE-1975 DESIGN-LOAD GAP CLOSE?")

print("  ours = H_tot * 30 / area, versus the SIA 384.201 midpoint")
print("  %-12s %5s %10s %10s %10s %9s"
      % ("era", "n", "SIA-lookup", "geom b=0.5", "benchmark", "ratio b05"))
for e in U_ERA:
    s = G[G.era == e]
    if len(s) >= 5:
        print("  %-12s %5d %10.1f %10.1f %10.1f %9.2f"
              % (e, len(s), s.Pdes_sia.mean(), s.Pdes_b05.mean(),
                 BENCH[e], s.Pdes_b05.mean() / BENCH[e]))
print("\n  P2 had pre-1975 at ratio 1.59 on the era lookup.")

head("6. WITHIN-ERA VERSUS ACROSS-ERA RANKING")

print("  Miguel, 2026-09-10: the pre-1975 inconsistency matters less because we")
print("  are comparing. That is TRUE WITHIN AN ERA and FALSE ACROSS ERAS.")
print()
print("  If every pre-1975 house is inflated by the same factor, their order")
print("  among themselves is untouched - a common factor cannot reorder a list.")
print("  But a single fleet-wide ranked list puts inflated pre-1975 houses above")
print("  correctly-scaled modern ones that may waste more.")
print()
print("  So: RANK WITHIN ERA is safe under the P2 F1 defect.")
print("      ONE FLEET-WIDE LIST is not, until the 1.59 is resolved.")

G.to_parquet(DATA / "p3_geometry.parquet", index=False)
keep = ["Household_ID", "era", "area", "footprint", "n_above", "has_basement",
        "A_wall", "A_roof", "huell_b05", "huell_sia", "H_b05", "H_sia",
        "Tbal_b05", "Tbal_sia", "Pdes_b05", "Pdes_sia"]
G[keep].to_csv(DATA / "p3_geometry.csv", index=False, sep=";")
print("\n  written: p3_geometry.parquet, p3_geometry.csv")
print("\nP3 complete.")
