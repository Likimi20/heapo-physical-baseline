"""P4 - Category B, on real geometry and a fixed base. The first shippable numbers.

Everything P0-P3 settled, applied at once:

  base        FIXED HDD_12 (P0). The computed per-household balance temperature
              is DEAD - P3 measured corr(tau) = -0.066 with 45 distinct values,
              no better than the 5-value era lookup. Occupant behaviour dominates
              the envelope, and NREL UMP Ch.8 prescribes a fixed base exactly when
              change-point fits are noisy.
  geometry    audited per-storey areas, BASEMENT CORRECTED (P3 defect fixed here)
  huellzahl   geometric per household, never an era lookup (P3)
  U           TABULA era midpoints as-built; SIA 380/1 target 0.269 reference
  JAZ         field values; GSHP+radiator DERIVED, not the rejected 4.4 (P2)
  ranking     WITHIN ERA (P3) - a common inflation factor cannot reorder a list,
              but it can reorder a fleet-wide one.

BASEMENT FIX. P3 counted only above-ground storeys while the total area INCLUDED
the heated basement, so a bungalow-with-basement scored as one storey carrying two
storeys of area, and basement walls against earth were ignored entirely. Here:

  A_wall_above = 4*sqrt(footprint) * h * n_above
  A_wall_bsmt  = 4*sqrt(footprint) * h * 1        if heated basement, at b_ground
  A_roof       = footprint
  A_lowest     = footprint                        at b_ground
  A_th_eff     = A_wall_above + A_roof + b*(A_wall_bsmt + A_lowest)

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p4"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

U_ERA = {"< 1975": 1.35, "1976 - 80": 0.80, "1981 - 85": 0.80, "1986 - 90": 0.80,
         "1991 - 95": 0.55, "1995 - 00": 0.55, "2000 - 10": 0.40, "> 2010": 0.24}
U_REF = 0.269
BENCH = {"< 1975": 60, "1976 - 80": 45, "1981 - 85": 45, "1986 - 90": 45,
         "1991 - 95": 35, "1995 - 00": 35, "2000 - 10": 32.5, "> 2010": 25}
H_STOREY, B_GND = 2.70, 0.5
HV_PER_M2 = 0.34 * 0.7 * 2.05
T_SET, T_DESIGN = 20.0, -10.0
JAZ_ASHP = {"floor_only": 3.50, "radiator_only": 2.80, "both": 3.10}
GF = 4.25
JAZ_GSHP = {"floor_only": GF, "radiator_only": GF * 2.80 / 3.50,
            "both": GF * 3.10 / 3.50}
JAZ_DHW_HP, JAZ_DHW_ELEC = 2.30, 1.00
DHW_KWH_PD = 2.33
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


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    d = pos[:, None] - neg[None, :]
    return ((d > 0).sum() + 0.5 * (d == 0).sum()) / (len(pos) * len(neg))


def auc_ci(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) < 2 or len(neg) < 2:
        return auc(pos, neg), np.nan, np.nan
    b = [auc(RNG.choice(pos, len(pos), True), RNG.choice(neg, len(neg), True))
         for _ in range(NBOOT)]
    return auc(pos, neg), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


sys.stdout = Tee(LOGS / "p4_run.txt")

head("1. GEOMETRY, BASEMENT CORRECTED")

pr = pd.read_csv(ROOT / "heapo_data/reports/protocols.csv", sep=None,
                 engine="python")
pr["Household_ID"] = pr.Household_ID.astype("Int64")
hh = (pr[pr.Household_ID.notna()].sort_values("Visit_Date")
      .drop_duplicates("Household_ID", keep="first").copy())

S = {k: pd.to_numeric(hh["Building_FloorAreaHeated_" + k], errors="coerce")
     for k in ["Basement", "GroundFloor", "FirstFloor", "SecondFloor", "TopFloor"]}
hh["area"] = pd.to_numeric(hh.Building_FloorAreaHeated_Total, errors="coerce")
hh["residents"] = pd.to_numeric(hh.Building_Residents, errors="coerce")
hh["footprint"] = S["GroundFloor"]
hh["n_above"] = (pd.concat([S["GroundFloor"], S["FirstFloor"], S["SecondFloor"],
                            S["TopFloor"]], axis=1) > 0).sum(axis=1)
hh["bsmt"] = (S["Basement"] > 0).fillna(False)
hh["era"] = hh.Building_ConstructionYear_Interval
hh["hp_type"] = hh.HeatPump_Installation_Type
rad = hh.HeatDistribution_System_Radiators.fillna(False).astype(bool)
flo = hh.HeatDistribution_System_FloorHeating.fillna(False).astype(bool)
hh["emitter"] = np.select([flo & ~rad, rad & ~flo, rad & flo],
                          ["floor_only", "radiator_only", "both"], default=None)
hh["dhw_elec"] = hh.DHW_Production_ByElectricWaterHeater.fillna(False).astype(bool)
hh["installed_kW"] = pd.to_numeric(hh.HeatPump_Installation_HeatingCapacity,
                                   errors="coerce")

D = hh[hh.footprint.notna() & (hh.footprint > 0) & hh.area.notna()
       & (hh.n_above > 0) & hh.residents.notna() & hh.era.isin(U_ERA)
       & hh.hp_type.isin(["air-source", "ground-source"])
       & hh.emitter.notna()].copy()
print("  households carried forward : %d of %d" % (len(D), len(hh)))
print("  with a heated basement     : %d  (%.1f%%)"
      % (int(D.bsmt.sum()), 100 * D.bsmt.mean()))

per = 4 * np.sqrt(D.footprint)
D["A_wall_above"] = per * H_STOREY * D.n_above
D["A_wall_bsmt"] = np.where(D.bsmt, per * H_STOREY, 0.0)
D["A_roof"] = D.footprint
D["A_lowest"] = D.footprint
D["A_th"] = (D.A_wall_above + D.A_roof
             + B_GND * (D.A_wall_bsmt + D.A_lowest))
D["huell"] = D.A_th / D.area

print("\n  BASEMENT FIX - the P3 storey table read backwards. Now:")
D["storeys_eff"] = D.n_above + D.bsmt.astype(int)
for n in sorted(D.storeys_eff.unique()):
    s = D[D.storeys_eff == n]
    if len(s) >= 5:
        print("    %d heated storeys (incl basement)  n=%-4d median huellzahl %.2f"
              % (n, len(s), s.huell.median()))
print("  A bungalow must carry MORE envelope per heated m2 than a stacked house.")
print("  If this is still not monotonic, the geometry is still wrong - say so.")

print("\n  geometric huellzahl: median %.2f  IQR %.2f-%.2f  5-95%% %.2f-%.2f"
      % (D.huell.median(), D.huell.quantile(.25), D.huell.quantile(.75),
         D.huell.quantile(.05), D.huell.quantile(.95)))

head("2. HEAT LOSS AND THE DESIGN-LOAD CROSS-CHECK")

D["u"] = D.era.map(U_ERA)
D["H_as_built"] = D.u * D.A_th + HV_PER_M2 * D.area
D["H_reference"] = U_REF * D.A_th + HV_PER_M2 * D.area
D["Pdes_W_m2"] = D.H_as_built * (T_SET - T_DESIGN) / D.area
D["required_kW_phys"] = D.H_as_built * (T_SET - T_DESIGN) / 1000.0

print("  %-12s %5s %10s %10s %8s" % ("era", "n", "ours W/m2", "benchmark", "ratio"))
rr = []
for e in U_ERA:
    s = D[D.era == e]
    if len(s) >= 5:
        r = s.Pdes_W_m2.mean() / BENCH[e]
        rr.append(r)
        print("  %-12s %5d %10.1f %10.1f %8.2f"
              % (e, len(s), s.Pdes_W_m2.mean(), BENCH[e], r))
print("  spread of the ratio: %.2f - %.2f  (range %.2f)"
      % (min(rr), max(rr), max(rr) - min(rr)))
print("  P2 era lookup range 0.62; P3 geometry range 0.32.")

head("3. THE TWO BASELINES ON FIXED HDD_12")

D["jaz"] = [(JAZ_ASHP if t == "air-source" else JAZ_GSHP)[e]
            for t, e in zip(D.hp_type, D.emitter)]
D["jaz_ref"] = np.where(D.hp_type == "air-source", JAZ_ASHP["floor_only"],
                        JAZ_GSHP["floor_only"])
D["jaz_derived"] = (D.hp_type == "ground-source") & (D.emitter != "floor_only")

hw = pd.read_parquet(ROOT / "outputs/household_weather.parquet",
                     columns=["Household_ID", "date", "HDD_12"])
ds = pd.read_parquet(ROOT / "outputs/daily_states.parquet",
                     columns=["Household_ID", "date", "state_total", "kwh_total"])
pan = ds.merge(hw, on=["Household_ID", "date"], how="inner")
pan = pan[pan.state_total.isin(["NORMAL", "MIXED_ZERO"]) & pan.kwh_total.notna()
          & pan.HDD_12.notna()]
obs = pan.groupby("Household_ID").agg(n_days=("kwh_total", "size"),
                                      hdd12_pd=("HDD_12", "mean"),
                                      kwh_pd=("kwh_total", "mean")).reset_index()
D = D.merge(obs, on="Household_ID", how="left")
print("  with usable consumption days : %d of %d"
      % (int(D.n_days.notna().sum()), len(D)))

D["heat_ab"] = (D.H_as_built * 24 / 1000 / D.jaz) * D.hdd12_pd * 365
D["heat_rf"] = (D.H_reference * 24 / 1000 / D.jaz_ref) * D.hdd12_pd * 365
D["dhw_th"] = DHW_KWH_PD * D.residents * 365
D["dhw_ab"] = D.dhw_th / np.where(D.dhw_elec, JAZ_DHW_ELEC, JAZ_DHW_HP)
D["dhw_rf"] = D.dhw_th / JAZ_DHW_HP
D["E_as_built"] = D.heat_ab + D.dhw_ab
D["E_reference"] = D.heat_rf + D.dhw_rf
D["deficiency"] = D.E_as_built - D.E_reference

D["term_envelope"] = ((D.H_as_built - D.H_reference) * 24 / 1000 / D.jaz
                      * D.hdd12_pd * 365)
D["term_emitter"] = (D.H_reference * 24 / 1000 * (1 / D.jaz - 1 / D.jaz_ref)
                     * D.hdd12_pd * 365)
D["term_dhw"] = D.dhw_ab - D.dhw_rf
print("  decomposition residual: max |sum - total| = %.6f kWh"
      % (D.term_envelope + D.term_emitter + D.term_dhw - D.deficiency).abs().max())

v = D.dropna(subset=["deficiency"])
print("\n  annual kWh/yr, n=%d:" % len(v))
for c in ["E_as_built", "E_reference", "deficiency"]:
    print("    %-14s median %8.0f   IQR %7.0f - %8.0f"
          % (c, v[c].median(), v[c].quantile(.25), v[c].quantile(.75)))
print("\n  fleet total deficiency: %.0f kWh/yr" % v.deficiency.sum())
for t in ["term_envelope", "term_emitter", "term_dhw"]:
    print("    %-16s share of fleet total %5.1f%%   n>0 %3d"
          % (t, 100 * v[t].sum() / v.deficiency.sum(), int((v[t] > 1).sum())))

head("4. RANKED WITHIN ERA - the deliverable")

v = v.copy()
v["rank_in_era"] = v.groupby("era").deficiency.rank(ascending=False, method="min")
v["n_in_era"] = v.groupby("era").deficiency.transform("size")
v["pct_of_own_use"] = 100 * v.deficiency / v.E_as_built
print("  median deficiency and share of own consumption, by era:")
for e in U_ERA:
    s = v[v.era == e]
    if len(s) >= 5:
        print("    %-12s n=%-4d median %7.0f kWh/yr   %5.1f%% of own use"
              % (e, len(s), s.deficiency.median(), s.pct_of_own_use.median()))

print("\n  top 3 within each era:")
for e in U_ERA:
    s = v[v.era == e].nsmallest(3, "rank_in_era")
    if len(s) >= 3:
        ids = ", ".join("%d (%.0f kWh)" % (i, d)
                        for i, d in zip(s.Household_ID, s.deficiency))
        print("    %-12s %s" % (e, ids))

head("5. VALIDATION - physics-derived sizing against the inspector")

D["ratio_phys"] = D.installed_kW / D.required_kW_phys
D["logr"] = np.log(D.ratio_phys)
lab = D[D.HeatPump_Installation_CorrectlyPlanned.notna() & D.logr.notna()]
good = lab[lab.HeatPump_Installation_CorrectlyPlanned == True]
bad = lab[lab.HeatPump_Installation_CorrectlyPlanned == False]
ov = lab[lab.HeatPump_Installation_IncorrectlyPlanned_Categorization == "oversized"]
print("  P1 used the SIA 384.201 W/m2 benchmark for required capacity.")
print("  Here required capacity comes from OUR OWN physics: H_tot * 30 K.")
print("  Two independent routes to the same validation.\n")
print("  sizing ratio: median %.2f   IQR %.2f-%.2f"
      % (D.ratio_phys.median(), D.ratio_phys.quantile(.25),
         D.ratio_phys.quantile(.75)))
a, lo, hi = auc_ci(bad.logr.abs(), good.logr.abs())
print("  MISMATCH either direction : AUC %.3f [%.3f, %.3f]   n %d / %d"
      % (a, lo, hi, len(bad), len(good)))
a2, lo2, hi2 = auc_ci(ov.logr, good.logr)
print("  OVERSIZED                 : AUC %.3f [%.3f, %.3f]   n %d / %d"
      % (a2, lo2, hi2, len(ov), len(good)))
print("  P1 on the SIA benchmark had 0.685 and 0.772.")

head("6. SANITY")

D["kwh_yr"] = D.kwh_pd * 365
res = (D.kwh_yr - D.E_as_built).dropna()
print("  implied non-heating electricity (actual - E_as_built), kWh/yr:")
print("    median %6.0f   IQR %6.0f - %6.0f   5-95%% %7.0f - %7.0f"
      % (res.median(), res.quantile(.25), res.quantile(.75),
         res.quantile(.05), res.quantile(.95)))
print("    Swiss SFH non-heating consumption is ~3500-4500 kWh/yr.")
print("    P2 on the era lookup gave median 3052, 5-95%% -6555 to 11400.")

D.to_parquet(DATA / "p4_deficiency.parquet", index=False)
keep = ["Household_ID", "era", "area", "footprint", "n_above", "bsmt", "huell",
        "residents", "hp_type", "emitter", "jaz", "jaz_derived",
        "H_as_built", "H_reference", "required_kW_phys", "installed_kW",
        "ratio_phys", "E_as_built", "E_reference", "deficiency",
        "term_envelope", "term_emitter", "term_dhw", "kwh_yr"]
v_out = D[keep].copy()
v_out["rank_in_era"] = v_out.groupby("era").deficiency.rank(ascending=False,
                                                            method="min")
v_out.sort_values(["era", "rank_in_era"]).to_csv(
    DATA / "p4_category_b.csv", index=False, sep=";")
print("\n  written: p4_deficiency.parquet, p4_category_b.csv")
print("\nP4 complete.")
