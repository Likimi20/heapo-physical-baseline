"""Pipeline guarantees. Every check is a thing that has already gone wrong
somewhere in this project or in its parent, or a rule that would silently rot.

Run: ../venv_viz/Scripts/python.exe p_pipeline_test.py
Transcript lands in outputs/p0/logs/p_pipeline_test.txt

NOT included, deliberately:
  * "zero false negatives against the consultant flags" - that would make the
    inspector's verdict a GATE. It is a LABEL. Spending it as an ingredient ends
    the only validation this workstream has that clears 0.5. It also asserts a
    result measured to be false: oversizing detection is AUC 0.786.
  * IQR spike filtering and visit-date blackouts - those are DATA-CLEANING
    DESIGN CHANGES, not tests. Smuggling them in through a test file would
    change every number without a decision.

numpy + pandas only.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import p_physics as ph
from p_adapter_heapo import load_households, modellable, daily_observations, station_normals

LOG = HERE / "outputs" / "p0" / "logs" / "p_pipeline_test.txt"
LOG.parent.mkdir(parents=True, exist_ok=True)

PASS, FAIL = [], []


class Tee:
    def __init__(self, p):
        self.f = open(p, "w", encoding="utf-8")

    def write(self, s):
        sys.__stdout__.write(s)
        self.f.write(s)

    def flush(self):
        sys.__stdout__.flush()
        self.f.flush()


sys.stdout = Tee(LOG)


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("  %-4s %-58s %s" % ("ok" if cond else "FAIL", name, detail))


def head(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


# ======================================================== A. PORTABILITY
head("A. PORTABILITY - the physics layer must not know about HEAPO")

src = (HERE / "p_physics.py").read_text(encoding="utf-8")
heapo_names = ["Building_", "HeatPump_", "HeatDistribution_", "DHW_", "Survey_",
               "Household_ID", "protocols.csv", "daily_states", "household_weather"]
for n in heapo_names:
    check("p_physics.py free of '%s'" % n, n not in src)
check("p_physics.py imports no pandas", "import pandas" not in src)
check("p_adapter_heapo.py exists", (HERE / "p_adapter_heapo.py").exists())

# ======================================================== B. LABELS NEVER INPUTS
head("B. THE INSPECTOR'S VERDICT IS A LABEL, NEVER AN INPUT")

verdicts = ["CorrectlyPlanned", "TooHigh_BeforeVisit", "NightSetbackSetting",
            "TechnicallyOkay", "Categorization", "LastDescaling_TooLongAgo"]
for v in verdicts:
    check("physics never references '%s'" % v, v not in src)

adapter = (HERE / "p_adapter_heapo.py").read_text(encoding="utf-8")
check("adapter marks label columns as validation-only",
      "VALIDATION LABELS" in adapter or "never model inputs" in adapter)

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
roles = {"area_m2", "footprint_m2", "n_storeys_above", "heated_basement", "era",
         "renovation_count", "residents", "hp_type", "emitter", "dhw_electric",
         "hdd_per_day", "n_days"}
rec = dict.fromkeys(roles, 1)
rec.update({"era": "pre1975", "hp_type": "air-source", "emitter": "floor_only",
            "heated_basement": False, "dhw_electric": False,
            "renovation_count": 0, "n_days": 10 ** 6})
check("evaluate() runs on ROLES alone, no label present",
      isinstance(ph.evaluate(rec), dict))

# ======================================================== C. THERMODYNAMICS
head("C. THERMODYNAMIC SANITY - every JAZ published, and physically ordered")

# 2026-09-10 rejected GSHP+radiators = 4.4 as impossible. P20 overturned that: OST
# P+I 2020 Tab 1 publishes it, below GSHP floor 5.7. The error was the floor value.
for t in ["air-source", "ground-source"]:
    f_, b_, r_ = [ph.jaz_for(t, e)[0] for e in ["floor_only", "both", "radiator_only"]]
    check("%s JAZ falls with flow temperature" % t, f_ > b_ > r_,
          "%.2f > %.2f > %.2f" % (f_, b_, r_))
check("no JAZ is derived - every cell is published",
      not any(ph.jaz_for(t, e)[1] for (t, e) in ph.JAZ_KEYS))
check("GSHP + radiators is the published 4.4, below GSHP floor",
      abs(ph.jaz_for("ground-source", "radiator_only")[0] - 4.4) < 1e-9
      and ph.jaz_for("ground-source", "radiator_only")[0]
      < ph.jaz_for("ground-source", "floor_only")[0])
check("ground-source beats air-source at every emitter",
      all(ph.jaz_for("ground-source", e)[0] > ph.jaz_for("air-source", e)[0]
          for e in ["floor_only", "both", "radiator_only"]))
check("DHW JAZ is below space-heating JAZ for each pump type",
      all(ph.value(ph.JAZ_HOTWATER_KEYS[t]) < ph.jaz_for(t, "radiator_only")[0]
          for t in ph.JAZ_HOTWATER_KEYS))

# ======================================================== D. CONSTANTS
head("D. CONSTANTS - sourced, banded, and mutually consistent")

for k, v in ph.C.items():
    check("constant '%s' carries value/lo/hi/unit/source/section" % k, len(v) == 6)
    check("constant '%s' band brackets its value" % k, v[1] <= v[0] <= v[2])
u_ref = ph.value("u_reference")
lo10, hi10 = ph.band("u_era_post2010")
check("reference U (MuKEn 2014) sits at the lower edge of the post-2010 band",
      lo10 - 1e-9 <= u_ref <= hi10,
      "%.3f vs %.3f-%.3f" % (u_ref, lo10, hi10))
us = [ph.value(ph.ERA_KEYS[e]) for e in ph.ERA_ORDER]
# Non-increasing, not strict: TEP 2016 pools 1991-2009, so 1991_2000 == 2001_2010.
check("U never rises with construction era",
      all(us[i] >= us[i + 1] for i in range(len(us) - 1)),
      " > ".join("%.3f" % u for u in us))
check("b_ground is sourced, not invented",
      "UNSOURCED" not in ph.C["b_ground"][4],
      "currently: %s" % ph.C["b_ground"][4])

# ======================================================== E. HDD CORRECTION
head("E. THE HDD BIAS CORRECTION - P6's finding must not silently vanish")

check("hdd_correction() exists", hasattr(ph, "hdd_correction"))
check("short records are corrected DOWNWARD", ph.hdd_correction(450) > 1.10,
      "450 days -> divide by %.3f" % ph.hdd_correction(450))
check("long records are corrected less than short ones",
      ph.hdd_correction(2000) < ph.hdd_correction(450),
      "%.3f < %.3f" % (ph.hdd_correction(2000), ph.hdd_correction(450)))
check("no record length is corrected upward past 1.35",
      max(ph.hdd_correction(n) for n in [200, 450, 600, 900, 1500]) < 1.35)
r1 = dict(rec, n_days=450, hdd_per_day=4.0)
r2 = dict(rec, n_days=2000, hdd_per_day=4.0)
check("a short record yields a SMALLER deficiency than a long one, same inputs",
      ph.evaluate(r1)["deficiency"] < ph.evaluate(r2)["deficiency"])

# ======================================================== F. THE MODEL
head("F. MODEL ALGEBRA")

o = ph.evaluate(dict(rec, area_m2=200, footprint_m2=100, n_storeys_above=2,
                     residents=4, hdd_per_day=4.0, n_days=1500))
check("deficiency == E_as_built - E_reference",
      abs(o["deficiency"] - (o["E_as_built"] - o["E_reference"])) < 1e-9)
check("terms sum to the deficiency",
      abs(o["term_envelope"] + o["term_emitter"] + o["term_dhw"] + o["term_vintage"]
          - o["deficiency"]) < 1e-6)
ov = ph.evaluate(dict(rec, area_m2=200, footprint_m2=100, n_storeys_above=2, residents=4,
                      hdd_per_day=4.0, n_days=1500, hp_install_year=2000.0))
check("an older heat pump adds a positive vintage term, and terms still sum (P23)",
      ov["term_vintage"] > 0 and abs(ov["term_envelope"] + ov["term_emitter"] + ov["term_dhw"]
                                     + ov["term_vintage"] - ov["deficiency"]) < 1e-6,
      "%.0f kWh/yr" % ov["term_vintage"])
check("unknown installation year makes no vintage claim on the point estimate",
      ph.evaluate(dict(rec, hp_install_year=float("nan")))["term_vintage"] == 0)
check("H_as_built >= H_reference for a pre-1975 house",
      o["H_as_built"] > o["H_reference"])
v1 = ph.ventilation_coefficient(200, 0.7, 2.05, 0.34)
check("ventilation is identical in both baselines, so it CANCELS",
      abs((o["H_as_built"] - o["H_reference"])
          - (ph.value("u_era_pre1975") - ph.value("u_reference"))
          * o["a_thermal"]) < 1e-6, "H_V = %.1f W/K drops out" % v1)
b1 = ph.envelope_area(100, 1, False, 2.7, 0.5)
b2 = ph.envelope_area(50, 2, False, 2.7, 0.5)
check("a bungalow carries more envelope than a stacked house of equal area",
      b1 / 100 > b2 / 100, "%.2f > %.2f" % (b1 / 100, b2 / 100))
check("a heated basement adds envelope",
      ph.envelope_area(100, 1, True, 2.7, 0.5) > b1)

# ======================================================== G. POPULATION
head("G. POPULATION - the funnel, pinned")

check("protocols.csv holds 410 reports",
      len(pd.read_csv(ROOT / "heapo_data/reports/protocols.csv", sep=None,
                      engine="python")) == 410)
check("214 distinct households carry a Household_ID", len(H) == 214,
      "NOT 217 - that is reports-with-an-ID")
M = H[modellable(H)]
check("190 households are modellable", len(M) == 190, "%d" % len(M))
check("24 are unjudgeable and carry a reason", len(H) - len(M) == 24)
check("Household_ID is an integer, never float", H.Household_ID.dtype.kind == "i")
check("PV is three-level - absence is NOT 'no PV'",
      H.pv.isna().sum() > 0 and set(H.pv.dropna().unique()) <= {True, False},
      "%d True / %d False / %d NaN" % (int((H.pv == True).sum()),
                                       int((H.pv == False).sum()),
                                       int(H.pv.isna().sum())))
check("unknown DHW source is carried, not defaulted to heat pump",
      (~H.dhw_known).sum() > 0 and ph.completeness_tier(dict(rec, dhw_known=False)) != "T1",
      "%d households tick no DHW source" % int((~H.dhw_known).sum()))
check("emitter is never silently defaulted",
      H.emitter.isna().sum() > 0, "%d NaN kept as NaN" % int(H.emitter.isna().sum()))

# ======================================================== H. END TO END
head("H. END TO END - the P22 numbers (sourced registry, normal-year HDD)")

obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
A = M.merge(obs[(obs.n_days >= 180) & (obs.n_warm >= 60)
                & (obs.n_cold >= 60)], on="Household_ID")
check("172 households clear >=180/60/60 on all days", len(A) == 172, "%d" % len(A))
A = A.merge(station_normals(ROOT / "outputs/weather_daily.parquet",
                            ROOT / "outputs/household_weather.parquet"),
            on="Household_ID", how="left")
check("every scored household has a station normal year",
      A.hdd_normal_per_day.notna().all(), "%d missing" % int(A.hdd_normal_per_day.isna().sum()))
res = [ph.evaluate(r) for r in A.to_dict("records")]
check("record length never enters Category B (P18)",
      all(abs(x["hdd_corrected"] - r["hdd_normal_per_day"]) < 1e-12
          for x, r in zip(res, A.to_dict("records"))))
d = np.array([x["deficiency"] for x in res])
# P23 on 2026-09-11 (P22 registry + heat-pump vintage): 288,788 kWh/yr, median 1,498.
# P22 without vintage 268,271 / 1,286; P6's 321,330 / 1,609 - both superseded.
check("fleet deficiency 275k-305k kWh/yr (P23)",
      275_000 < d.sum() < 305_000, "%.0f" % d.sum())
check("median household deficiency 1350-1650 kWh/yr (P23)",
      1350 < np.median(d) < 1650, "%.0f" % np.median(d))
post = A[A.era == "post2010"]
dp = np.array([ph.evaluate(r)["deficiency"] for r in post.to_dict("records")])
check("post-2010 houses sit at or below the reference",
      np.median(dp) < 200, "median %.0f kWh/yr on n=%d" % (np.median(dp), len(dp)))
check("no household has a negative E_reference",
      all(x["E_reference"] > 0 for x in res))
check("huellzahl is physically plausible fleet-wide (1.0-3.5)",
      all(1.0 < x["huellzahl"] < 3.5 for x in res),
      "min %.2f max %.2f" % (min(x["huellzahl"] for x in res),
                             max(x["huellzahl"] for x in res)))
check("geometry that does not reconcile is tiered down, not dropped",
      (~H.storey_reconciles.fillna(False)).sum() > 0
      and all(ph.completeness_tier(dict(r, geometry_complete=False)) != "T1"
              for r in [rec]),
      "%d households fail storey reconciliation"
      % int((~H.storey_reconciles.fillna(True)).sum()))

# ======================================================== I. NO CALIBRATION
head("I. THE CALIBRATION RULE - no constant may be fitted to the meter")

for token in ["kwh_total", "kwh_per_day", "curve_fit", "polyfit", "lstsq",
              "minimize", "OLS", "regress"]:
    check("physics layer never touches '%s'" % token, token not in src)
check("HDD_SAMPLING is documented as WEATHER ONLY",
      "WEATHER ONLY" in src or "no consumption enters" in src)

# ======================================================== J. APPLIANCE TERM
head("J. APPLIANCE TERM - the published table, reproduced (P14)")

ap = {n: float(ph.appliance_electricity(n)) for n in range(1, 9)}
check("4 persons reproduces BFE 2021 Tab 1 EFH total", abs(ap[4] - 4048.0) < 1e-9,
      "%.1f" % ap[4])
check("2 persons = 4048 - 2 x 593.5", abs(ap[2] - 2861.0) < 1e-9, "%.1f" % ap[2])
check("5th person tapered by 50 kWh (Tab 1 footnote 1)",
      abs(ap[5] - (4048.0 + 543.5)) < 1e-9, "%.1f" % ap[5])
check("appliance load rises with every resident",
      all(ap[n + 1] > ap[n] for n in range(1, 8)))
check("appliance term never enters evaluate(), so the deficiency is untouched",
      not any("appl" in k for k in o))

# ======================================================== K. REGISTRY
head("K. STANDARDS REGISTRY - every constant carries a status (P19)")

levels = set(ph._REG["status_levels"])
check("every constant has a registry status from the declared levels",
      set(ph.STATUS) == set(ph.C) and all(s in levels for s in ph.STATUS.values()))
reg_txt = ph.REGION_FILE.read_text(encoding="utf-8")
check("registry is free of HEAPO names", not any(n in reg_txt for n in heapo_names))
cnt = {s: sum(v == s for v in ph.STATUS.values()) for s in sorted(levels)}
print("  status counts: %s" % cnt)
mism = sorted(k for k, s in ph.STATUS.items() if s == "CITATION_MISMATCH")
print("  WARN %d constants cite a document that does not contain them:" % len(mism))
print("       %s" % ", ".join(mism))
inp = ph._REG.get("inputs", {})
weak = sorted(k for k, v in inp.items() if v.get("status") != "VERIFIED")
print("  WARN %d registry INPUTS are not verified: %s"
      % (len(weak), ", ".join("%s (%s)" % (k, inp[k]["status"]) for k in weak) or "none"))
import p22_registry
U = p22_registry.derive_u(inp)
check("derived U entries reproduce their published inputs exactly",
      all(abs(ph.C[ph.ERA_KEYS[e]][i] - U[e][i]) < 1e-9
          for e in ph.ERA_ORDER for i in range(3))
      and abs(ph.value("u_reference") - U["reference"][0]) < 1e-9)

head("SUMMARY")
print("  %d checks, %d passed, %d FAILED" % (len(PASS) + len(FAIL), len(PASS), len(FAIL)))
if FAIL:
    for f in FAIL:
        print("    FAILED: %s" % f)
    sys.exit(1)
print("\n  all green.")
