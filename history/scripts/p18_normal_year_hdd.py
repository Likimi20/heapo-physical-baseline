"""P18 - limitation 5, short records.

Category B never reads the meter, yet its degree-days come from the household's own
meter days: hdd_per_day is averaged over usable meter days, then corrected for record
length by P6's HDD_SAMPLING bins. Below 365 days that correction is EXTRAPOLATED.

Spec v3 proposes a PRISM change-point fit projected onto a typical year, with
u ~ 1/sqrt(N). Wrong tool here: a fit reads the meter, and Category B must not.

P18 removes the dependence instead. Each household gets its STATION'S normal-year
HDD_12: the mean annual HDD_12 over the complete years in the weather file. Weather
only. Record length no longer enters Category B at all.

The deficiency is linear in HDD for the heating terms and independent of it for DHW,
so it is rescaled exactly from evaluate()'s own terms. Nothing in p_physics changes.

Declared: the "normal" is the 2019-2024 record-period mean at each station (3-5
complete years), NOT a 20-year climate normal. Year-to-year spread is reported.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph
from p_adapter_heapo import load_households, modellable, daily_observations

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p18"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

MIN_DAYS, MIN_WARM, MIN_COLD = 180, 60, 60
BINS = [0, 365, 548, 730, 1095, 10 ** 9]


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


sys.stdout = Tee(LOGS / "p18_run.txt")

head("1. STATION NORMAL-YEAR HDD_12 - complete years only")

w = pd.read_parquet(ROOT / "outputs/weather_daily.parquet",
                    columns=["Weather_ID", "date", "HDD_12", "full_day"])
w["year"] = pd.to_datetime(w.date).dt.year
yr = w[w.full_day & w.HDD_12.notna()].groupby(["Weather_ID", "year"]).HDD_12.agg(
    ["size", "sum"])
yr = yr[yr["size"] >= 360]
yr["annual"] = yr["sum"] * 365 / yr["size"]
N = yr.groupby("Weather_ID").annual.agg(["size", "mean", "std", "min", "max"])
N.columns = ["complete_years", "normal_hdd_yr", "sd_between_years", "min_year", "max_year"]
N["cv"] = N.sd_between_years / N.normal_hdd_yr
print(N.round(1).to_string())
print("\n  year-to-year CV, median over stations: %.1f%%" % (100 * N.cv.median()))

hw = pd.read_parquet(ROOT / "outputs/household_weather.parquet",
                     columns=["Household_ID", "Weather_ID"])
station = hw.groupby("Household_ID").Weather_ID.agg(lambda s: s.mode().iat[0])

head("2. CATEGORY B ON NORMAL-YEAR HDD versus the P6 record-length correction")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)]
obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
A = M.merge(obs[(obs.n_days >= MIN_DAYS) & (obs.n_warm >= MIN_WARM)
                & (obs.n_cold >= MIN_COLD)], on="Household_ID")
A["Weather_ID"] = A.Household_ID.map(station)
A["normal_hdd_day"] = A.Weather_ID.map(N.normal_hdd_yr) / 365
print("  households: %d (P6: 172)   without a station normal: %d"
      % (len(A), int(A.normal_hdd_day.isna().sum())))

rows = []
for h in A.to_dict("records"):
    e = ph.evaluate(h)
    heat = e["term_envelope"] + e["term_emitter"]
    scale = h["normal_hdd_day"] / e["hdd_corrected"]
    rows.append({"Household_ID": h["Household_ID"], "era": h["era"], "n_days": h["n_days"],
                 "Weather_ID": h["Weather_ID"], "hdd_raw_day": h["hdd_per_day"],
                 "hdd_p6_day": e["hdd_corrected"], "hdd_normal_day": h["normal_hdd_day"],
                 "def_p6": e["deficiency"], "def_normal": heat * scale + e["term_dhw"],
                 "env_p6": e["term_envelope"], "env_normal": e["term_envelope"] * scale})
R = pd.DataFrame(rows)
R["bin"] = pd.cut(R.n_days, BINS, right=True,
                  labels=["<365", "365-548", "548-730", "730-1095", "1095+"])
R["raw_over_normal"] = R.hdd_raw_day / R.hdd_normal_day
R["p6_over_normal"] = R.hdd_p6_day / R.hdd_normal_day
R["def_ratio"] = R.def_normal / R.def_p6

print("\n  fleet deficiency: P6 route %.0f   normal-year %.0f kWh/yr   (%+.1f%%)"
      % (R.def_p6.sum(), R.def_normal.sum(), 100 * (R.def_normal.sum() / R.def_p6.sum() - 1)))
print("  median household: P6 %.0f   normal-year %.0f" % (R.def_p6.median(),
                                                         R.def_normal.median()))
print("  Spearman of the deficiency, fleet: %.4f" % R[["def_p6", "def_normal"]].corr(
    method="spearman").iloc[0, 1])
wr = [R[R.era == e][["def_p6", "def_normal"]].corr(method="spearman").iloc[0, 1]
      for e in ph.ERA_ORDER]
print("  Spearman within era: %s" % "  ".join("%s %.3f" % (e, r) for e, r in
                                              zip(ph.ERA_ORDER, wr)))

print("\n  by record length - raw HDD over normal is the P6 bias, measured again:")
print("  %-9s %4s | %10s %10s | %8s | %s"
      % ("days", "n", "raw/norm", "P6/norm", "def n/P6", "P6 bin median it replaces"))
p6 = {"<365": "extrapolated 1.252", "365-548": "1.252", "548-730": "0.956",
      "730-1095": "1.112", "1095+": "1.077"}
for b in R.bin.cat.categories:
    q = R[R.bin == b]
    if len(q):
        print("  %-9s %4d | %10.3f %10.3f | %8.3f | %s"
              % (b, len(q), q.raw_over_normal.median(), q.p6_over_normal.median(),
                 q.def_ratio.median(), p6[b]))

print("\n  897731 (212 days, flagged in P6 as extrapolated):")
print(R[R.Household_ID == 897731][["n_days", "hdd_raw_day", "hdd_p6_day", "hdd_normal_day",
                                   "def_p6", "def_normal"]].round(2).to_string(index=False))

head("3. THE RANKED QUEUE - does anything move?")

R["rank_p6"] = R.groupby("era").def_p6.rank(ascending=False)
R["rank_normal"] = R.groupby("era").def_normal.rank(ascending=False)
top = lambda col: set(R[R.groupby("era")[col].rank(ascending=False)
                        <= np.ceil(R.groupby("era")[col].transform("size") * 0.25)].Household_ID)
t6, tn = top("def_p6"), top("def_normal")
print("  worst quartile within era: P6 %d, normal-year %d, shared %d, in/out %d/%d"
      % (len(t6), len(tn), len(t6 & tn), len(tn - t6), len(t6 - tn)))
print("  max |rank change| within era: %d" % int((R.rank_p6 - R.rank_normal).abs().max()))

R.to_parquet(DATA / "p18_normal_year.parquet", index=False)
R.to_csv(DATA / "p18_normal_year.csv", sep=";", index=False)
N.to_csv(DATA / "p18_station_normals.csv", sep=";")
print("\n  written: p18_normal_year, p18_station_normals")
