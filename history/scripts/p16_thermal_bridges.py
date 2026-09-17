"""P16 - limitation 3, the era gradient is too steep.

P9: physics matches the pre-1975 meter slope (0.97) and under-predicts every newer
era by 24-53%. Spec v3 proposes gamma(>2000) = 1.30. REJECTED: it sits inside the
P9 ratios we have already seen, so it would be calibration with a citation attached.
Setpoint rebound cannot enter either - the degree-day base is fixed at 12 C.

P16 tests a MECHANISM instead. TABULA's own method (Common Calculation Method, eq. 4,
Table 3) adds thermal bridging as a SEPARATE surcharge dU_tb on all U-values; element
U-values exclude it, and p_physics has never carried it. An ADDITIVE term matters
proportionally more for a U of 0.24 than of 1.35, which is exactly the shape of the
P9 error. Values are TABULA's categories, fixed before the run: 0.05 low, 0.10 medium
(the worked example, and the DIN 4108 Bbl 2 flat default for stock), 0.15 high.

The meter side is P9's own beta_meas, unchanged. No value is chosen by fit: every
category is reported, and none is selected by which one closes the gap.

NOTHING HERE CHANGES p_physics.

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "p16"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

DU = [0.0, 0.05, 0.10, 0.15]
NBOOT = 2000
RNG = np.random.default_rng(20260914)
P9_RATIOS = {"pre1975": 0.97, "1976_1990": 1.26, "1991_2000": 1.24,
             "2001_2010": 1.53, "post2010": 1.31}
METER_PRE_POST = (2.50, 1.68, 3.45)
BENCH = {"pre1975": 60.0, "1976_1990": 45.0, "1991_2000": 35.0,
         "2001_2010": 32.5, "post2010": 25.0}


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


def spear(a, b, boot=True):
    s = pd.DataFrame({"a": a, "b": b}).dropna()
    r = s.corr(method="spearman").iloc[0, 1]
    if not boot:
        return r, np.nan, np.nan
    bs = [pd.DataFrame(s.values[RNG.integers(0, len(s), len(s))], columns=["a", "b"])
          .corr(method="spearman").iloc[0, 1] for _ in range(NBOOT)]
    return r, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def era_ratios(df, phys_m2):
    return {e: df.loc[df.era == e, "beta_meas_m2"].median()
            / phys_m2[df.era == e].median() for e in ph.ERA_ORDER}


sys.stdout = Tee(LOGS / "p16_run.txt")

head("1. P9 REPRODUCED ON THE LIVE MODEL")

V = pd.read_parquet(HERE / "outputs/p9/data/p9_envelope_validation.parquet")
live = [ph.evaluate(r) for r in V.to_dict("records")]
V["a_th"] = [e["a_thermal"] for e in live]
V["H_live"] = [e["H_as_built"] for e in live]
V["jaz_live"] = [e["jaz_as_built"] for e in live]
V["hdd_corrected"] = [e["hdd_corrected"] for e in live]
V["deficiency"] = [e["deficiency"] for e in live]
dH = (V.H_live - V.H_as_built).abs()
print("  households: %d   H_as_built live vs P9 file: max |diff| %.2e W/K, %d differ > 1e-6"
      % (len(V), dH.max(), int((dH > 1e-6).sum())))
r0 = era_ratios(V, V.H_live * 24 / 1000 / V.jaz_live / V.area_m2)
print("  era ratio measured/physics, live vs P9 report:")
for e in ph.ERA_ORDER:
    print("    %-10s %.2f   (P9 %.2f)" % (e, r0[e], P9_RATIOS[e]))

head("2. THERMAL-BRIDGE SURCHARGE ON THE AS-BUILT U - the P9 tests rerun")

print("  %-6s | %s | %6s %6s | %8s | %14s | %s"
      % ("dU_tb", "  ".join("%9s" % e[:9] for e in ph.ERA_ORDER), "range", "max/mn",
         "pre/post", "phys/meas med", "Spearman per m2"))
rows = []
for du in DU:
    bp = (V.H_live + du * V.a_th) * 24 / 1000 / V.jaz_live
    bpm2 = bp / V.area_m2
    rr = era_ratios(V, bpm2)
    vals = list(rr.values())
    pre_post = bpm2[V.era == "pre1975"].median() / bpm2[V.era == "post2010"].median()
    rho, lo, hi = spear(bpm2, V.beta_meas_m2, boot=du in (0.0, 0.10))
    ci = "" if np.isnan(lo) else " [%+.3f, %+.3f]" % (lo, hi)
    print("  %-6.2f | %s | %6.2f %6.2f | %8.2f | %14.2f | %+.3f%s"
          % (du, "  ".join("%9.2f" % v for v in vals), max(vals) - min(vals),
             max(vals) / min(vals), pre_post, (bp / V.beta_meas).median(), rho, ci))
    rows.append({"dU_tb": du, **{"ratio_" + e: rr[e] for e in ph.ERA_ORDER},
                 "range": max(vals) - min(vals), "pre_post_phys": pre_post,
                 "phys_over_meas_median": (bp / V.beta_meas).median(), "spearman_m2": rho})
print("\n  meter pre-1975 / post-2010, from P9: %.2f [%.2f, %.2f]" % METER_PRE_POST)

head("3. COUPLING WITH LIMITATION 2 - the same surcharge on the design load")

D = pd.read_parquet(HERE / "outputs/p15/data/p15_design_load.parquet")
print("  P15 S2 (EN 12831 conventions) + dU_tb x huellzahl x 30 K, ratio to SIA 384.201:")
print("  %-6s | %s | %6s %6s" % ("dU_tb", "  ".join("%9s" % e[:9] for e in ph.ERA_ORDER),
                                 "range", "fleet"))
for du in DU:
    w = D.S2 + du * D.huellzahl * (ph.value("t_set") - ph.value("t_design"))
    r = w / D.bench
    vals = [r[D.era == e].median() for e in ph.ERA_ORDER]
    print("  %-6.2f | %s | %6.2f %6.2f"
          % (du, "  ".join("%9.2f" % v for v in vals), max(vals) - min(vals), r.median()))

head("4. WHAT IT DOES TO THE DEFICIENCY - a policy choice, not physics")

base = V.deficiency.sum()
print("  fleet deficiency, these %d households, live: %.0f kWh/yr" % (len(V), base))
print("  (a) same dU_tb on BOTH baselines: H_as_built - H_reference unchanged,")
print("      so term_envelope moves by exactly 0. Only the level and the slope move.")
for ab, rf in [(0.10, 0.05), (0.15, 0.05), (0.10, 0.0)]:
    add = ph.heating_electricity((ab - rf) * V.a_th, V.jaz_live, V.hdd_corrected)
    print("  (b) as-built %.2f, reference %.2f: +%.0f kWh/yr fleet (+%.1f%%), median +%.0f"
          % (ab, rf, add.sum(), 100 * add.sum() / base, add.median()))

pd.DataFrame(rows).to_csv(DATA / "p16_scenarios.csv", sep=";", index=False)
V[["Household_ID", "era", "area_m2", "a_th", "H_live", "jaz_live", "beta_meas",
   "beta_meas_m2", "hdd_corrected", "deficiency"]].to_parquet(
    DATA / "p16_households.parquet", index=False)
print("\n  written: p16_scenarios.csv, p16_households.parquet")
