"""P14 - limitation 1, "levels are not predictions".

E_as_built omits all non-heat-pump electricity, so E_actual - E_as_built was always
dominated by appliances (P13: median 6,045 kWh/yr). P14 adds a SOURCED appliance
term - BFE/EnergieSchweiz Faktenblatt 08.2021, single-family house, excluding the
heat pump and electric DHW - and asks two questions of the meter:

  TEST 1  SUB-METER. Total - HeatPump is measured non-heat-pump electricity. Does
          the appliance term (plus electric DHW where present) predict it?
          Needs only residents and DHW source, so NOT restricted to modellable.

  TEST 2  THE LEVEL, LIKE-FOR-LIKE. Predicted kWh/day on the household's own
          recorded days (raw mean HDD of those days, so no annualisation and no
          HDD correction) against measured kWh/day. With and without appliances.
          Per m2 as well as raw - both scale with house size (P9 rule).

PV True is excluded from every headline: Total is grid import, not consumption.
All meter days are used - this is VALIDATION, not categorisation.

NOTHING HERE IS TUNED. The constants stay as they are whatever this run says.

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
OUT = HERE / "outputs" / "p14"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

MIN_DAYS, MIN_WARM, MIN_COLD = 180, 60, 60
MIN_PAIRED = 180
NDRAW = 400
NBOOT = 2000
RNG = np.random.default_rng(20260911)
RNG_APPL = np.random.default_rng(20260912)
RNG_BOOT = np.random.default_rng(20260913)
USABLE = ["NORMAL", "MIXED_ZERO"]


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


def spear(a, b):
    s = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(s) < 4:
        return np.nan, np.nan, np.nan, len(s)
    r = s.corr(method="spearman").iloc[0, 1]
    boot = [pd.DataFrame(s.values[RNG_BOOT.integers(0, len(s), len(s))],
                         columns=["a", "b"]).corr(method="spearman").iloc[0, 1]
            for _ in range(NBOOT)]
    return r, float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5)), len(s)


def pv_level(v):
    return "True" if v is True or v == True else ("False" if v is False or v == False else "Unknown")


sys.stdout = Tee(LOGS / "p14_run.txt")

head("1. THE SOURCE - BFE/EnergieSchweiz Faktenblatt 08.2021, Tabelle 1")

print("  EFH, 2019 data. EXCLUDES heat pump, electric heating, electric DHW.")
print("  4 persons 4,048 kWh/yr, +/- 593.5 per person, -50 per person from five.")
print("  Band hi = S.A.F.E./Nipkow 2013 (2011 data). No household spread is published.\n")
print("  residents   point      lo      hi")
for n in range(1, 9):
    lo = ph.band("appl_efh_4p")[0] + (np.where(n > 4, ph.band("appl_efh_per_person")[0] - 50,
                                               ph.band("appl_efh_per_person")[0])) * (n - 4)
    hi = ph.band("appl_efh_4p")[1] + (np.where(n > 4, ph.band("appl_efh_per_person")[1] - 50,
                                               ph.band("appl_efh_per_person")[1])) * (n - 4)
    print("  %9d  %6.0f  %6.0f  %6.0f" % (n, ph.appliance_electricity(n), min(lo, hi), max(lo, hi)))

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
H["pv_level"] = H.pv.map(pv_level)
print("\n  building type, all 214 (the source is for single-family houses):")
print(H.building_type.value_counts(dropna=False).to_string())

head("2. TEST 1 - SUB-METER: measured non-heat-pump electricity")

ds = pd.read_parquet(ROOT / "outputs/daily_states.parquet",
                     columns=["Household_ID", "date", "state_total", "state_hp",
                              "kwh_total", "kwh_hp"])
ds = ds[ds.Household_ID.isin(H.Household_ID)]
pd_ = ds[ds.state_total.isin(USABLE) & ds.state_hp.isin(USABLE)
         & ds.kwh_total.notna() & ds.kwh_hp.notna()].copy()
pd_["other"] = pd_.kwh_total - pd_.kwh_hp
g = pd_.groupby("Household_ID")
S = pd.DataFrame({"n_paired": g.size(), "other_per_day": g.other.mean(),
                  "neg_other_days": g.other.apply(lambda s: int((s < 0).sum()))}).reset_index()
print("  protocol households with any paired Total+HeatPump day: %d" % len(S))
S = S[S.n_paired >= MIN_PAIRED].merge(
    H[["Household_ID", "residents", "dhw_electric", "pv_level", "building_type"]],
    on="Household_ID", how="left")
S = S[S.residents.notna()].copy()
print("  with >= %d paired days and residents recorded: %d" % (MIN_PAIRED, len(S)))
print("  days with Total < HeatPump (negative 'other'): %d" % int(S.neg_other_days.sum()))

kpd = ph.value("dhw_kwh_person_day")
S["measured_other_kwh_yr"] = S.other_per_day * 365
S["pred_appliance"] = [float(ph.appliance_electricity(r)) for r in S.residents]
S["pred_dhw_electric"] = np.where(S.dhw_electric,
                                  ph.dhw_electricity(S.residents, 1.0, kpd), 0.0)
S["pred_other_kwh_yr"] = S.pred_appliance + S.pred_dhw_electric
draws = np.array([[float(ph.appliance_electricity(r, RNG_APPL))
                   + (ph.dhw_electricity(r, 1.0, ph.sample("dhw_kwh_person_day", RNG_APPL))
                      if e else 0.0)
                   for r, e in zip(S.residents, S.dhw_electric)] for _ in range(NDRAW)])
S["pred_other_lo"], S["pred_other_hi"] = np.percentile(draws, [2.5, 97.5], axis=0)
S["ratio_meas_pred"] = S.measured_other_kwh_yr / S.pred_other_kwh_yr
S["inside_band"] = S.measured_other_kwh_yr.between(S.pred_other_lo, S.pred_other_hi)
cols = ["Household_ID", "residents", "dhw_electric", "pv_level", "n_paired",
        "measured_other_kwh_yr", "pred_other_kwh_yr", "pred_other_lo", "pred_other_hi",
        "ratio_meas_pred", "inside_band"]
print()
print(S[cols].sort_values(["pv_level", "residents"]).round(2).to_string(index=False))

for name, sub in [("PV False", S[S.pv_level == "False"]),
                  ("PV False + Unknown", S[S.pv_level != "True"]),
                  ("PV True (grid import - biased low)", S[S.pv_level == "True"])]:
    if len(sub) == 0:
        continue
    r, lo, hi, n = spear(sub.pred_other_kwh_yr, sub.measured_other_kwh_yr)
    print("\n  %-36s n=%2d  median meas/pred %.2f  inside band %d/%d"
          % (name, len(sub), sub.ratio_meas_pred.median(), int(sub.inside_band.sum()), len(sub)))
    print("  %-36s       Spearman pred vs meas %+.3f [%+.3f, %+.3f]" % ("", r, lo, hi))
    print("  %-36s       measured 5-95%% %.0f - %.0f   predicted %.0f - %.0f"
          % ("", sub.measured_other_kwh_yr.quantile(.05), sub.measured_other_kwh_yr.quantile(.95),
             sub.pred_other_kwh_yr.quantile(.05), sub.pred_other_kwh_yr.quantile(.95)))

head("3. TEST 2 - THE LEVEL, like-for-like on each household's own recorded days")

obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
M = H[modellable(H)]
A = M.merge(obs[(obs.n_days >= MIN_DAYS) & (obs.n_warm >= MIN_WARM)
                & (obs.n_cold >= MIN_COLD)], on="Household_ID")
print("  modellable and >= %d/%d/%d: %d" % (MIN_DAYS, MIN_WARM, MIN_COLD, len(A)))


def per_day(e, h, appl):
    heat = e["H_as_built"] * 24 / 1000 / e["jaz_as_built"] * h["hdd_per_day"]
    dhw = (e["E_as_built"] - ph.heating_electricity(e["H_as_built"], e["jaz_as_built"],
                                                   e["hdd_corrected"])) / 365
    return heat, dhw, appl / 365


rows = []
for h in A.to_dict("records"):
    heat, dhw, ap = per_day(ph.evaluate(h), h, float(ph.appliance_electricity(h["residents"])))
    tot = np.empty(NDRAW)
    for k in range(NDRAW):
        hk, dk, ak = per_day(ph.evaluate(h, RNG), h,
                             float(ph.appliance_electricity(h["residents"], RNG_APPL)))
        tot[k] = hk + dk + ak
    rows.append({"Household_ID": h["Household_ID"], "era": h["era"], "area_m2": h["area_m2"],
                 "residents": h["residents"], "pv_level": h["pv_level"],
                 "n_days": h["n_days"], "hdd_per_day_raw": h["hdd_per_day"],
                 "meas_kwh_day": h["kwh_per_day"],
                 "pred_heat_kwh_day": heat, "pred_dhw_kwh_day": dhw, "pred_appl_kwh_day": ap,
                 "pred_noappl_kwh_day": heat + dhw, "pred_kwh_day": heat + dhw + ap,
                 "pred_lo_kwh_day": np.percentile(tot, 2.5),
                 "pred_hi_kwh_day": np.percentile(tot, 97.5)})
L = pd.DataFrame(rows)
L["resid_noappl_kwh_yr"] = (L.meas_kwh_day - L.pred_noappl_kwh_day) * 365
L["resid_kwh_yr"] = (L.meas_kwh_day - L.pred_kwh_day) * 365
L["ratio_meas_pred"] = L.meas_kwh_day / L.pred_kwh_day
L["inside_band"] = L.meas_kwh_day.between(L.pred_lo_kwh_day, L.pred_hi_kwh_day)
L["above_band"] = L.meas_kwh_day > L.pred_hi_kwh_day
L["band_rel_width"] = (L.pred_hi_kwh_day - L.pred_lo_kwh_day) / L.pred_kwh_day

print("\n  pv_level counts: %s" % L.pv_level.value_counts().to_dict())
for name, sub in [("PV False (headline)", L[L.pv_level == "False"]),
                  ("PV Unknown", L[L.pv_level == "Unknown"]),
                  ("PV True (grid import - biased low)", L[L.pv_level == "True"])]:
    print("\n  %s, n=%d" % (name, len(sub)))
    print("    residual WITHOUT appliances  median %6.0f   5-95%% %6.0f - %6.0f kWh/yr"
          % (sub.resid_noappl_kwh_yr.median(), sub.resid_noappl_kwh_yr.quantile(.05),
             sub.resid_noappl_kwh_yr.quantile(.95)))
    print("    residual WITH appliances     median %6.0f   5-95%% %6.0f - %6.0f kWh/yr"
          % (sub.resid_kwh_yr.median(), sub.resid_kwh_yr.quantile(.05),
             sub.resid_kwh_yr.quantile(.95)))
    print("    measured / predicted         median %.2f   IQR %.2f - %.2f"
          % (sub.ratio_meas_pred.median(), sub.ratio_meas_pred.quantile(.25),
             sub.ratio_meas_pred.quantile(.75)))
    print("    inside band %d  above %d  below %d   median band width %.0f%% of prediction"
          % (int(sub.inside_band.sum()), int(sub.above_band.sum()),
             int((~sub.inside_band & ~sub.above_band).sum()), 100 * sub.band_rel_width.median()))

C = L[L.pv_level == "False"]
r, lo, hi, n = spear(C.pred_kwh_day, C.meas_kwh_day)
print("\n  PV False  Spearman raw   pred vs meas  %+.3f [%+.3f, %+.3f]  n=%d" % (r, lo, hi, n))
r, lo, hi, n = spear(C.pred_kwh_day / C.area_m2, C.meas_kwh_day / C.area_m2)
print("  PV False  Spearman per m2 pred vs meas  %+.3f [%+.3f, %+.3f]  n=%d" % (r, lo, hi, n))
r, lo, hi, n = spear(C.area_m2, C.meas_kwh_day)
print("  PV False  Spearman area alone vs meas   %+.3f [%+.3f, %+.3f]  n=%d" % (r, lo, hi, n))

print("\n  PV False, by era: median measured / predicted")
print(C.groupby("era").ratio_meas_pred.agg(["size", "median"]).reindex(ph.ERA_ORDER)
      .round(2).to_string())
print("\n  PV False, by residents: median residual WITH appliances, kWh/yr")
print(C.groupby(C.residents.clip(upper=5)).resid_kwh_yr.agg(["size", "median"])
      .round(0).to_string())
print("\n  share of the predicted level that is appliances (PV False): median %.0f%%"
      % (100 * (C.pred_appl_kwh_day / C.pred_kwh_day).median()))

for df, name in [(S, "p14_submeter_other"), (L, "p14_level_check")]:
    df.to_parquet(DATA / (name + ".parquet"), index=False)
    df.to_csv(DATA / (name + ".csv"), sep=";", index=False)
print("\n  written: %s, %s" % ("p14_submeter_other", "p14_level_check"))
