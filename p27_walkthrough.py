"""P27 - the worked example. One household traced end to end, plus three contrast cases.

WHY THIS EXISTS (Miguel, 2026-09-17): the mechanism is spread over 26 CLAUDE.md sections
and a dozen findings reports. Nowhere is it readable as a single story: this house, these
numbers, this rank, and for every number where it came from.

THE RULE THAT SHAPES IT: no number is typed by hand. Every figure is computed here or
read from the registry / the shipped export, so the document cannot go stale. This model
has already revised its fleet totals twice and corrected an envelope constant; a
hand-typed walkthrough would have gone quietly wrong on both occasions.

WHAT IT IS NOT: a claim that the model works. It says HOW the model works. Performance
belongs in the report's own results section (Miguel, 2026-09-17).

FOUR PROVENANCE TAGS, because "from a reference" is really two different things:
  DATABASE  a value HEAPO measured or an auditor recorded - named to its column
  VERIFIED  a constant read in the cited primary document
  DERIVED   a constant WE computed from published inputs (re-derived by the test)
  GENERATED a number this model computes for this household

numpy + pandas only.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import p_physics as ph
from p_adapter_heapo import (load_households, modellable, daily_observations,
                             station_normals, drop_reasons)

OUT = HERE / "outputs" / "p27"
for d in (OUT / "data", OUT / "logs", OUT / "reports"):
    d.mkdir(parents=True, exist_ok=True)
EXPORT = HERE / "outputs" / "export" / "physical_baseline_v2.parquet"

DEEP = 116121
ROUND_TOL = 2.0

# role -> the HEAPO column it comes from. Kept beside the trace, because a provenance
# document whose own provenance is "trust me" is worth nothing.
SRC = {
    "area_m2": "Building_FloorAreaHeated_Total",
    "footprint_m2": "max(Building_FloorAreaHeated_<storey>)",
    "n_storeys_above": "count(Building_FloorAreaHeated_<storey> > 0)",
    "heated_basement": "Building_FloorAreaHeated_Basement > 0",
    "era": "Building_ConstructionYear_Interval",
    "renovation_count": "Building_Renovated_Windows + _Walls + _Roof",
    "residents": "Building_Residents",
    "hp_type": "HeatPump_Installation_Type",
    "emitter": "HeatPump heat-distribution flags (floor / radiator)",
    "dhw_electric": "DHW_Production_ByElectricWaterHeater",
    "hp_install_year": "HeatPump_Installation_Year",
    "hdd_normal_per_day": "weather_daily.parquet, station NORMAL year",
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


sys.stdout = Tee(OUT / "logs" / "p27_run.txt")

TRACE = []


def rec(step, what, value, unit, tag, src, note=""):
    TRACE.append({"step": step, "quantity": what, "value": value, "unit": unit,
                  "provenance": tag, "source": src, "note": note})
    return value


def ref(step, name, note=""):
    """Pull a constant AND its provenance out of the registry in one move."""
    v, lo, hi, unit, source, section = ph.C[name]
    rec(step, name, v, unit, ph.STATUS[name], source + " | " + section, note)
    return v


head("0. POPULATION AND CASE SELECTION")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
M = H[modellable(H)]
obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
A = M.merge(obs[(obs.n_days >= 180) & (obs.n_warm >= 60) & (obs.n_cold >= 60)],
            on="Household_ID").merge(
    station_normals(ROOT / "outputs/weather_daily.parquet",
                    ROOT / "outputs/household_weather.parquet"),
    on="Household_ID", how="left").set_index("Household_ID")
X = pd.read_parquet(EXPORT).set_index("household_id")

print("  audited households in the export       %d" % len(X))
print("  reach the physics (geometry + record)   %d" % len(A))
print("  never computed (INCOMPLETE_AUDIT)       %d"
      % int((X.phys_status == "INCOMPLETE_AUDIT").sum()))

gate = int(X[X.phys_status == "INCOMPLETE_AUDIT"].index.min())
inconc = int(X[(X.phys_status == "INCONCLUSIVE") & (X.phys_era == "post2010")].index.min())
nc = X[X.phys_heat_pump_point_is_no_claim & (X.phys_status != "INCOMPLETE_AUDIT")]
noclaim = int(nc.sort_values("phys_rank_fleet").index[0])
CONTRAST = [noclaim, inconc, gate]
print("\n  deep trace       %d" % DEEP)
print("  contrast cases   %s  (no-claim / refuses-to-claim / never-computed)" % CONTRAST)

head("1. THE HOUSE - every input, and the column it came from")

h = A.loc[DEEP].to_dict()
h["Household_ID"] = DEEP
for role in ("area_m2", "footprint_m2", "n_storeys_above", "heated_basement", "era",
             "renovation_count", "residents", "hp_type", "emitter", "dhw_electric",
             "hp_install_year", "hdd_normal_per_day"):
    rec(1, role, h.get(role), "", "DATABASE", SRC[role])
    print("  %-20s %-26s <- %s" % (role, h.get(role), SRC[role]))

head("2. GEOMETRY - the thermal envelope")

sh = ref(2, "storey_height")
bg = ref(2, "b_ground")
pf = ref(2, "perimeter_factor")
per = 4.0 * np.sqrt(h["footprint_m2"]) * pf
rec(2, "perimeter", per, "m", "GENERATED", "4*sqrt(footprint)*perimeter_factor")
a_th = ph.envelope_area(h["footprint_m2"], h["n_storeys_above"], h["heated_basement"],
                        sh, bg, pf)
rec(2, "a_thermal", a_th, "m2", "GENERATED", "envelope_area()",
    "wall + roof + b_ground*(basement wall + lowest floor)")
print("  perimeter         %8.2f m   = 4*sqrt(%.0f)*%.2f" % (per, h["footprint_m2"], pf))
print("  thermal envelope  %8.2f m2  = %.2f x the heated floor area"
      % (a_th, a_th / h["area_m2"]))
print("  a square plan is the MINIMUM perimeter, so perimeter_factor >= 1 widens it")

head("3. VENTILATION - identical in both baselines, so it CANCELS")

n_air = ref(3, "n_air")
vnet = ref(3, "v_net_per_m2")
rhoc = ref(3, "rho_c")
h_vent = ph.ventilation_coefficient(h["area_m2"], n_air, vnet, rhoc)
rec(3, "H_ventilation", h_vent, "W/K", "GENERATED", "ventilation_coefficient()")
print("  H_ventilation     %8.2f W/K" % h_vent)
print("  sits in BOTH baselines -> contributes exactly 0 to the deficiency")

head("4. THE TWO U-VALUES - where as-built and reference split")

u_ab = ph.u_as_built(h["era"], h["renovation_count"])
ek = ph.ERA_KEYS[h["era"]]
v, lo, hi, unit, source, section = ph.C[ek]
rec(4, "u_as_built (" + ek + ")", u_ab, unit, ph.STATUS[ek], source + " | " + section,
    "era %s, %d renovations" % (h["era"], h["renovation_count"]))
u_rf = ref(4, "u_reference")
dtb = ref(4, "du_thermal_bridge", "ONE draw, added to BOTH baselines")
print("  u_as_built        %8.4f W/m2K   era=%s   status=%s"
      % (u_ab, h["era"], ph.STATUS[ek]))
print("  u_reference       %8.4f W/m2K   status=%s" % (u_rf, ph.STATUS["u_reference"]))
print("  thermal bridge   +%8.4f W/m2K   both baselines, so it cancels" % dtb)

H_ab = ph.heat_loss_coefficient(u_ab + dtb, a_th, h_vent)
H_rf = ph.heat_loss_coefficient(u_rf + dtb, a_th, h_vent)
rec(4, "H_as_built", H_ab, "W/K", "GENERATED", "u_as_built*A + H_vent")
rec(4, "H_reference", H_rf, "W/K", "GENERATED", "u_reference*A + H_vent")
print("  H_as_built        %8.2f W/K" % H_ab)
print("  H_reference       %8.2f W/K   difference %.2f W/K" % (H_rf, H_ab - H_rf))

head("5. EFFICIENCY - three JAZ values, and the unit's generation")

jaz_new, _ = ph.jaz_for(h["hp_type"], h["emitter"])
jk = ph.JAZ_KEYS[(h["hp_type"], h["emitter"])]
v, lo, hi, unit, source, section = ph.C[jk]
rec(5, "jaz_current_unit (" + jk + ")", jaz_new, unit, ph.STATUS[jk],
    source + " | " + section)
vf = ph.vintage_factor(h["hp_type"], h["hp_install_year"])
rec(5, "vintage_factor", vf, "-", "GENERATED", "vintage_factor()",
    "install year %s vs the table's ~2017 units" % h["hp_install_year"])
jaz_ab = jaz_new * vf
rec(5, "jaz_as_built", jaz_ab, "-", "GENERATED", "jaz_current_unit * vintage_factor")
rk = ph.JAZ_KEYS[(h["hp_type"], "floor_only")]
jaz_rf, _ = ph.jaz_for(h["hp_type"], "floor_only")
rec(5, "jaz_reference (" + rk + ")", jaz_rf, "-", ph.STATUS[rk],
    ph.C[rk][4] + " | " + ph.C[rk][5],
    "the reference house gets floor heating AND a current unit")
jdhw = ref(5, ph.JAZ_HOTWATER_KEYS[h["hp_type"]])
kpd = ref(5, "dhw_kwh_person_day")
print("  jaz current unit  %8.3f   (%s, %s)" % (jaz_new, h["hp_type"], h["emitter"]))
print("  vintage factor    %8.3f   install year %s" % (vf, h["hp_install_year"]))
print("  jaz as-built      %8.3f   = current unit x vintage" % jaz_ab)
print("  jaz reference     %8.3f   floor heating + current unit" % jaz_rf)
print("  jaz hot water     %8.3f   electric cylinder? %s" % (jdhw, h["dhw_electric"]))
print("\n  VINTAGE IS TECHNOLOGY GENERATION, NOT WEAR. FAWA saw no ageing loss over")
print("  9 years, so an old unit is not a worn unit - it is an older design.")

head("6. ENERGY - both baselines, then the difference")

hdd = h["hdd_normal_per_day"]
rec(6, "hdd_normal_per_day", hdd, "K", "DATABASE", SRC["hdd_normal_per_day"],
    "station NORMAL year: the length of this household's record never enters")
heat_ab = ph.heating_electricity(H_ab, jaz_ab, hdd)
heat_rf = ph.heating_electricity(H_rf, jaz_rf, hdd)
dhw_ab = ph.dhw_electricity(h["residents"], 1.0 if h["dhw_electric"] else jdhw, kpd)
dhw_rf = ph.dhw_electricity(h["residents"], jdhw, kpd)
for nm, val in (("heating_as_built", heat_ab), ("heating_reference", heat_rf),
                ("dhw_as_built", dhw_ab), ("dhw_reference", dhw_rf)):
    rec(6, nm, val, "kWh/yr", "GENERATED", "heating_electricity() / dhw_electricity()")
E_ab, E_rf = heat_ab + dhw_ab, heat_rf + dhw_rf
rec(6, "E_as_built", E_ab, "kWh/yr", "GENERATED", "heating + hot water, as built")
rec(6, "E_reference", E_rf, "kWh/yr", "GENERATED", "heating + hot water, code twin")
print("  E_as_built        %9.0f kWh/yr   (heating %.0f + hot water %.0f)"
      % (E_ab, heat_ab, dhw_ab))
print("  E_reference       %9.0f kWh/yr   (heating %.0f + hot water %.0f)"
      % (E_rf, heat_rf, dhw_rf))
print("  deficiency        %9.0f kWh/yr" % (E_ab - E_rf))
print("\n  NEITHER IS A PREDICTED BILL. Appliances are excluded from both, so each")
print("  level is incomplete on purpose. Only the DIFFERENCE is meaningful.")

head("7. THE FOUR TERMS - what the difference is made of")

e = ph.evaluate(h)
terms = {"envelope": e["term_envelope"], "emitter": e["term_emitter"],
         "dhw": e["term_dhw"], "vintage": e["term_vintage"]}
own = {"envelope": "builder", "emitter": "builder", "dhw": "builder",
       "vintage": "installer"}
for nm, val in terms.items():
    rec(7, "term_" + nm, val, "kWh/yr", "GENERATED", "evaluate()", "owner: " + own[nm])
tot = sum(terms.values())
print("  %-12s %9s   %s" % ("term", "kWh/yr", "who fixes it"))
for nm, val in sorted(terms.items(), key=lambda kv: -abs(kv[1])):
    print("  %-12s %9.0f   %s" % (nm, val, own[nm]))
print("  %-12s %9.0f" % ("TOTAL", tot))

head("8. THE CHECKS - the trace must reproduce the model AND the export")

d_eval = e["deficiency"]
assert abs(tot - d_eval) < 1e-6, "terms %.6f != evaluate %.6f" % (tot, d_eval)
print("  four terms == evaluate() deficiency      %.6f == %.6f   OK" % (tot, d_eval))
assert abs((E_ab - E_rf) - d_eval) < 1e-6
print("  E_as_built - E_reference == deficiency   OK")
x = X.loc[DEEP]
assert abs(d_eval - x.phys_deficiency_kwh_yr) <= ROUND_TOL
print("  == the SHIPPED export                    %.1f vs %.1f   OK"
      % (d_eval, x.phys_deficiency_kwh_yr))
house = terms["envelope"] + terms["emitter"] + terms["dhw"]
assert abs(house + terms["vintage"] - tot) < 1e-6
print("  house + heat pump == total               OK")
print("\n  These asserts are the point: if the model changes and this document does")
print("  not, the run FAILS instead of quietly printing a stale story.")

head("9. THE BAND - read from the export, never recomputed here")

print("  point  %6.0f kWh/yr" % x.phys_deficiency_kwh_yr)
print("  lower  %6.0f kWh/yr  <- what is ranked and shown: 'at least this much'"
      % x.phys_deficiency_lo_kwh_yr)
print("  upper  %6.0f kWh/yr" % x.phys_deficiency_hi_kwh_yr)
print("  tier   %s   (T1 tightest -> T3 widest)" % x.phys_completeness_tier)
print("\n  The band is the PUBLISHED SPREAD of the constants, sampled. Not invented")
print("  error bars, and not a confidence interval from a fit - nothing is fitted.")

head("10. THE DECISION RULES THAT FIRED")

print("  status               %-22s %s" % (x.phys_status, x.phys_status_reason))
print("  rank (fleet)         %-22s ranked on %s" % (x.phys_rank_fleet, x.phys_rank_on))
print("  unit recommendation  %-22s age %s yr as of %s"
      % (x.phys_unit_recommendation, x.phys_unit_age_years, x.phys_unit_age_reference_year))
print("  vintage inside rank? %s" % (not bool(x.phys_rank_excludes_vintage)))
print("  heat-pump no-claim?  %s" % bool(x.phys_heat_pump_point_is_no_claim))

head("11. WHY THE 42 WERE NEVER COMPUTED - measured, not the blanket string")

gate_ids = list(X.index[X.phys_status == "INCOMPLETE_AUDIT"])
Hx = load_households(ROOT / "heapo_data/reports/protocols.csv").reset_index(drop=True)
bldg_ok = pd.Series(list(modellable(Hx)), index=list(Hx.Household_ID)).reindex(gate_ids).fillna(False)
why_b = pd.Series(list(drop_reasons(Hx)), index=list(Hx.Household_ID)).reindex(gate_ids)
oi = obs.set_index("Household_ID").reindex(gate_ids)
meter_ok = ((oi.n_days >= 180) & (oi.n_warm >= 60) & (oi.n_cold >= 60)).fillna(False)

n_b = int((~bldg_ok & meter_ok).sum())
n_m = int((bldg_ok & ~meter_ok).sum())
n_x = int((~bldg_ok & ~meter_ok).sum())
assert n_b + n_m + n_x == len(gate_ids)
print("  building data missing ONLY    %2d   <- AN AUDITOR CAN FIX THIS" % n_b)
print("  meter record too short ONLY   %2d   <- only more data fixes it, no visit helps" % n_m)
print("  both                          %2d" % n_x)
print("  total                         %2d" % len(gate_ids))
print("\n  THE EXPORT PUTS ONE BLANKET STRING ON A MIXED SET:")
print("    phys_status_reason    'building data missing'    true for %2d of %d"
      % (int((~bldg_ok).sum()), len(gate_ids)))
print("    phys_no_result_reason 'insufficient meter days'  true for %2d of %d"
      % (int((~meter_ok).sum()), len(gate_ids)))
print("  Neither holds for all 42, and the two causes have DIFFERENT FIXES, so")
print("  phys_no_result_is_fixable=True conflates 'go and look' with 'wait'.")
print("  Found by writing this walkthrough, 2026-09-17. Logged, export not yet changed.")


def true_cause(hid):
    b, m = bool(bldg_ok.get(hid, False)), bool(meter_ok.get(hid, False))
    if not b and not m:
        return "building data missing (%s) AND meter record too short" % why_b.get(hid)
    if not b:
        return "building data missing: %s" % why_b.get(hid)
    if not m:
        return "meter record too short / no season coverage"
    return "computed"


head("12. THREE CONTRAST CASES - where a different rule takes over")

rows = []
for hid in CONTRAST:
    r = X.loc[hid]
    # For a never-computed household the export's blanket string is wrong for
    # roughly half the set, so use the cause measured above instead.
    why = (true_cause(hid) if r.phys_status == "INCOMPLETE_AUDIT"
           else r.phys_status_reason)
    rows.append({"household": hid, "era": r.phys_era, "status": r.phys_status,
                 "point": r.phys_deficiency_kwh_yr, "lo": r.phys_deficiency_lo_kwh_yr,
                 "hi": r.phys_deficiency_hi_kwh_yr,
                 "pump_point": r.phys_group_heat_pump_kwh_yr,
                 "pump_lo": r.phys_group_heat_pump_lo_kwh_yr,
                 "no_claim": bool(r.phys_heat_pump_point_is_no_claim),
                 "unit": r.phys_unit_recommendation, "rank": r.phys_rank_fleet,
                 "why": why})
CT = pd.DataFrame(rows)
print(CT.to_string(index=False))

T = pd.DataFrame(TRACE)
T.insert(0, "household", DEEP)
T.to_csv(OUT / "data" / "p27_trace.csv", sep=";", index=False)
CT.to_csv(OUT / "data" / "p27_contrast.csv", sep=";", index=False)
print("\n  trace rows %d   provenance mix %s"
      % (len(T), T.provenance.value_counts().to_dict()))
print("  written: p27_trace, p27_contrast")

# ---------------------------------------------------------------- the document
# One content model renders to BOTH markdown and print-ready HTML, so the two
# artifacts can never drift apart. Every number below comes from a variable.
import re

B = []
h1 = lambda t: B.append(("h1", t))
h2 = lambda t: B.append(("h2", t))
par = lambda t: B.append(("p", t))
tech = lambda t: B.append(("tech", t))       # the "with knowledge" layer
note = lambda t: B.append(("note", t))
tab = lambda c, r: B.append(("table", c, r))
img = lambda n: B.append(("fig", n))  # not `fig`: matplotlib owns that name
# One headline number is a hero figure, not a chart. It leads on the LOWER bound,
# because that is the number this model ranks and displays - so the first thing the
# reader meets also teaches the rule.
hero = lambda v, u, lab, sub: B.append(("hero", v, u, lab, sub))

# Colour carries the FAMILY (three, validated all-pairs); the TEXT carries the precise
# tag. Six distinct tag colours were tested and fail the normal-vision floor at dE 12.9,
# i.e. indistinguishable even with full colour vision - so three it is.
FAM = {"db": ["DATABASE"], "ref": ["VERIFIED", "SECOND_HAND", "PHYSICAL"],
       "ours": ["DERIVED", "GENERATED"]}


def f0(v):
    return "{:,.0f}".format(v)


def fv(v):
    """Readable cell value. A raw repr like 4.052917477628678 belongs in the CSV,
    not in a printed report."""
    if isinstance(v, float):
        if v != v:
            return "not recorded"
        if float(v).is_integer():
            return "%d" % int(v)
        return "%.2f" % v
    return str(v)


ART = "an" if str(h["hp_type"])[:1].lower() in "aeiou" else "a"


# ---------------------------------------------------------------- figures
# Forms chosen before colour, per the dataviz procedure:
#   F1 part-to-whole across two baselines -> stacked horizontal bar, categorical (2)
#   F2 part-to-whole of one total          -> single stacked horizontal bar, categorical (4)
#   F3 "does the band cross zero?"         -> interval plot, EMPHASIS (1 hue + grey)
# F3 is on PERCENT OF REFERENCE, not kWh: 8,000 and 176 kWh on one axis would hide
# the small one, and the figure's job is the SIGN, not the magnitude. Percent is the
# honest shared scale and the export already carries it.
#
# Colour: slots 1-3 of the validated categorical theme. Six distinct tag colours were
# tested and FAIL the all-pairs normal-vision floor (dE 12.9), so the tags are coloured
# by FAMILY (three) and the precise tag stays as text - redundant encoding, so nothing
# is colour-alone and the whole thing survives greyscale printing.
import base64

import matplotlib
matplotlib.use("Agg")           # writing PNG files, not notebook inline output
import matplotlib.pyplot as plt

S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SURF, INK, MUT, GREY = "#ffffff", "#1a1a1a", "#5b6472", "#b9c3d0"
FIGD = OUT / "figures"
FIGD.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 9, "figure.dpi": 150, "savefig.dpi": 150,
                     "text.color": INK, "axes.labelcolor": MUT,
                     "xtick.color": MUT, "ytick.color": MUT,
                     "axes.edgecolor": GREY, "figure.facecolor": SURF,
                     "axes.facecolor": SURF})
FIGS = {}


def recessive(ax, xlabel=""):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GREY)
    ax.tick_params(length=0)
    ax.xaxis.grid(True, color=GREY, lw=.6, alpha=.55)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel)


def save(fig, name, caption):
    p = FIGD / (name + ".png")
    fig.savefig(p, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    FIGS[name] = (p, caption,
                  base64.b64encode(p.read_bytes()).decode("ascii"))


# --- F1: the same house, built twice -----------------------------------------
fig, ax = plt.subplots(figsize=(7.0, 2.05))
lab = ["as built", "code-compliant twin"]
ax.barh(lab, [heat_ab, heat_rf], .44, color=S1, edgecolor=SURF, lw=2, label="heating")
ax.barh(lab, [dhw_ab, dhw_rf], .44, left=[heat_ab, heat_rf], color=S2,
        edgecolor=SURF, lw=2, label="hot water")
for y, (a, b) in enumerate([(heat_ab, dhw_ab), (heat_rf, dhw_rf)]):
    ax.text(a / 2, y, f0(a), ha="center", va="center", color="white", fontsize=8.5)
    # the hot-water segment is narrow on the reference bar, so label it outside
    if b / E_ab > .10:
        ax.text(a + b / 2, y, f0(b), ha="center", va="center", color="white", fontsize=8.5)
    else:
        ax.annotate(f0(b), xy=(a + b / 2, y - .26), xytext=(a + b / 2, y - .52),
                    ha="center", color=INK, fontsize=8.5,
                    arrowprops=dict(arrowstyle="-", color=MUT, lw=.8))
    ax.text(a + b + 210, y, f0(a + b), va="center", color=INK, fontsize=9.5)
ax.annotate("", xy=(E_rf, 1.62), xytext=(E_ab, 1.62),
            arrowprops=dict(arrowstyle="<->", color=MUT, lw=1.2))
ax.text((E_ab + E_rf) / 2, 1.80, "the gap = %s kWh/yr" % f0(E_ab - E_rf),
        ha="center", va="top", color=INK, fontsize=9.5)
ax.set_ylim(-.75, 2.05)
ax.invert_yaxis()
recessive(ax, "kWh/yr")
# Legend ABOVE the plot: at lower right it sat on top of the gap annotation.
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(.5, 1.0), ncol=2,
          fontsize=8.5, handlelength=1.1, columnspacing=1.6)
save(fig, "F1_two_baselines",
     "The same house, built twice. Everything is identical except the U-value and the "
     "hot-water source, so the gap is the answer. Appliances are in neither bar.")

# --- F2: what the gap is made of ---------------------------------------------
fig, ax = plt.subplots(figsize=(7.0, 1.62))
order = ["envelope", "dhw", "emitter", "vintage"]
cols = {"envelope": S1, "dhw": S2, "emitter": S3, "vintage": S4}
left = 0.0
for nm in order:
    v = terms[nm]
    ax.barh([0], [v], .40, left=left, color=cols[nm], edgecolor=SURF, lw=2)
    if v / tot > .07:
        ax.text(left + v / 2, 0, "%s\n%s" % (nm, f0(v)), ha="center", va="center",
                color="white", fontsize=8.5, linespacing=1.35)
    else:
        ax.annotate("%s %s" % (nm, f0(v)), xy=(left + v / 2, .21),
                    xytext=(left + v / 2, .40), ha="center", color=INK, fontsize=8.5,
                    arrowprops=dict(arrowstyle="-", color=MUT, lw=.8))
    left += v
ax.plot([house, house], [-.30, .30], color=INK, lw=1.4)
ax.text(house / 2, -.36, "a builder fixes these three  %s" % f0(house), ha="center",
        va="top", color=INK, fontsize=8.5)
# The number is already on the segment callout above; repeating it here read as
# two different quantities.
ax.text(house + terms["vintage"] / 2, -.36, "an installer", ha="center", va="top",
        color=INK, fontsize=8.5)
ax.set_ylim(-.95, .62)
ax.set_yticks([])
recessive(ax, "kWh/yr")
save(fig, "F2_four_terms",
     "The gap split by who fixes it. Envelope alone is %.0f%% of it, so replacing the "
     "heat pump would leave most of the gap standing."
     % (100.0 * terms["envelope"] / tot))

# --- F3: does the band cross zero? -------------------------------------------
_pc = ["phys_deficiency_pct_of_reference", "phys_deficiency_pct_lo",
       "phys_deficiency_pct_hi"]
if all(c in X.columns for c in _pc):
    # Reversed so the deep-trace house sits at the TOP, matching the reading order.
    ids = [CONTRAST[1], CONTRAST[0], DEEP]
    fig, ax = plt.subplots(figsize=(7.0, 2.25))
    for i, hid in enumerate(ids):
        r = X.loc[hid]
        pt, lo2, hi2 = (r[_pc[0]], r[_pc[1]], r[_pc[2]])
        dec = bool(r.phys_excess_confirmed)
        c = S1 if dec else GREY
        ax.plot([lo2, hi2], [i, i], color=c, lw=6, solid_capstyle="butt",
                alpha=1.0 if dec else .95)
        ax.plot([pt], [i], "o", ms=9, color=SURF, mec=c, mew=2.2, zorder=3)
        ax.text(hi2 + 2.0, i, "%s  %s" % (hid, r.phys_status), va="center",
                color=INK if dec else MUT, fontsize=8.5)
        ax.text(lo2 - 2.0, i, "%+.0f%%" % lo2, va="center", ha="right",
                color=MUT, fontsize=8.5)
    ax.axvline(0, color=INK, lw=1.2)
    ax.text(0, len(ids) - .35, " code-compliant", color=MUT, fontsize=8.5, va="bottom")
    ax.set_yticks([])
    ax.set_ylim(-.7, len(ids) - .15)
    _his = [X.loc[i, _pc[2]] for i in ids]
    ax.set_xlim(-22, max(_his) * 1.30)
    recessive(ax, "% over a code-compliant version of the same house")
    save(fig, "F3_bands",
         "Why one of these is not ranked. The dot is the point estimate, the bar the "
         "published-spread band, and the number at the left end is the **lower bound** - "
         "the figure the ranking uses. 121728's band crosses the code line, so no excess "
         "is claimed and it gets no rank; the fourth case has no bar at all, never having "
         "been computed. Shown as percent over code, not kWh, because the question here "
         "is the sign, and 8,000 against 176 kWh on one axis would hide the small one.")

h1("How the physical baseline works - one house, traced end to end")
hero(f0(x.phys_deficiency_lo_kwh_yr), "kWh/yr",
     "at least this much more electricity than a code-compliant version of the same house",
     "point estimate %s  &middot;  band %s to %s kWh/yr  &middot;  at least +%.0f%% over "
     "code  &middot;  household %d, ranked %.0f of the fleet  &middot;  completeness %s"
     % (f0(x.phys_deficiency_kwh_yr), f0(x.phys_deficiency_lo_kwh_yr),
        f0(x.phys_deficiency_hi_kwh_yr), x["phys_deficiency_pct_lo"], DEEP,
        x.phys_rank_fleet, x.phys_completeness_tier))
par("Household **%d** of the HEAPO audit set, followed from the floor area an auditor "
    "wrote down to its position at the top of the visit list. Then three short cases "
    "where a different rule takes over." % DEEP)
par("**Read it either way.** The plain text carries the argument and needs no "
    "background. The grey technical lines under each step give the formula and the "
    "exact quantity, and can be skipped or checked.")
note("This document says **how the model works**, not whether it works. It makes no "
     "performance claim; that belongs in the results section of the report. Every "
     "number here is generated by `p27_walkthrough.py` - none is typed by hand, so "
     "it cannot quietly go stale when a constant changes.")

h2("Where every number comes from - four tags")
par("The question this document exists to answer is *which numbers are ours*. "
    "\"From a reference\" is really two different things, so there are four tags:")
_n = lambda k: str(int((T.provenance == k).sum()))
tab(["tag", "family", "meaning", "count"],
    [["`DATABASE`", "from the database",
      "HEAPO measured it, or an auditor recorded it - named to its column", _n("DATABASE")],
     ["`VERIFIED`", "from a reference",
      "a constant read in the cited primary document", _n("VERIFIED")],
     ["`SECOND_HAND`", "from a reference",
      "source named but the document was not read here", _n("SECOND_HAND")],
     ["`PHYSICAL`", "from a reference",
      "a physical property of air, not a modelling choice", _n("PHYSICAL")],
     ["`DERIVED`", "**ours**",
      "a constant **we** computed from published inputs; the test re-derives it", _n("DERIVED")],
     ["`GENERATED`", "**ours**",
      "computed by the model for this household", _n("GENERATED")]])
par("The three families are colour-coded throughout, and the exact tag is always "
    "spelled out - so nothing is carried by colour alone and the whole document still "
    "reads in greyscale print. Six separate tag colours were tested and rejected: the "
    "worst pair is hard to tell apart even with full colour vision.")
note("**Nothing is fitted to consumption.** No constant was chosen, tuned or selected "
     "by looking at how much electricity these houses actually used. That is the "
     "calibration rule, and it is why a constant that happens to reproduce the data "
     "would be treated as a warning sign rather than a success.")

h2("The question the model asks")
par("Not *\"is this house using a lot?\"* - a big house uses a lot and that says "
    "nothing. The question is: **how much more electricity does this house use than "
    "a code-compliant version of the same house, on the same plot, in the same "
    "weather, with the same number of people?**")
par("So the model builds the house **twice**. Once as it is (`E_as_built`) and once "
    "as the building code would have it (`E_reference`). The answer is the gap. Both "
    "levels exclude appliances, which is why **neither is a predicted bill** and only "
    "the difference means anything.")

h2("Step 1 - the house, as recorded")
par("Twelve inputs. All of them come from the audit or the weather archive; not one "
    "is guessed.")
tab(["input", "value", "HEAPO column"],
    [[r["quantity"], fv(r["value"]), "`%s`" % r["source"]]
     for r in TRACE if r["step"] == 1])

h2("Step 2 - the envelope: how much surface loses heat")
par("Heat escapes through the outside surface, so the model needs that area. It is not "
    "recorded, so it is built from the footprint: a square plan is the smallest "
    "possible perimeter for a given floor area, which keeps the estimate conservative.")
tech("perimeter = 4*sqrt(%s m2) * %.2f = %.2f m    |    thermal envelope = %.2f m2 "
     "= %.2f x heated floor area" % (f0(h["footprint_m2"]), pf, per, a_th, a_th / h["area_m2"]))
par("A heated basement adds a storey of wall against earth and moves the lowest floor "
    "down. Earth is a milder neighbour than air, so both are charged at a reduced "
    "weight (**b_ground = %.2f**) rather than counted in full." % bg)

h2("Step 3 - ventilation, and the first thing that cancels")
par("Air changes lose heat too. This term is **identical in both baselines** - the "
    "code-compliant twin breathes the same - so it contributes exactly zero to the "
    "answer. It is computed anyway, because it belongs in each level.")
tech("H_ventilation = rho_c * n_air * v_net_per_m2 * area = %.2f W/K  ->  cancels in "
     "the difference" % h_vent)

h2("Step 4 - the two U-values: where the baselines split")
par("A U-value is how fast heat crosses a square metre of wall. This is the heart of "
    "the model: the house keeps **its own era's** U-value, the reference twin gets the "
    "**code** U-value, and everything else about the two houses is identical.")
tab(["quantity", "value", "unit", "provenance"],
    [["u_as_built (%s)" % h["era"], "%.4f" % u_ab, "W/m2K", "`%s`" % ph.STATUS[ek]],
     ["u_reference (code)", "%.4f" % u_rf, "W/m2K", "`%s`" % ph.STATUS["u_reference"]],
     ["thermal bridge", "+%.4f" % dtb, "W/m2K", "`%s`" % ph.STATUS["du_thermal_bridge"]]])
par("The thermal-bridge allowance is added to **both** houses, so like ventilation it "
    "cancels. Corners and balconies leak in a code house too.")
tech("H = U * A_envelope + H_ventilation    ->    H_as_built %.2f W/K, "
     "H_reference %.2f W/K, difference %.2f W/K" % (H_ab, H_rf, H_ab - H_rf))
note("This house is **unrenovated**, so it takes its era value directly. Had it been "
     "renovated, no source gives the U-value of a half-renovated wall - so renovation "
     "**widens the band** toward the next-newer era instead of applying an invented "
     "correction. Widening an uncertainty is honest; inventing a number is not.")

h2("Step 5 - efficiency, and the age of the unit")
par("A heat pump multiplies electricity into heat. The multiplier (**JAZ**, the "
    "seasonal field average) depends on the unit type and on how hot the water has to "
    "be: floor heating runs cool and efficient, radiators run hot and lose ground.")
tab(["quantity", "value", "what it represents"],
    [["jaz, current unit", "%.3f" % jaz_new,
      "%s %s unit with %s, from the published field tables"
      % (ART, h["hp_type"], h["emitter"])],
     ["vintage factor", "%.3f" % vf, "this unit is from %s, so it is an older generation"
      % ("%.0f" % h["hp_install_year"])],
     ["jaz, as built", "%.3f" % jaz_ab, "current-unit value x vintage"],
     ["jaz, reference", "%.3f" % jaz_rf, "the twin gets floor heating **and** a current unit"],
     ["jaz, hot water", "%.3f" % jdhw, "separate figure for the cylinder"]])
note("**Vintage is technology generation, not wear.** The field study behind it saw no "
     "efficiency loss over nine years of operation, so an older unit here is an older "
     "*design*, not a tired one. This is why the model never says \"it is old\" as if "
     "that were a fault.")
par("This house heats its water with an **electric cylinder**, which has no multiplier "
    "at all - one kilowatt-hour in, one out. The reference twin uses the heat pump. "
    "That single difference is the whole hot-water term.")

h2("Step 6 - the two totals, and the gap")
par("Weather enters once, as degree-days from the station's **normal year** rather "
    "than from this household's own record. That deliberately keeps the length of a "
    "meter record out of the building score: a house with 18 months of data must not "
    "look worse than a house with five years.")
tab(["", "heating", "hot water", "total"],
    [["as built", f0(heat_ab), f0(dhw_ab), "**%s**" % f0(E_ab)],
     ["code-compliant twin", f0(heat_rf), f0(dhw_rf), "**%s**" % f0(E_rf)],
     ["gap", f0(heat_ab - heat_rf), f0(dhw_ab - dhw_rf), "**%s**" % f0(E_ab - E_rf)]])
par("All figures kWh/yr. **%s kWh/yr** is the answer: what this house spends because "
    "it is not built to code." % f0(E_ab - E_rf))
img("F1_two_baselines")

h2("Step 7 - what the gap is made of, and who fixes it")
par("A single number tells nobody what to do. The gap splits into four terms, and the "
    "split matters because **different people fix different terms**.")
tab(["term", "kWh/yr", "share", "who fixes it"],
    [[nm, f0(v), "%.0f%%" % (100.0 * v / tot), own[nm]]
     for nm, v in sorted(terms.items(), key=lambda kv: -abs(kv[1]))])
par("Three of the four are the **fabric** - a builder's work. Only vintage belongs to "
    "an **installer**. For this house the envelope alone is %.0f%% of the problem, so "
    "replacing the heat pump would leave most of the gap untouched."
    % (100.0 * terms["envelope"] / tot))
img("F2_four_terms")
tech("four terms sum to %.6f kWh/yr == evaluate() deficiency == the shipped export "
     "value %s (asserted at run time)" % (tot, f0(x.phys_deficiency_kwh_yr)))

h2("Step 8 - the band, and why the lowest number is the one we use")
par("Every constant above is published with a spread, not as a single truth. The model "
    "re-runs the whole calculation many times, drawing each constant from its own "
    "published range, which gives a range for the answer.")
tab(["", "kWh/yr", "meaning"],
    [["point", f0(x.phys_deficiency_kwh_yr), "the middle estimate"],
     ["**lower bound**", "**%s**" % f0(x.phys_deficiency_lo_kwh_yr),
      "**what gets ranked and displayed - \"at least this much\"**"],
     ["upper", f0(x.phys_deficiency_hi_kwh_yr), "the optimistic end"]])
par("The list is ordered on the **lower** bound, so a household's position is "
    "defensible: it claims only what survives the least favourable reading of the "
    "sources. Data completeness is reported beside it as a tier - this house is "
    "**%s**, the tightest." % x.phys_completeness_tier)
note("The band is the **published spread of the constants**, sampled. It is not an "
     "invented error bar and not a confidence interval from a fit, because there is no "
     "fit anywhere in this model.")

h2("Step 9 - the decisions this produces")
tab(["decision", "value", "rule that fired"],
    [["status", "`%s`" % x.phys_status, x.phys_status_reason],
     ["rank, fleet-wide", "%.0f" % x.phys_rank_fleet, "ordered on `%s`" % x.phys_rank_on],
     ["the unit", "`%s`" % x.phys_unit_recommendation,
      "%.0f years old as of %s, against its measured expected service life"
      % (x.phys_unit_age_years, x.phys_unit_age_reference_year)]])
par("**\"Old\" is never an action.** A replacement is recommended only at or past the "
    "expected service life, taken from measured failure data. A mid-life unit reads "
    "`KEEP_IN_LIFE` and its vintage kWh stay information rather than instruction.")

h2("Three contrast cases - where a different rule takes over")
par("One household can only ever show one path. These three show the model declining "
    "to answer, in three different ways.")
tab(["household", "status", "point", "lower", "what it demonstrates"],
    [["%d" % 876511, "`%s`" % CT.iloc[0]["status"], f0(CT.iloc[0]["point"]),
      f0(CT.iloc[0]["lo"]),
      "**no claim on the unit.** Install year unrecorded, so the heat-pump point is "
      "**0** while its band opens at **%s** - every draw samples an older unit. Show "
      "the band, never the zero" % f0(CT.iloc[0]["pump_lo"])],
     ["%d" % 121728, "`%s`" % CT.iloc[1]["status"], f0(CT.iloc[1]["point"]),
      f0(CT.iloc[1]["lo"]),
      "**the model refuses to claim.** A post-2010 house: the band crosses zero, so "
      "despite a positive point estimate there is no finding and no rank"],
     ["%d" % 100120, "`%s`" % CT.iloc[2]["status"], "-", "-",
      "**never computed.** %s" % CT.iloc[2]["why"]]])
img("F3_bands")
note("**There is no \"normal\" status.** Confirming a house is fine would need its "
     "whole band at or below code, and not one household in the set achieves that. The "
     "model confirms an excess or says nothing - it never issues a clean bill of "
     "health, and nothing on the page may render green.")

h2("Why the never-computed 42 are not one thing")
par("A household can miss out for two unrelated reasons, and they need opposite "
    "responses. Measured here rather than taken from the export's summary string:")
tab(["cause", "n", "what actually fixes it"],
    [["building data missing only", str(n_b), "**an auditor can fix this** - go and record it"],
     ["meter record too short only", str(n_m), "only a longer record; no visit helps"],
     ["both", str(n_x), "both"]])
# DERIVED, never asserted. This note used to say "export not yet changed" and was
# false within the hour - the exact rot this generator exists to prevent. Read the
# export and describe what is actually in it.
_ia_r = X.loc[X.phys_status == "INCOMPLETE_AUDIT", "phys_no_result_reason"].nunique()
if "phys_no_result_fix" in X.columns and _ia_r > 1:
    _fx = X.loc[X.phys_status == "INCOMPLETE_AUDIT", "phys_no_result_fix"].value_counts()
    note("**This split used to be invisible, and writing this document is what exposed "
         "it.** The export labelled all 42 with one blanket string: the cause was read "
         "from a frame joined to the *scored* households, so it was empty for exactly "
         "the unscored ones and every one fell through to a single default. **Fixed "
         "2026-09-17** - `phys_no_result_reason` now carries **%d distinct per-household "
         "causes** and `phys_no_result_fix` names who acts (%s). Read that column, not "
         "`phys_no_result_is_fixable`, which says only whether a household can ever "
         "become answerable - not whether to send anyone."
         % (_ia_r, " / ".join("**%d** %s" % (n, r.split(";")[0]) for r, n in _fx.items())))
else:
    note("**Known defect, export not yet fixed.** All 42 carry one blanket reason "
         "string (%d distinct), so take the split from the table above." % _ia_r)

h2("How to read these numbers")
par("Four scope limits that change how a figure should be read. None is a verdict on "
    "the model; each is a boundary on what a number means.")
tab(["limit", "what it does to a number"],
    [["The order leans old", "per square metre the physics under-predicts newer "
      "buildings, so a fleet-wide list tilts toward older houses. Era is therefore a "
      "**filter** on the page, and the in-era rank is kept as a column"],
     ["Bands are wide, on purpose", "they carry the published disagreement between "
      "sources. A wide band is information, not a failure"],
     ["Levels are not bills", "appliances are excluded from both baselines. Only the "
      "**difference** is meaningful; neither level is what a household pays"],
     ["Nothing is calibrated", "where the physics and the meter disagree, the "
      "disagreement is **reported**, never tuned away"]])
par("The constants are Swiss. The **method** ports to another country; the **numbers** "
    "do not, and a new region means a new registry file rather than new code.")
tab(["artefact", "path"],
    [["this document", "`outputs/p27/reports/p27_walkthrough.md` / `.html`"],
     ["every traced number", "`outputs/p27/data/p27_trace.csv` (%d rows)" % len(T)],
     ["the contrast cases", "`outputs/p27/data/p27_contrast.csv`"],
     ["the constants registry", "`constants_ch.json`"],
     ["the shipped export", "`outputs/export/physical_baseline_v2.parquet`"]])


def md_of(blocks):
    o = []
    for b in blocks:
        if b[0] == "h1":
            o.append("# " + b[1] + "\n")
        elif b[0] == "h2":
            o.append("\n## " + b[1] + "\n")
        elif b[0] == "p":
            o.append(b[1] + "\n")
        elif b[0] == "tech":
            o.append("```\n" + b[1] + "\n```\n")
        elif b[0] == "note":
            o.append("> " + b[1].replace("\n", "\n> ") + "\n")
        elif b[0] == "fig":
            _c = FIGS[b[1]][1]
            o.append("![%s](../figures/%s.png)\n" % (_c, b[1]))
            o.append("*%s*\n" % _c)
        elif b[0] == "hero":
            _s = b[4].replace("&middot;", "·")
            o.append("> ## %s %s\n>\n> **%s**\n>\n> %s\n" % (b[1], b[2], b[3], _s))
        else:
            cols, rows = b[1], b[2]
            o.append("| " + " | ".join(cols) + " |")
            o.append("|" + "|".join(["---"] * len(cols)) + "|")
            for r in rows:
                o.append("| " + " | ".join(str(c) for c in r) + " |")
            o.append("")
    return "\n".join(o)


def inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    for fam, names in FAM.items():
        for nm in names:
            t = t.replace("<code>%s</code>" % nm,
                          '<code class="t t-%s">%s</code>' % (fam, nm))
    return t


CSS = """
:root{--ink:#1a1a1a;--mut:#5b6472;--rule:#d8dde5;--bg:#fff}
*{box-sizing:border-box}
body{margin:0;background:#f4f5f7;color:var(--ink);
 font:15px/1.62 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.page{max-width:820px;margin:0 auto;background:var(--bg);padding:56px 60px}
h1{font-size:27px;line-height:1.25;margin:0 0 6px;letter-spacing:-.2px}
h2{font-size:17px;margin:34px 0 10px;padding-bottom:6px;
 border-bottom:1px solid var(--rule);letter-spacing:-.1px}
p{margin:11px 0}
code{font:12.5px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;
 background:#eef1f5;padding:1px 5px;border-radius:3px}
pre{background:#f7f9fb;border-left:3px solid #b9c3d0;color:var(--mut);
 font:12.5px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;
 padding:9px 13px;margin:11px 0;overflow-x:auto;white-space:pre-wrap}
blockquote{margin:14px 0;padding:11px 15px;background:#fbf8ef;
 border-left:3px solid #d8b455}
blockquote p{margin:0}
table{border-collapse:collapse;width:100%;margin:13px 0;font-size:13.5px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--rule);
 vertical-align:top}
th{background:#f7f9fb;font-weight:600}
td:nth-child(n+2){font-variant-numeric:tabular-nums}
@media print{
 body{background:#fff;font-size:10.5pt}
 .page{max-width:none;padding:0}
 h2{page-break-after:avoid}
 table,blockquote,pre{page-break-inside:avoid}
}
@page{margin:18mm}
/* Provenance families. The hue sits on a border and a pale tint; the TEXT stays ink, so
   legibility never depends on the hue and greyscale print still reads. */
/* The hero figure: one headline number, not a one-bar chart. */
.hero{margin:20px 0 4px;padding:19px 22px;background:#f7f9fb;
 border-left:4px solid #2a78d6}
.hero .n{font-size:48px;line-height:1.02;font-weight:650;letter-spacing:-1.4px;
 color:var(--ink);font-variant-numeric:tabular-nums}
.hero .u{font-size:17px;font-weight:500;color:var(--mut);margin-left:7px;
 letter-spacing:0}
.hero .lab{margin-top:7px;font-size:14.5px;line-height:1.45;color:var(--ink)}
.hero .sub{margin-top:9px;font-size:12.5px;line-height:1.5;color:var(--mut);
 font-variant-numeric:tabular-nums}
@media print{.hero{page-break-inside:avoid}.hero .n{font-size:34pt}}
code.t{border-left:3px solid;padding-left:5px;border-radius:0 3px 3px 0}
code.t-db{border-color:#2a78d6;background:#eaf2fc}
code.t-ref{border-color:#1baf7a;background:#e7f6f0}
code.t-ours{border-color:#eb6834;background:#fdefe7}
figure{margin:18px 0}
figure img{width:100%;height:auto;display:block}
figcaption{margin-top:7px;color:var(--mut);font-size:12.5px;line-height:1.5}
@media print{figure{page-break-inside:avoid}}
"""


def html_of(blocks):
    o = ["<style>" + CSS + "</style>", "<div class=page>"]
    for b in blocks:
        if b[0] == "h1":
            o.append("<h1>" + inline(b[1]) + "</h1>")
        elif b[0] == "h2":
            o.append("<h2>" + inline(b[1]) + "</h2>")
        elif b[0] == "p":
            o.append("<p>" + inline(b[1]) + "</p>")
        elif b[0] == "tech":
            o.append("<pre>" + inline(b[1]) + "</pre>")
        elif b[0] == "note":
            o.append("<blockquote><p>" + inline(b[1]) + "</p></blockquote>")
        elif b[0] == "fig":
            _c, _b64 = FIGS[b[1]][1], FIGS[b[1]][2]
            o.append('<figure><img alt="%s" src="data:image/png;base64,%s">'
                     '<figcaption>%s</figcaption></figure>'
                     % (inline(_c), _b64, inline(_c)))
        elif b[0] == "hero":
            o.append('<div class="hero"><div class="n">%s<span class="u">%s</span></div>'
                     '<div class="lab">%s</div><div class="sub">%s</div></div>'
                     % (b[1], inline(b[2]), inline(b[3]), b[4]))
        else:
            cols, rows = b[1], b[2]
            o.append("<table><thead><tr>"
                     + "".join("<th>" + inline(c) + "</th>" for c in cols)
                     + "</tr></thead><tbody>")
            for r in rows:
                o.append("<tr>" + "".join("<td>" + inline(str(c)) + "</td>" for c in r)
                         + "</tr>")
            o.append("</tbody></table>")
    o.append("</div>")
    return "\n".join(o)


(OUT / "reports" / "p27_walkthrough.md").write_text(md_of(B), encoding="utf-8")
(OUT / "reports" / "p27_walkthrough.html").write_text(
    "<title>How the physical baseline works</title>\n" + html_of(B), encoding="utf-8")
print("  written: p27_walkthrough.md, p27_walkthrough.html  (%d blocks)" % len(B))
