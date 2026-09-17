"""P15 - limitation 2, the design-load offset.

Our design load runs 1.13-1.49x the SIA 384.201 W/m2 table (P4). Spec v3 calls it an
installer safety margin (alpha = 1.25). REJECTED: installer oversizing is installed /
required; this offset is two calculations of REQUIRED load disagreeing, and 1.25 is
the midpoint of our own measured range.

P15 asks whether the offset is a CONVENTION mismatch. p_physics computes design load
with the ANNUAL-ENERGY conventions of SIA 380/1 (n = 0.7 1/h, b_ground = 0.5
unsourced). A design-load table is built with EN 12831 conventions. Cumulative steps,
each justified by a source and never by the result:

  S0  the live model, exactly as evaluate() computes design_kw
  S1  ventilation at EN 12831 minimum air change n_min = 0.5 1/h, habitable rooms
  S2  ground at EN 12831 f_g1 * f_g2, f_g2 = (T_set - T_me) / (T_set - T_design),
      T_me = the station's own annual mean temperature from the weather file
  D1  DIAGNOSTIC ONLY: transmission alone at S2 - how much of the load is ventilation

NOTHING HERE CHANGES p_physics. Weather only enters T_me; no consumption is read, so
the calibration rule is not engaged.

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
OUT = HERE / "outputs" / "p15"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

# SIA 384.201 W/m2 band midpoints, identical to P1 DESIGN_LOAD / P4 BENCH.
BENCH = {"pre1975": 60.0, "1976_1990": 45.0, "1991_2000": 35.0,
         "2001_2010": 32.5, "post2010": 25.0}
N_MIN_EN12831 = 0.5
F_G1_EN12831 = 1.45
T_SET, T_DESIGN = ph.value("t_set"), ph.value("t_design")


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


sys.stdout = Tee(LOGS / "p15_run.txt")

head("1. STATION CLIMATE - annual mean temperature over complete years")

w = pd.read_parquet(ROOT / "outputs/weather_daily.parquet",
                    columns=["Weather_ID", "date", "temp_mean", "full_day"])
w["year"] = pd.to_datetime(w.date).dt.year
yr = w[w.full_day & w.temp_mean.notna()].groupby(["Weather_ID", "year"]).temp_mean.agg(
    ["size", "mean"])
yr = yr[yr["size"] >= 360]
tme = yr.groupby("Weather_ID")["mean"].agg(["size", "mean"]).rename(
    columns={"size": "complete_years", "mean": "T_me"})
print(tme.round(2).to_string())

hw = pd.read_parquet(ROOT / "outputs/household_weather.parquet",
                     columns=["Household_ID", "Weather_ID"])
station = hw.groupby("Household_ID").Weather_ID.agg(lambda s: s.mode().iat[0])

head("2. THE OFFSET, STEP BY STEP")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)].copy()
M["Weather_ID"] = M.Household_ID.map(station)
M["T_me"] = M.Weather_ID.map(tme.T_me)
print("  modellable: %d   without a station T_me: %d" % (len(M), int(M.T_me.isna().sum())))
M["T_me"] = M.T_me.fillna(tme.T_me.mean())

sh, pf = ph.value("storey_height"), ph.value("perimeter_factor")


def w_per_m2(h, n_air, b_g, trans_only=False):
    per = 4.0 * np.sqrt(h["footprint_m2"]) * pf
    a_above = per * sh * h["n_storeys_above"] + h["footprint_m2"]
    a_ground = h["footprint_m2"] + (per * sh if h["heated_basement"] else 0.0)
    h_t = ph.u_as_built(h["era"], h["renovation_count"]) * (a_above + b_g * a_ground)
    h_v = 0.0 if trans_only else ph.ventilation_coefficient(
        h["area_m2"], n_air, ph.value("v_net_per_m2"), ph.value("rho_c"))
    return (h_t + h_v) * (T_SET - T_DESIGN) / h["area_m2"]


rows = []
for h in M.to_dict("records"):
    live = ph.evaluate(dict(h, hdd_per_day=1.0, n_days=10 ** 6))
    b_en = F_G1_EN12831 * (T_SET - h["T_me"]) / (T_SET - T_DESIGN)
    rows.append({"Household_ID": h["Household_ID"], "era": h["era"],
                 "renovated": h["renovation_count"] > 0, "area_m2": h["area_m2"],
                 "huellzahl": live["huellzahl"], "b_ground_en12831": b_en,
                 "live_W_m2": live["design_kw"] * 1000 / h["area_m2"],
                 "S0": w_per_m2(h, ph.value("n_air"), ph.value("b_ground")),
                 "S1": w_per_m2(h, N_MIN_EN12831, ph.value("b_ground")),
                 "S2": w_per_m2(h, N_MIN_EN12831, b_en),
                 "D1": w_per_m2(h, N_MIN_EN12831, b_en, trans_only=True)})
R = pd.DataFrame(rows)
R["bench"] = R.era.map(BENCH)
mism = (R.S0 - R.live_W_m2).abs().max()
print("  S0 reproduces evaluate() design_kw: max |diff| %.2e W/m2  %s"
      % (mism, "OK" if mism < 1e-9 else "MISMATCH - STOP"))
print("  EN 12831 b_ground (f_g1 x f_g2): median %.3f  range %.3f - %.3f   (live model 0.50)"
      % (R.b_ground_en12831.median(), R.b_ground_en12831.min(), R.b_ground_en12831.max()))
for s in ["S0", "S1", "S2", "D1"]:
    R["r_" + s] = R[s] / R.bench


def table(df, title):
    print("\n  %s" % title)
    print("  %-10s %4s %6s | %6s %6s | %6s %6s %6s | %6s"
          % ("era", "n", "bench", "S0 mn", "S0 md", "S1 md", "S2 md", "D1 md", "S2 W/m2"))
    spans = {s: [] for s in ["S0mn", "S0", "S1", "S2", "D1"]}
    for e in ph.ERA_ORDER:
        q = df[df.era == e]
        if len(q) < 5:
            print("  %-10s %4d  held out, n < 5" % (e, len(q)))
            continue
        vals = {"S0mn": q.r_S0.mean(), "S0": q.r_S0.median(), "S1": q.r_S1.median(),
                "S2": q.r_S2.median(), "D1": q.r_D1.median()}
        for k, v in vals.items():
            spans[k].append(v)
        print("  %-10s %4d %6.1f | %6.2f %6.2f | %6.2f %6.2f %6.2f | %6.1f"
              % (e, len(q), BENCH[e], vals["S0mn"], vals["S0"], vals["S1"], vals["S2"],
                 vals["D1"], q.S2.median()))
    print("  %-10s %4s %6s | %6s %6s | %6s %6s %6s"
          % ("range", "", "", *["%.2f" % (max(v) - min(v)) for v in spans.values()]))
    print("  %-10s %4s %6s | %6s %6s | %6s %6s %6s"
          % ("mid", "", "", *["%.2f" % np.median(v) for v in spans.values()]))


table(R, "ALL modellable households (ratio ours / SIA 384.201 midpoint)")
table(R[~R.renovated], "UNRENOVATED only - the table is for as-built stock")

head("3. WHAT REMAINS")

s2 = R.r_S2.median()
print("  fleet median ratio: S0 %.2f -> S1 %.2f -> S2 %.2f" %
      (R.r_S0.median(), R.r_S1.median(), s2))
print("  ventilation share of the S2 load: median %.0f%%"
      % (100 * (1 - R.D1 / R.S2).median()))
print("\n  UNRESOLVABLE FROM THE DATA: the area basis. SIA tables are per m2 of")
print("  Energiebezugsflaeche (gross, SIA 416). If HEAPO's heated area is a NET area,")
print("  our W/m2 is inflated by EBF/net. The factor that would close S2 is %.2f." % s2)
print("  That is WHAT IT WOULD TAKE, not a correction. Nothing is applied.")

R.to_parquet(DATA / "p15_design_load.parquet", index=False)
R.to_csv(DATA / "p15_design_load.csv", sep=";", index=False)
print("\n  written: p15_design_load")
