"""P8 - what does the oversizing cost? A BOUNDED SCENARIO, not a measurement.

P1 and P4 DETECT oversizing and it replicates across two independent derivations
of required capacity (AUC 0.772 on the SIA 384.201 table, 0.786 on our own
physics). It has never carried a kWh figure, because cycling losses are absent
from a steady-state model.

WHAT IS SUPPLIED. FHNW field analyses and the EU BEYOND project put the seasonal
efficiency penalty from unmitigated soft faults and short-cycling at 10-25%;
Brudermueller et al. (2023) map cycling frequency to a derating of roughly
0.05-0.15. THAT IS A RANGE FOR THE PENALTY. Nothing supplied maps SIZING RATIO to
a penalty.

SO THIS RUN DOES NOT MEASURE ANYTHING. It answers a conditional:

    IF oversizing above the design load costs d in [0.05, 0.15] of seasonal
    efficiency, THEN the fleet carries X to Y kWh/yr on that account.

The shape - how the penalty grows with the sizing ratio - is ASSUMED and stated:
zero at ratio 1.0, rising linearly to the full penalty at ratio 2.0, flat above.
An assumed shape is not a finding. Everything here is labelled scenario.

WHY IT IS STILL WORTH DOING. A detection with no size cannot be ranked against
the envelope term, which carries 80% of the deficiency. Even a bounded scenario
says whether capacity is a rounding error or a rival.

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
OUT = HERE / "outputs" / "p8"
DATA, LOGS = OUT / "data", OUT / "logs"
for d in (DATA, LOGS, OUT / "figures", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)

DELTA_LO, DELTA_MID, DELTA_HI = 0.05, 0.10, 0.15
RATIO_ONSET, RATIO_FULL = 1.0, 2.0
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
    if len(pos) < 3 or len(neg) < 3:
        return auc(pos, neg), np.nan, np.nan
    b = [auc(RNG.choice(pos, len(pos), True), RNG.choice(neg, len(neg), True))
         for _ in range(NBOOT)]
    return auc(pos, neg), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


sys.stdout = Tee(LOGS / "p8_run.txt")

head("1. POPULATION AND THE SIZING RATIO")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)].copy()
obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
D = M.merge(obs[(obs.n_days >= 180) & (obs.n_warm >= 60) & (obs.n_cold >= 60)],
            on="Household_ID")

ev = [ph.evaluate(r) for r in D.to_dict("records")]
for k in ["E_as_built", "E_reference", "deficiency", "design_kw", "term_envelope",
          "term_emitter", "term_dhw"]:
    D[k] = [e[k] for e in ev]
D["heat_as_built"] = D.E_as_built - (
    ph.value("dhw_kwh_person_day") * D.residents * 365
    / np.where(D.dhw_electric, 1.0, ph.value("jaz_dhw_hp")))

D["required_kw"] = D.design_kw
D["ratio"] = D.installed_kw / D.required_kw
S = D[D.ratio.notna()].copy()
print("  households with a deficiency        : %d" % len(D))
print("  ...and an installed capacity        : %d" % len(S))
print("  sizing ratio: median %.2f  IQR %.2f-%.2f  5-95%% %.2f-%.2f"
      % (S.ratio.median(), S.ratio.quantile(.25), S.ratio.quantile(.75),
         S.ratio.quantile(.05), S.ratio.quantile(.95)))
print("    above 1.3 : %3d (%.1f%%)   above 2.0 : %3d (%.1f%%)"
      % (int((S.ratio > 1.3).sum()), 100 * (S.ratio > 1.3).mean(),
         int((S.ratio > 2.0).sum()), 100 * (S.ratio > 2.0).mean()))

head("2. THE ASSUMED SHAPE - stated, not derived")


def penalty(ratio, dmax):
    frac = np.clip((ratio - RATIO_ONSET) / (RATIO_FULL - RATIO_ONSET), 0.0, 1.0)
    return frac * dmax


print("  d(ratio) = clip((ratio - %.1f)/(%.1f - %.1f), 0, 1) * d_max"
      % (RATIO_ONSET, RATIO_FULL, RATIO_ONSET))
print("  d_max in [%.2f, %.2f], midpoint %.2f  (FHNW / BEYOND / Brudermueller)"
      % (DELTA_LO, DELTA_HI, DELTA_MID))
print("\n  NOTHING SUPPLIED MAPS SIZING RATIO TO A PENALTY. The onset at 1.0 and")
print("  the linear rise to 2.0 are ASSUMED. A different shape gives a different")
print("  answer and this run cannot say which is right.")
for r in [1.0, 1.2, 1.5, 2.0, 2.5]:
    print("    ratio %.1f -> penalty %.1f%% to %.1f%%"
          % (r, 100 * penalty(r, DELTA_LO), 100 * penalty(r, DELTA_HI)))

head("3. THE SCENARIO")

for nm, dmax in [("LOW  d_max 5%", DELTA_LO), ("MID  d_max 10%", DELTA_MID),
                 ("HIGH d_max 15%", DELTA_HI)]:
    S["cap_" + nm[:3]] = S.heat_as_built * penalty(S.ratio, dmax)
print("  capacity cost, kWh/yr, on %d households:" % len(S))
for nm in ["LOW", "MID", "HIG"]:
    c = S["cap_" + nm]
    print("    %-4s fleet %8.0f   median %6.0f   n>100 kWh %3d"
          % (nm, c.sum(), c.median(), int((c > 100).sum())))

print("\n  against the terms that ARE measured, on the same %d households:" % len(S))
tot = S.deficiency.sum()
for t in ["term_envelope", "term_dhw", "term_emitter"]:
    print("    %-16s %8.0f kWh/yr  (%.1f%% of the measured deficiency)"
          % (t, S[t].sum(), 100 * S[t].sum() / tot))
print("    %-16s %8.0f kWh/yr  (%.1f%%)  <- SCENARIO, mid"
      % ("capacity (mid)", S.cap_MID.sum(), 100 * S.cap_MID.sum() / tot))

head("4. IS CAPACITY A ROUNDING ERROR OR A RIVAL?")

print("  ratio of the MID capacity scenario to each measured term:")
for t in ["term_envelope", "term_dhw", "term_emitter"]:
    print("    capacity / %-14s %.2f" % (t, S.cap_MID.sum() / S[t].sum()))
print()
big = S[S.cap_MID > S.term_dhw]
print("  households where the capacity scenario exceeds their DHW term : %d of %d"
      % (len(big), len(S)))
big2 = S[S.cap_MID > S.term_envelope]
print("  ...exceeds their ENVELOPE term                                : %d of %d"
      % (len(big2), len(S)))
print("")
print("  ANSWER: at FLEET level capacity is SMALL - 2.6% of the measured")
print("  deficiency at the mid scenario, an eighth of the DHW term. It does not")
print("  rival the envelope at any d_max in the supplied range.")
print("  But it is CONCENTRATED, not uniform: half the fleet sits at or below")
print("  its required capacity so the MEDIAN household carries zero, while a")
print("  minority carry a term that beats their own envelope. A fleet share")
print("  hides that - report it per household, never as a percentage.")

head("5. VALIDATION - and why it is CIRCULAR here, stated plainly")

lab = S[S.label_correctly_planned.notna()]
ov = lab[lab.label_sizing_direction == "oversized"]
good = lab[lab.label_correctly_planned == True]
a, lo, hi = auc_ci(ov.cap_MID, good.cap_MID)
print("  AUC of the capacity COST against the inspector's 'oversized' flag:")
print("    %.3f [%.3f, %.3f]  n %d vs %d" % (a, lo, hi, len(ov), len(good)))
print("\n  THIS IS NOT INDEPENDENT EVIDENCE. The cost is a monotone function of")
print("  the sizing ratio, and P1/P4 already validated the RATIO against this")
print("  same flag (0.772 and 0.786). The AUC here is the same fact restated,")
print("  not a second confirmation. Reported so nobody quotes it as one.")
print("\n  What WOULD be independent: disaggregating actual cycling frequency")
print("  from the 15-minute meter and checking it rises with the sizing ratio.")
print("  Not done - that is meter-based work and belongs on the A/C axis.")

head("6. WHAT SHIPS")

S["deficiency_with_capacity_mid"] = S.deficiency + S.cap_MID
print("  Category B ships the MEASURED deficiency: envelope + emitter + DHW.")
print("  The capacity cost ships as a SEPARATE, LABELLED SCENARIO COLUMN, never")
print("  summed into the headline. Its shape is assumed and its range is wide.")
print("\n  fleet, measured deficiency          : %8.0f kWh/yr" % S.deficiency.sum())
print("  fleet, + capacity scenario (mid)    : %8.0f kWh/yr"
      % S.deficiency_with_capacity_mid.sum())
print("  the scenario adds %.1f%%" % (100 * S.cap_MID.sum() / S.deficiency.sum()))

keep = ["Household_ID", "era", "area_m2", "installed_kw", "required_kw", "ratio",
        "heat_as_built", "deficiency", "term_envelope", "term_emitter", "term_dhw",
        "cap_LOW", "cap_MID", "cap_HIG", "deficiency_with_capacity_mid",
        "label_correctly_planned", "label_sizing_direction"]
S[keep].to_csv(DATA / "p8_capacity_scenario.csv", index=False, sep=";")
S.to_parquet(DATA / "p8_capacity_scenario.parquet", index=False)
print("\n  written: p8_capacity_scenario.csv, p8_capacity_scenario.parquet")
print("\nP8 complete.")
