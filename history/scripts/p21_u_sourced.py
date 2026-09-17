"""P21 - the as-built U-values, from a real Swiss source.

The registry's five as-built U-values cite a TABULA/EPISCOPE CH typology that does not
exist; inside the verified notebook they occur only in an AI-generated report.
The verified notebook (b02e42f0, question q13, answers in outputs/p21/data/) read the
real Swiss building-stock model:

  TEP Energy (2016), Erweiterung des Gebaeudeparkmodells gemaess SIA-Effizienzpfad
  Energie, BFE Schlussbericht, section 3.2.1, Abbildung 30-33, EFH, mean and SD.

Cross-check that passed BEFORE this run: the report's own text says roofs improve
~60% and cellar ceilings ~40% from 1976-90 to 1991-2009; the chart readings give
-58% and -42%. The readings are still read off a chart - declared as approximate.

Envelope mean = element U weighted by the live area split (wall .50 / roof .22 /
floor .18 / window .10). THE SPLIT ITSELF STILL CARRIES THE DEAD TABULA-CH CITATION -
declared, not resolved here. Periods before 1975 are pooled with TEP's EFH stock
shares (Tabelle 19: 13 / 20 / 27 %). After 2010 TEP has no period, so the legal
limits apply: MuKEn 2008 (value) to MuKEn 2014 (lo), EnDK/Energiehub 2014 Abb. 13.

Scenarios, fixed before the run, NONE chosen by fit:
  S0  live registry
  S1  TEP 2016 EFH envelope means, band = +/- aggregated SD
  S2  S1 but pre-1975 walls/attic from Jakob et al. 2002 Tab 4.3-38 (1925-1965: wall
      1.16, attic 0.88) - the higher Swiss estimate, as a sensitivity
  S3  S1 together with P20's S2 heating JAZ - what adopting both would do

Nothing in p_physics changes.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "p21"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

W = {"wall": .50, "roof": .22, "floor": .18, "window": .10}
# (mean, sd) per element, EFH, TEP 2016 Abb. 30-33 as read by the notebook
TEP = {"pre1920":   {"wall": (.86, .10), "window": (2.20, .20), "roof": (.75, .15), "floor": (.67, .03)},
       "1920_1946": {"wall": (.90, .10), "window": (2.09, .20), "roof": (.71, .15), "floor": (.67, .03)},
       "1947_1975": {"wall": (.95, .20), "window": (1.98, .20), "roof": (.70, .05), "floor": (.70, .05)},
       "1976_1990": {"wall": (.65, .15), "window": (1.75, .20), "roof": (.60, .10), "floor": (.60, .10)},
       "1991_2009": {"wall": (.27, .07), "window": (1.40, .20), "roof": (.25, .06), "floor": (.35, .06)}}
PRE_SHARE = {"pre1920": 13, "1920_1946": 20, "1947_1975": 27}
MUKEN = {"2008": {"wall": .20, "roof": .20, "floor": .25, "window": 1.3},
         "2014": {"wall": .17, "roof": .17, "floor": .25, "window": 1.0}}


def env(el):
    m = sum(W[k] * el[k][0] for k in W)
    sd = np.sqrt(sum((W[k] * el[k][1]) ** 2 for k in W))
    return m, sd


def pooled(periods, override=None):
    tot = sum(PRE_SHARE[p] for p in periods)
    m = sd = 0.0
    for p in periods:
        el = dict(TEP[p])
        if override:
            el.update(override)
        pm, psd = env(el)
        m += PRE_SHARE[p] / tot * pm
        sd += PRE_SHARE[p] / tot * psd
    return m, sd


def u_table(jakob=False):
    ov = {"wall": (1.16, .20), "roof": (.88, .15)} if jakob else None
    pre = pooled(list(PRE_SHARE), ov)
    t = {"pre1975": pre, "1976_1990": env(TEP["1976_1990"]),
         "1991_2000": env(TEP["1991_2009"]), "2001_2010": env(TEP["1991_2009"])}
    m08 = sum(W[k] * MUKEN["2008"][k] for k in W)
    m14 = sum(W[k] * MUKEN["2014"][k] for k in W)
    t["post2010"] = (m08, None, m14)
    return t


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


def patched(u=None, jaz=None, dhw=None):
    saved = {k: ph.C[k] for k in ph.C}
    saved_jf = ph.jaz_for
    if u:
        for era, v in u.items():
            key = ph.ERA_KEYS[era]
            if v[1] is None:
                m, lo = v[0], v[2]
                hi = m + (m - lo)
            else:
                m, lo, hi = v[0], v[0] - v[1], v[0] + v[1]
            ph.C[key] = (m, lo, hi) + saved[key][3:]
    if jaz:
        ph.jaz_for = lambda t, e, rng=None: (jaz[(t, e)], False)
    return saved, saved_jf


def run(D, u=None, jaz=None, dhw=None):
    saved, saved_jf = patched(u, jaz)
    rows = []
    try:
        for h in D.to_dict("records"):
            if dhw is not None:
                v = dhw[h["hp_type"]]
                ph.C["jaz_dhw_hp"] = (v, v, v) + saved["jaz_dhw_hp"][3:]
            e = ph.evaluate(h)
            rows.append({"Household_ID": h["Household_ID"], "deficiency": e["deficiency"],
                         "term_envelope": e["term_envelope"], "u_as_built": e["u_as_built"],
                         "beta_phys": e["H_as_built"] * 24 / 1000 / e["jaz_as_built"],
                         "design_w_m2": e["design_kw"] * 1000 / h["area_m2"]})
    finally:
        ph.C.clear()
        ph.C.update(saved)
        ph.jaz_for = saved_jf
    return pd.DataFrame(rows).set_index("Household_ID")


sys.stdout = Tee(LOGS / "p21_run.txt")

head("1. THE SOURCED U TABLE - envelope means by HEAPO era")

T1, T2 = u_table(), u_table(jakob=True)
print("  %-10s %-26s %-18s %-18s" % ("era", "registry (dead citation)", "S1 TEP 2016", "S2 Jakob pre-1975"))
for e in ph.ERA_ORDER:
    v, lo, hi = ph.C[ph.ERA_KEYS[e]][:3]
    s1, s2 = T1[e], T2[e]
    f = lambda s: ("%.3f +/- %.3f" % (s[0], s[1])) if s[1] is not None else ("%.3f (lo %.3f)" % (s[0], s[2]))
    print("  %-10s %.2f [%.2f-%.2f]%9s %-18s %-18s" % (e, v, lo, hi, "", f(s1), f(s2)))
print("\n  reference: live u_reference %.3f; MuKEn 2014 on the same split %.3f"
      % (ph.value("u_reference"), sum(W[k] * MUKEN["2014"][k] for k in W)))

A, G = "air-source", "ground-source"
F_, M_, R_ = "floor_only", "both", "radiator_only"
JAZ_S2 = {(A, F_): 3.7, (A, M_): 3.3, (A, R_): 2.9, (G, F_): 5.7, (G, M_): 5.0, (G, R_): 4.4}
DHW_S2 = {A: 2.8, G: 3.3}

D = pd.read_parquet(HERE / "outputs/p17/data/p17_slope_step.parquet")
res = {"S0_live": run(D), "S1_TEP": run(D, T1), "S2_TEP_Jakob": run(D, T2),
       "S3_TEP+JAZ": run(D, T1, JAZ_S2, DHW_S2)}

head("2. CATEGORY B - deficiency")

era = D.set_index("Household_ID").era


def topq(s):
    r = s.groupby(era.loc[s.index]).rank(ascending=False)
    n = s.groupby(era.loc[s.index]).transform("size")
    return set(s[r <= np.ceil(n * 0.25)].index)


t0 = topq(res["S0_live"].deficiency)
print("  %-14s %9s %7s %9s | worst-q | median deficiency by era" % ("scenario", "fleet", "median", "envelope"))
for k, r in res.items():
    by = "  ".join("%5.0f" % r.deficiency[era.loc[r.index] == e].median() for e in ph.ERA_ORDER)
    print("  %-14s %9.0f %7.0f %9.0f | %2d/%2d | %s" % (k, r.deficiency.sum(), r.deficiency.median(),
                                                     r.term_envelope.sum(), len(topq(r.deficiency) & t0),
                                                     len(t0), by))
print("  era order: %s" % " ".join(ph.ERA_ORDER))

head("3. VALIDATION ONLY - the meter (P17 step slope) and the SIA 384.201 table")

Dm = D.set_index("Household_ID")
BENCH = {"pre1975": 60.0, "1976_1990": 45.0, "1991_2000": 35.0, "2001_2010": 32.5, "post2010": 25.0}
print("  %-14s %9s | meas/phys by era: %s | range | rho m2 | design/table by era" %
      ("scenario", "phys/meas", " ".join(e[:7] for e in ph.ERA_ORDER)))
for k, r in res.items():
    bpm2 = r.beta_phys / Dm.area_m2
    bmm2 = Dm.b_step / Dm.area_m2
    vals = [bmm2[Dm.era == e].median() / bpm2[Dm.era == e].median() for e in ph.ERA_ORDER]
    rho = pd.concat([bpm2, bmm2], axis=1).corr(method="spearman").iloc[0, 1]
    dz = [r.design_w_m2[Dm.era == e].median() / BENCH[e] for e in ph.ERA_ORDER]
    print("  %-14s %9.3f | %s | %5.2f | %+.3f | %s" % (
        k, (r.beta_phys / Dm.b_step).median(), " ".join("%7.2f" % v for v in vals),
        max(vals) - min(vals), rho, " ".join("%4.2f" % v for v in dz)))
print("\n  Validation, not selection: a scenario landing nearer 1.0 is NOT evidence for it (trap 4).")

out = pd.concat(res, axis=1)
out.columns = ["%s__%s" % c for c in out.columns]
out.reset_index().to_parquet(DATA / "p21_u_scenarios.parquet", index=False)
print("\n  written: p21_u_scenarios.parquet")
