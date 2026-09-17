"""P20 - the heating JAZ, from the primary source the verified notebook found.

OST WPZ Buchs, "Wie gut sind aktuelle Waermepumpen im Feld?", Heizungsplaner +
Installateur 11/12-2020, Tabelle 1 (notebook b02e42f0, source 15; body text read here
confirms air/water Altbau 2.8 and Sanierung 3.1 for heating + DHW). JAZ by application:

                        heating only        heating + DHW
  Neubau 35-30 C        air 3.7  gnd 5.7    air 3.5  gnd 4.9
  Sanierung 45-40 C     air 3.3  gnd 5.0    air 3.1  gnd 4.6
  Altbau 55-50 C        air 2.9  gnd 4.4    air 2.8  gnd 4.3
  DHW alone (Abb. 3)    air 2.8  gnd 3.3

The live registry uses the air "heating + DHW" column for a heating-only term, and a
ground-source floor value (4.25) found in no primary source, with radiators DERIVED at
3.40 where the table gives 4.3-4.4.

Scenarios, fixed before the run, NONE chosen by fit:
  S0  live registry
  S1  one column for both types: heating + DHW (ground 4.9 / 4.6 / 4.3, no derivation)
  S2  system-boundary consistent: heating-only column for space heating, DHW-alone
      JAZ by pump type for DHW - the model already carries DHW as a separate term
  S3  vintage lower bound: FAWA 1996-2003 fleet means, air 2.7, ground 3.5, flat

Emitter mapping as live: floor_only -> Neubau, both -> Sanierung, radiator_only -> Altbau.
Weather only on the physics side; the meter enters only the level comparison (P17's
step slope), which is VALIDATION. Nothing in p_physics changes.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "p20"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

A, G = "air-source", "ground-source"
F, M, R = "floor_only", "both", "radiator_only"
SCEN = {
    "S1_heat+dhw": ({(A, F): 3.5, (A, M): 3.1, (A, R): 2.8,
                     (G, F): 4.9, (G, M): 4.6, (G, R): 4.3}, None),
    "S2_boundary": ({(A, F): 3.7, (A, M): 3.3, (A, R): 2.9,
                     (G, F): 5.7, (G, M): 5.0, (G, R): 4.4}, {A: 2.8, G: 3.3}),
    "S3_fawa_vintage": ({(t, e): (2.7 if t == A else 3.5) for t in (A, G) for e in (F, M, R)},
                        None),
}


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


def run(D, table=None, dhw=None):
    live_jaz, live_dhw = ph.jaz_for, ph.C["jaz_dhw_hp"]
    if table is not None:
        ph.jaz_for = lambda t, e, rng=None: (table[(t, e)], False)
    rows = []
    try:
        for h in D.to_dict("records"):
            if dhw is not None:
                v = dhw[h["hp_type"]]
                ph.C["jaz_dhw_hp"] = (v, v, v) + live_dhw[3:]
            e = ph.evaluate(h)
            rows.append({"Household_ID": h["Household_ID"], "deficiency": e["deficiency"],
                         "term_envelope": e["term_envelope"], "term_emitter": e["term_emitter"],
                         "term_dhw": e["term_dhw"], "E_as_built": e["E_as_built"],
                         "beta_phys": e["H_as_built"] * 24 / 1000 / e["jaz_as_built"],
                         "jaz_as_built": e["jaz_as_built"]})
    finally:
        ph.jaz_for, ph.C["jaz_dhw_hp"] = live_jaz, live_dhw
    return pd.DataFrame(rows)


sys.stdout = Tee(LOGS / "p20_run.txt")

head("1. POPULATION - P17's 172 households, with the step-model measured slope")

D = pd.read_parquet(HERE / "outputs/p17/data/p17_slope_step.parquet")
print("  households: %d" % len(D))
print(D.groupby(["hp_type", "emitter"]).size().rename("n").to_string())

res = {"S0_live": run(D)}
for k, (tab, dhw) in SCEN.items():
    res[k] = run(D, tab, dhw)
s0 = res["S0_live"].set_index("Household_ID")
print("  S0 fleet deficiency %.0f kWh/yr (P6 record 321,330)" % s0.deficiency.sum())

head("2. CATEGORY B - deficiency and its terms, kWh/yr fleet")

print("  %-16s %9s %8s | %9s %9s %9s | %s"
      % ("scenario", "fleet", "median", "envelope", "emitter", "dhw", "worst-quartile overlap vs S0"))
era = D.set_index("Household_ID").era


def topq(s):
    r = s.groupby(era.loc[s.index]).rank(ascending=False)
    n = s.groupby(era.loc[s.index]).transform("size")
    return set(s[r <= np.ceil(n * 0.25)].index)


t0 = topq(s0.deficiency)
for k, r in res.items():
    r = r.set_index("Household_ID")
    tq = topq(r.deficiency)
    print("  %-16s %9.0f %8.0f | %9.0f %9.0f %9.0f | %d / %d"
          % (k, r.deficiency.sum(), r.deficiency.median(), r.term_envelope.sum(),
             r.term_emitter.sum(), r.term_dhw.sum(), len(tq & t0), len(t0)))

gnr = D[(D.hp_type == G) & (D.emitter != F)].Household_ID
print("\n  the %d ground-source non-floor households (live JAZ DERIVED):" % len(gnr))
for k, r in res.items():
    r = r.set_index("Household_ID").loc[gnr]
    print("    %-16s median as-built JAZ %.2f   median deficiency %6.0f"
          % (k, r.jaz_as_built.median(), r.deficiency.median()))

head("3. THE LEVEL CHECK (validation only) - physics vs P17's step slope")

Dm = D.set_index("Household_ID")
print("  %-16s %9s | %s | %s" % ("scenario", "phys/meas", "  ".join("%9s" % e[:9]
                                  for e in ph.ERA_ORDER), "rho per m2"))
for k, r in res.items():
    r = r.set_index("Household_ID")
    bpm2 = r.beta_phys / Dm.area_m2
    bmm2 = Dm.b_step / Dm.area_m2
    vals = [bmm2[Dm.era == e].median() / bpm2[Dm.era == e].median() for e in ph.ERA_ORDER]
    rho = pd.concat([bpm2, bmm2], axis=1).corr(method="spearman").iloc[0, 1]
    print("  %-16s %9.3f | %s | %+.3f" % (k, (r.beta_phys / Dm.b_step).median(),
                                         "  ".join("%9.2f" % v for v in vals), rho))
print("\n  A scenario landing nearer 1.0 is NOT evidence for it (trap 4).")

out = pd.concat({k: r.set_index("Household_ID") for k, r in res.items()}, axis=1)
out.columns = ["%s__%s" % c for c in out.columns]
out.reset_index().to_parquet(DATA / "p20_scenarios.parquet", index=False)
print("\n  written: p20_scenarios.parquet")
