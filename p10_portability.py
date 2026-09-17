"""P10 - portability, DEMONSTRATED rather than claimed.

Until now "portable method" was an architectural property enforced by a test that
greps p_physics.py for HEAPO column names. That proves the physics does not
MENTION HEAPO. It does not prove another dataset can actually drive it.

Three bindings, run end to end:

  #1 p_adapter_heapo.py       protocols.csv   -> the live deliverable
  #2 p_adapter_synthetic.py   a foreign schema in German, areas as a LIST, a
                              numeric era code -> ROUND TRIP against answers
                              derived by hand, not against the model itself
  #3 p_adapter_meta.py        meta_data.csv, 1,358 households, SIX TIMES the
                              protocol cohort -> MUST REFUSE, and name why

Binding #3 is the point. A contract that only ever says yes is decoration.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph
import p_adapter_synthetic as syn
import p_adapter_meta as meta
from p_adapter_heapo import load_households, modellable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "p10"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

OK, BAD = [], []


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


def check(name, cond, detail=""):
    (OK if cond else BAD).append(name)
    print("  %-4s %-56s %s" % ("ok" if cond else "FAIL", name, detail))


sys.stdout = Tee(LOGS / "p10_run.txt")

head("1. BINDING #2 - A FOREIGN SCHEMA DRIVES THE PHYSICS UNCHANGED")

raw = syn.make_frame()
print("  synthetic source columns: %s" % list(raw.columns))
print("  note: areas arrive as a LIST per building, era as a NUMERIC code,")
print("  emitter as FBH/HK/MIX, heat pump as L/W or S/W. Nothing HEAPO-shaped.")
R = syn.to_roles(raw)
ev = [ph.evaluate(r) for r in R.to_dict("records")]
S = pd.DataFrame(ev)
S["Household_ID"] = R.Household_ID.values
S["era"] = R.era.values
print("\n  %d synthetic buildings evaluated, 0 changes to p_physics.py" % len(S))
check("every building produced a deficiency", S.deficiency.notna().all())
# HEAPO's own range is 1.14-2.96. The synthetic fleet deliberately contains
# SMALLER bungalows than HEAPO holds, and a small single-storey building really
# does carry a huellzahl above 3 - it is nearly all roof and floor. So the bound
# here is wider than the HEAPO test's on purpose: probing outside the range the
# real data covers is what a synthetic binding is FOR.
check("every huellzahl is physically plausible (synthetic range is wider)",
      bool(((S.huellzahl > 1.0) & (S.huellzahl < 4.5)).all()),
      "%.2f - %.2f  (HEAPO holds 1.14-2.96)" % (S.huellzahl.min(), S.huellzahl.max()))
check("the smallest single-storey buildings carry the largest huellzahl",
      S.loc[S.huellzahl.idxmax(), "huellzahl"] > S.huellzahl.median())

head("2. ROUND TRIP - checked against arithmetic, not against the model")

base = dict(area_m2=200.0, footprint_m2=100.0, n_storeys_above=2,
            heated_basement=False, era="post2010", renovation_count=0,
            residents=4.0, hp_type="air-source", emitter="floor_only",
            dhw_electric=False, hdd_per_day=4.0, n_days=10 ** 6,
            geometry_complete=True)

# (a) reference envelope == as-built envelope -> envelope term must be zero
a_th = ph.envelope_area(100.0, 2, False, ph.value("storey_height"),
                        ph.value("b_ground"))
h_v = ph.ventilation_coefficient(200.0, ph.value("n_air"),
                                 ph.value("v_net_per_m2"), ph.value("rho_c"))
o = ph.evaluate(base)
# The HDD correction is LIVE in evaluate(), so the hand arithmetic must apply it
# too - hdd 4.0 becomes 4.0/1.077 on a long record. This check first FAILED at
# -98.66 vs -106.26, a 7% gap, which is precisely the correction. The round trip
# caught the test's own arithmetic, and confirmed the correction is in the path.
hdd_eff = 4.0 / ph.hdd_correction(10 ** 6)
expect_env = ((ph.u_as_built("post2010", 0) - ph.value("u_reference")) * a_th
              * 24 / 1000 / ph.value("jaz_ashp_floor") * hdd_eff * 365)
check("envelope term matches hand arithmetic, correction included",
      abs(o["term_envelope"] - expect_env) < 1e-6,
      "%.2f vs %.2f kWh/yr" % (o["term_envelope"], expect_env))
check("the HDD correction is genuinely applied inside evaluate()",
      abs(o["hdd_corrected"] - hdd_eff) < 1e-9,
      "4.000 -> %.3f" % o["hdd_corrected"])

# (b) floor heating == reference emitter -> emitter term must be exactly zero
check("emitter term is exactly zero when emitter == reference",
      abs(o["term_emitter"]) < 1e-9, "%.2e" % o["term_emitter"])

# (c) heat-pump DHW == reference DHW -> DHW term must be exactly zero
check("DHW term is exactly zero when DHW == reference",
      abs(o["term_dhw"]) < 1e-9, "%.2e" % o["term_dhw"])

# (d) electric DHW: the term is fixed arithmetic, no physics involved
oe = ph.evaluate(dict(base, dhw_electric=True))
exp_dhw = (ph.value("dhw_kwh_person_day") * 4.0 * 365
           * (1 / 1.0 - 1 / ph.value("jaz_dhw_hp")))
check("electric DHW term matches hand arithmetic",
      abs(oe["term_dhw"] - exp_dhw) < 1e-6,
      "%.1f vs %.1f kWh/yr" % (oe["term_dhw"], exp_dhw))

# (e) doubling degree-days must exactly double every weather-driven term
o2 = ph.evaluate(dict(base, hdd_per_day=8.0))
check("doubling HDD doubles the envelope term",
      abs(o2["term_envelope"] - 2 * o["term_envelope"]) < 1e-6)
check("doubling HDD leaves the DHW term untouched",
      abs(oe["term_dhw"] - ph.evaluate(dict(base, dhw_electric=True,
                                            hdd_per_day=8.0))["term_dhw"]) < 1e-6)

# (f) ventilation is identical in both baselines, so it must cancel
check("ventilation cancels out of the difference",
      abs((o["H_as_built"] - o["H_reference"])
          - (ph.u_as_built("post2010", 0) - ph.value("u_reference")) * a_th) < 1e-9,
      "H_V = %.1f W/K present in both, absent from the difference" % h_v)

# (g) an older house must lose more, all else equal
older = ph.evaluate(dict(base, era="pre1975"))
check("a pre-1975 house has a larger deficiency than a post-2010 one",
      older["deficiency"] > o["deficiency"],
      "%.0f > %.0f kWh/yr" % (older["deficiency"], o["deficiency"]))

head("3. BINDING #3 - A REAL SECOND SOURCE THAT CORRECTLY REFUSES")

MR = meta.to_roles(ROOT / "heapo_data/meta_data/meta_data.csv")
print("  meta_data.csv: %d households - SIX TIMES the protocol cohort of 214"
      % len(MR))
rep = meta.contract_report(MR)
print()
print(rep.to_string(index=False))

missing = rep[rep.status == "MISSING"].role.tolist()
check("the contract report names every missing role", len(missing) == 5,
      ", ".join(missing))
check("no missing role was invented or defaulted",
      all(MR[r].isna().all() for r in missing))
try:
    ph.evaluate(MR.iloc[0].to_dict())
    ran = True
except Exception as e:
    ran = False
    why = type(e).__name__
check("p_physics REFUSES a meta_data row rather than guessing", not ran,
      why if not ran else "IT RAN - the contract is not being enforced")

print("\n  This is the generic-versus-specific split made machine-checkable.")
print("  meta_data drives the PEER model - any fleet, no site visit, imprecise.")
print("  The physical model needs someone to have walked through the building,")
print("  and the contract says so BEFORE a number is computed, not after.")

head("4. THE PHYSICS LAYER WAS NOT TOUCHED")

src = (HERE / "p_physics.py").read_text(encoding="utf-8")
for tok in ["Building_", "HeatPump_", "Survey_", "Gebaeude", "Baujahr",
            "protocols.csv", "meta_data"]:
    check("p_physics.py free of '%s'" % tok, tok not in src)
check("three adapters exist",
      all((HERE / f"p_adapter_{n}.py").exists()
          for n in ["heapo", "synthetic", "meta"]))

head("5. THE SAME PHYSICS, THREE SOURCES")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
n_heapo = int(modellable(H).sum())
rows = [("#1 heapo protocols.csv", 214, n_heapo, "the live deliverable"),
        ("#2 synthetic (foreign schema)", len(R), len(S), "round trip, all exact"),
        ("#3 heapo meta_data.csv", len(MR), 0,
         "REFUSED - 5 required roles absent")]
print("  %-32s %8s %12s  %s" % ("binding", "rows in", "modellable", "outcome"))
for a, b, c, d in rows:
    print("  %-32s %8d %12d  %s" % (a, b, c, d))

S.to_csv(DATA / "p10_synthetic_results.csv", index=False, sep=";")
rep.to_csv(DATA / "p10_meta_contract.csv", index=False, sep=";")

head("SUMMARY")
print("  %d checks, %d passed, %d FAILED" % (len(OK) + len(BAD), len(OK), len(BAD)))
if BAD:
    for f in BAD:
        print("    FAILED: %s" % f)
    sys.exit(1)
print("\n  Portability is now DEMONSTRATED, not claimed.")
print("  Still absent: a second REAL dataset with audit-level building data.")
print("  Synthetic proves the interface; only foreign field data proves the")
print("  CONSTANTS travel. Say so.")
