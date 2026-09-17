"""P11 - the dashboard export, SCHEMA v2. Building-side only, three groups, one list.

SETTLED WITH MIGUEL 2026-09-12 (CLAUDE.md section P26, interviewed before any code).

WHAT THIS IS FOR. The dashboard binds to one table while the model keeps changing, so
the CONTRACT is the schema, not the numbers. v1 stays on disk for one cycle beside v2.

ONE SECTION, TWO PAGES, and this file feeds both:
  page 1  explains the rank and names the owner - builder, installer, or both
  page 2  ONE FLEET-WIDE LIST with three columns: house / heat pump / total

  house      envelope + emitter + DHW   -> a builder
  heat pump  vintage + life-cycle call  -> an installer: replace, plan, or keep
  total      house + heat pump          -> the rank

BUILDING SIDE ONLY. No heating slope and no fault percentage belong on those pages.
Aaditya's fault model is not loaded anywhere in this workstream (removed 2026-09-12);
the two models meet only in a FINAL TARGET OVERVIEW, each keeping its own column. The
visit-axis columns stay in this export for that overview to consume, HIDDEN from our
two pages.

THERE IS NO "NORMAL" STATE. It would need a household's whole band at or below code, and
not one is. We confirm an excess, never its absence: the low end is the ABSENCE OF A
FINDING.

  HIGH_EXCESS       confirmed excess, worst 25% FLEET-WIDE     -> act
  EXCESS_CONFIRMED  confirmed excess, below the action cut     -> real, not first
  INCONCLUSIVE      computed, band straddles zero              -> no claim
  INCOMPLETE_AUDIT  never computed - MIXED CAUSE, per household: building data
                    missing (an auditor can fix) or meter record too short (only a
                    longer record fixes it). See phys_no_result_fix for who acts.

THE PRIMARY ORDER IS FLEET-WIDE (Miguel 2026-09-12), which OVERRIDES the standing
"rank within era, never fleet-wide" rule. Declared with it: P9/P21 measured that per m2
the physics under-predicts newer eras by 24-53%, so a fleet-wide list tilts toward older
houses. The mitigations are all in this file: era is a column and a filter,
`phys_rank_in_era` is kept, and `phys_rank_bias_note` ships the caveat.

ACT-FIRST IS OPTION A: `term_vintage` counts in the total, but NOT in the ranking value
for units we would KEEP. A 10-year-old unit must never push a near-compliant post-2010
house onto the act list.

RULES BUILT INTO THE FILE, NOT LEFT TO A README.
  1. ALL 214 HOUSEHOLDS APPEAR. Unjudged is not judged normal.
  2. EVERY ENERGY FIGURE TRAVELS WITH ITS BAND - now per group.
  3. THE CAPACITY SCENARIO IS NEVER SUMMED INTO THE HEADLINE.
  4. THE LEVEL IS NOT A PREDICTION - it excludes appliance electricity, and appliances
     never enter the model at all.
  5. NO FAULT COLUMN EXISTS IN THIS FILE.

Run order: p22_registry -> p24_lifecycle -> p13 -> p11.

numpy + pandas only.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph
from p_adapter_heapo import (load_households, modellable, drop_reasons,
                             daily_observations, station_normals)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs" / "export"
OUT.mkdir(parents=True, exist_ok=True)
(HERE / "outputs" / "p11" / "logs").mkdir(parents=True, exist_ok=True)

SCHEMA_VERSION = "physical_baseline_v2"
PREVIOUS_VERSION = "physical_baseline_v1"      # stays on disk for one cycle
NDRAW = 400
RNG = np.random.default_rng(20260910)
DELTA_LO, DELTA_MID, DELTA_HI = 0.05, 0.10, 0.15
# The action cut is a RANKING choice, not physics. Declared here, adjustable.
PRIORITY_FRACTION = 0.25
AGE_REFERENCE_YEAR = 2024        # ages are as of the END OF THE METER DATA, not today
BIAS_NOTE = ("ranked fleet-wide; per m2 the physics under-predicts newer construction "
             "eras by 24-53% (P9/P21), so this order tilts toward older houses - filter "
             "by phys_era or use phys_rank_in_era")
UNIT_RECOMMENDATIONS = {"REPLACE_END_OF_LIFE", "PLAN_REPLACEMENT", "KEEP_IN_LIFE",
                        "RECORD_INSTALL_YEAR"}
VISIT_STATES = {"SLOPE_EXCESS", "INCONCLUSIVE", "USES_LESS_THAN_MODELLED",
                "NOT_ASSESSABLE"}
STATES = {"HIGH_EXCESS", "EXCESS_CONFIRMED", "INCONCLUSIVE", "INCOMPLETE_AUDIT"}
NO_RESULT = ["INCONCLUSIVE", "INCOMPLETE_AUDIT"]


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


sys.stdout = Tee(HERE / "outputs" / "p11" / "logs" / "p11_run.txt")

head("1. BUILD - every household, none dropped, normal-year weather")

H = load_households(ROOT / "heapo_data/reports/protocols.csv")
ok = modellable(H)
H["drop_reason"] = drop_reasons(H)
obs = daily_observations(ROOT / "outputs/daily_states.parquet",
                         ROOT / "outputs/household_weather.parquet")
suff = obs[(obs.n_days >= 180) & (obs.n_warm >= 60) & (obs.n_cold >= 60)]
H = H.merge(suff, on="Household_ID", how="left").merge(
    station_normals(ROOT / "outputs/weather_daily.parquet",
                    ROOT / "outputs/household_weather.parquet"),
    on="Household_ID", how="left")
H["scoreable"] = ok & H.n_days.notna() & H.hdd_normal_per_day.notna()
print("  households in protocols.csv : %d" % len(H))
print("  modellable                  : %d" % int(ok.sum()))
print("  ...with sufficient days     : %d" % int(H.scoreable.sum()))
print("  INCOMPLETE_AUDIT            : %d" % int((~H.scoreable).sum()))

REC = HERE / "outputs" / "p24" / "data" / "p24_unit_recommendation.parquet"
if not REC.exists():
    raise SystemExit("p24_unit_recommendation.parquet missing - run p24_lifecycle.py first")
R = pd.read_parquet(REC).set_index("Household_ID")
H["unit_recommendation"] = H.Household_ID.map(R.unit_recommendation)
H["unit_age_years"] = H.Household_ID.map(R.unit_age_years)

S = H[H.scoreable].copy()
recs = S.to_dict("records")
KEYS = ["E_as_built", "E_reference", "deficiency", "term_envelope", "term_emitter",
        "term_dhw", "term_vintage", "vintage_factor", "H_as_built", "jaz_as_built",
        "design_kw", "huellzahl", "hdd_corrected"]
ev = [ph.evaluate(r) for r in recs]
for k in KEYS:
    S[k] = [e[k] for e in ev]
S["tier"] = [ph.completeness_tier(r) for r in recs]
S["group_house"] = S.term_envelope + S.term_emitter + S.term_dhw
S["group_heat_pump"] = S.term_vintage
# OPTION A: the ranking value drops vintage for units we would keep anyway.
keep = S.unit_recommendation.eq("KEEP_IN_LIFE").to_numpy()
S["rank_metric"] = np.where(keep, S.deficiency - S.term_vintage, S.deficiency)

acc = {k: np.zeros((len(recs), NDRAW)) for k in
       ["deficiency", "group_house", "group_heat_pump", "rank_metric"]}
for j in range(NDRAW):
    for i, r in enumerate(recs):
        e = ph.evaluate(r, RNG)
        h_ = e["term_envelope"] + e["term_emitter"] + e["term_dhw"]
        acc["deficiency"][i, j] = e["deficiency"]
        acc["group_house"][i, j] = h_
        acc["group_heat_pump"][i, j] = e["term_vintage"]
        acc["rank_metric"][i, j] = (e["deficiency"] - e["term_vintage"] if keep[i]
                                    else e["deficiency"])
for k, a in acc.items():
    S[k + "_lo"] = np.percentile(a, 2.5, axis=1)
    S[k + "_hi"] = np.percentile(a, 97.5, axis=1)
S["band"] = S.deficiency_hi - S.deficiency_lo
print("  record length never enters Category B: max |hdd - station normal| = %.2e"
      % (S.hdd_corrected - S.hdd_normal_per_day).abs().max())


def cap(dmax):
    ratio = S.installed_kw / S.design_kw
    heat = ph.heating_electricity(S.H_as_built, S.jaz_as_built, S.hdd_corrected)
    return heat * np.clip((ratio - 1.0) / 1.0, 0, 1) * dmax


for tag, d in [("lo", DELTA_LO), ("mid", DELTA_MID), ("hi", DELTA_HI)]:
    S["cap_" + tag] = cap(d)

head("2. STATUS AND THE FLEET-WIDE ORDER")

S["excess_confirmed"] = S.deficiency_lo > 0
conf = S[S.excess_confirmed]
S["rank_fleet"] = conf.rank_metric_lo.rank(ascending=False, method="min")
S["rank_in_era"] = conf.groupby("era").rank_metric_lo.rank(ascending=False, method="min")
n_conf = int(S.excess_confirmed.sum())
S["priority"] = S.excess_confirmed & (S.rank_fleet <= np.ceil(n_conf * PRIORITY_FRACTION))
S["status"] = np.where(S.priority, "HIGH_EXCESS",
                       np.where(S.excess_confirmed, "EXCESS_CONFIRMED", "INCONCLUSIVE"))
pct = int(100 * PRIORITY_FRACTION)
S["status_reason"] = np.select(
    [S.status == "HIGH_EXCESS", S.status == "EXCESS_CONFIRMED"],
    ["confirmed excess over code, in the worst %d%% of the fleet by lower bound" % pct,
     "confirmed excess over code, ranked below the action cut"],
    default="band straddles zero - the excess cannot be resolved at this precision")
print("  %s" % dict(S.status.value_counts()))
print("\n  ORDER IS FLEET-WIDE on the lower bound of the ranking value (Miguel")
print("  2026-09-12), overriding 'rank within era'. era stays a column and a filter,")
print("  phys_rank_in_era is kept, and the bias travels in phys_rank_bias_note.")
print("  OPTION A: vintage is in the total but out of the ranking value for the %d"
      % int(keep.sum()))
print("  households whose unit we would keep.")

head("3. ASSEMBLE")

E = pd.DataFrame({"household_id": H.Household_ID.astype("int64")})
E["schema_version"] = SCHEMA_VERSION
E["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
m = H[["Household_ID"]].merge(S, on="Household_ID", how="left")

E["phys_status"] = m.status.fillna("INCOMPLETE_AUDIT")

# THE NEVER-COMPUTED 42 ARE A MIXED SET AND USED TO BE LABELLED AS ONE (P27, fixed
# 2026-09-17). The cause was read from `m`, which is H's id column left-merged onto the
# SCORED frame S - so drop_reason is NaN for exactly the unscored households, and every
# one of them fell through to the "insufficient usable meter days" default. Two causes
# with two different fixes were printed as one. Read it from H, where it is populated.
_bldg_bad = H.drop_reason.fillna("").ne("")
_meter_bad = ~(H.n_days.notna() & H.hdd_normal_per_day.notna())
_dr = H.drop_reason.fillna("")
_cause = np.where(
    _bldg_bad & _meter_bad, "building data missing (" + _dr + ") AND meter record too short",
    np.where(_bldg_bad, "building data missing: " + _dr,
             "meter record too short or lacks season coverage"))
# Who can actually resolve it. An auditor can record a floor area; nobody can record
# meter history that was never captured, so those two must not read the same.
_fix = np.where(_bldg_bad, "record the missing building data - an auditor can do this",
                "none - needs a longer meter record; a visit does not help")

E["phys_status_reason"] = m.status_reason.fillna(
    "never computed - see phys_no_result_reason for this household's cause")
E["phys_no_result_reason"] = np.where(
    E.phys_status.isin(NO_RESULT),
    np.where(E.phys_status == "INCOMPLETE_AUDIT", _cause, "band straddles zero"), "")
E["phys_no_result_fix"] = np.where(
    E.phys_status.isin(NO_RESULT),
    np.where(E.phys_status == "INCOMPLETE_AUDIT", _fix,
             "none - the sources disagree too widely to resolve this one"), "")
# Kept as "will this ever become answerable": True for both audit gaps, False once we
# have looked and the sources cannot resolve it. WHO ACTS lives in phys_no_result_fix -
# do not read this boolean as "send someone".
E["phys_no_result_is_fixable"] = np.where(
    E.phys_status == "INCOMPLETE_AUDIT", True,
    np.where(E.phys_status == "INCONCLUSIVE", False, pd.NA))
_nb = int((_bldg_bad & ~_meter_bad).sum())
_nm = int((~_bldg_bad & _meter_bad).sum())
_nx = int((_bldg_bad & _meter_bad).sum())
print("\n  NEVER COMPUTED, BY TRUE CAUSE (P27): building data only %d, meter record"
      " only %d, both %d" % (_nb, _nm, _nx))
print("  phys_no_result_fix says who acts; phys_no_result_is_fixable does NOT.")
E["phys_excess_confirmed"] = m.excess_confirmed
E["phys_era"] = m.era

# THE ORDER. Fleet-wide is primary; era rank is kept so the bias stays checkable.
E["phys_rank_fleet"] = m.rank_fleet
E["phys_rank_in_era"] = m.rank_in_era
E["phys_rank_on"] = "phys_rank_value_lo_kwh_yr"
E["phys_rank_scope"] = "fleet"
E["phys_rank_bias_note"] = BIAS_NOTE
E["phys_rank_value_kwh_yr"] = m.rank_metric.round(0)
E["phys_rank_value_lo_kwh_yr"] = m.rank_metric_lo.round(0)
E["phys_rank_excludes_vintage"] = m.unit_recommendation.eq("KEEP_IN_LIFE")

E["phys_deficiency_kwh_yr"] = m.deficiency.round(0)
E["phys_deficiency_lo_kwh_yr"] = m.deficiency_lo.round(0)
E["phys_deficiency_hi_kwh_yr"] = m.deficiency_hi.round(0)
E["phys_deficiency_band_kwh_yr"] = m.band.round(0)
E["phys_deficiency_pct_of_reference"] = (100 * m.deficiency / m.E_reference).round(1)
E["phys_deficiency_pct_lo"] = (100 * m.deficiency_lo / m.E_reference).round(1)
E["phys_deficiency_pct_hi"] = (100 * m.deficiency_hi / m.E_reference).round(1)

# THE THREE GROUPS of page 2. house + heat_pump == total, asserted below.
E["phys_group_house_kwh_yr"] = m.group_house.round(0)
E["phys_group_house_lo_kwh_yr"] = m.group_house_lo.round(0)
E["phys_group_house_hi_kwh_yr"] = m.group_house_hi.round(0)
E["phys_group_house_owner"] = "builder"
E["phys_group_heat_pump_kwh_yr"] = m.group_heat_pump.round(0)
E["phys_group_heat_pump_lo_kwh_yr"] = m.group_heat_pump_lo.round(0)
E["phys_group_heat_pump_hi_kwh_yr"] = m.group_heat_pump_hi.round(0)
E["phys_group_heat_pump_owner"] = "installer"
# Unknown installation year makes NO CLAIM on the point (vintage factor 1.0 -> term 0)
# while every draw samples an older unit, so the band sits ABOVE the point. Declared
# here so a page shows the band rather than a bare zero. Decision 8, P26.
E["phys_heat_pump_point_is_no_claim"] = m.unit_recommendation.eq("RECORD_INSTALL_YEAR")

E["phys_term_envelope_kwh_yr"] = m.term_envelope.round(0)
E["phys_term_emitter_kwh_yr"] = m.term_emitter.round(0)
E["phys_term_dhw_kwh_yr"] = m.term_dhw.round(0)
E["phys_term_vintage_kwh_yr"] = m.term_vintage.round(0)
E["phys_vintage_factor"] = m.vintage_factor.round(3)

# THE HEAT-PUMP DECISION. Ages are as of the END OF THE METER DATA, not today.
E["phys_unit_recommendation"] = m.unit_recommendation
E["phys_unit_age_years"] = m.unit_age_years
E["phys_unit_age_reference_year"] = AGE_REFERENCE_YEAR
E["phys_unit_service_life_basis"] = (
    "measured failures, Weibull fit (ZHAW Hubbuch & Vecsei): air 20 yr SD 7, "
    "ground 26.7 yr SD 4.7")

E["phys_scenario_capacity_lo_kwh_yr"] = m.cap_lo.round(0)
E["phys_scenario_capacity_mid_kwh_yr"] = m.cap_mid.round(0)
E["phys_scenario_capacity_hi_kwh_yr"] = m.cap_hi.round(0)
E["phys_scenario_never_sum_into_total"] = True

E["phys_context_e_as_built_kwh_yr"] = m.E_as_built.round(0)
E["phys_context_e_reference_kwh_yr"] = m.E_reference.round(0)
E["phys_level_is_not_a_prediction"] = True
E["phys_appliances_excluded"] = True

E["phys_completeness_tier"] = m.tier
E["phys_geometry_reconciles"] = m.storey_reconciles
E["phys_pv_level"] = m.pv.map({True: "PV", False: "no PV"}).fillna("Unknown")
E["phys_n_meter_days"] = m.n_days
E["phys_hdd_normal_per_day"] = m.hdd_normal_per_day.round(3)
E["phys_weather_basis"] = "station normal year (record length does not enter)"

# THE VISIT AXIS, from P13. HIDDEN from our two pages; the end section consumes it.
VQ = HERE / "outputs" / "p13" / "data" / "p13_visit_queue.parquet"
if not VQ.exists():
    raise SystemExit("p13_visit_queue.parquet missing - run p13_visit_queue.py first")
V = pd.read_parquet(VQ).set_index("Household_ID")
v = V.reindex(E.household_id)
E["visit_status"] = v.visit_status.fillna("NOT_ASSESSABLE").to_numpy()
E["visit_technician_recoverable_kwh"] = v.technician_recoverable_envelope_kwh.to_numpy()
E["visit_slope_excess_lo_kwh"] = v.slope_excess_lo_kwh.round(0).to_numpy()
E["visit_slope_excess_hi_kwh"] = v.slope_excess_hi_kwh.round(0).to_numpy()
E["visit_slope_excess_pct"] = v.slope_excess_pct.round(1).to_numpy()
E["visit_step_kwh_day"] = v.step_kwh_day.round(2).to_numpy()
E["visit_rank_in_era"] = v.rank_in_era.to_numpy()
E["visit_never_sum_with_phys_deficiency"] = True
E["visit_hidden_from_building_pages"] = True

head("4. SELF-VALIDATION")

fails = []


def rule(name, cond, detail=""):
    if cond:
        print("  ok   %-58s %s" % (name, detail))
    else:
        fails.append(name)
        print("  FAIL %-58s %s" % (name, detail))


rule("schema version says v2", E.schema_version.eq(SCHEMA_VERSION).all())
rule("v1 still on disk for one cycle",
     (OUT / (PREVIOUS_VERSION + ".parquet")).exists(), PREVIOUS_VERSION)
rule("all 214 households present", len(E) == 214, "%d" % len(E))
rule("household_id unique", E.household_id.is_unique)
rule("every status is one of the four declared states",
     set(E.phys_status.unique()) <= STATES, ", ".join(sorted(E.phys_status.unique())))
rule("NO state claims a household is normal",
     not any(s.lower() in {"normal", "ok", "good", "pass", "fine"}
             for s in E.phys_status.unique()))
rule("statuses use NO single letters",
     all(len(s) > 2 for s in set(E.phys_status) | set(E.visit_status)))
rule("no status on either axis says 'below', which reads both ways",
     not any("below" in s.lower() for s in set(E.phys_status) | set(E.visit_status)),
     "USES_LESS_THAN_MODELLED replaced BELOW_PHYSICS")
rule("both no-result states are populated and distinguishable",
     set(NO_RESULT) <= set(E.phys_status.unique())
     and E.loc[E.phys_status.isin(NO_RESULT), "phys_no_result_is_fixable"].nunique() == 2,
     "%s" % dict(E[E.phys_status.isin(NO_RESULT)].phys_status.value_counts()))
rule("INCOMPLETE_AUDIT is flagged fixable, INCONCLUSIVE is not",
     bool((E.loc[E.phys_status == "INCOMPLETE_AUDIT", "phys_no_result_is_fixable"]
           == True).all())
     and bool((E.loc[E.phys_status == "INCONCLUSIVE", "phys_no_result_is_fixable"]
               == False).all()))
rule("every no-result row names a reason",
     (E.loc[E.phys_status.isin(NO_RESULT), "phys_no_result_reason"] != "").all())
# REGRESSION GUARD for the bug P27 found: a blanket string over a mixed set passed
# every rule above, because "is populated" is not "is true of this household".
_ia = E.loc[E.phys_status == "INCOMPLETE_AUDIT", "phys_no_result_reason"]
rule("never-computed reasons are PER HOUSEHOLD, not one blanket string",
     _ia.nunique() >= 2, "%d distinct causes over %d households" % (_ia.nunique(), len(_ia)))
rule("every no-result row says who can fix it, and the two audit causes differ",
     (E.loc[E.phys_status.isin(NO_RESULT), "phys_no_result_fix"] != "").all()
     and E.loc[E.phys_status == "INCOMPLETE_AUDIT", "phys_no_result_fix"].nunique() >= 2)
rule("no result-bearing row carries a no-result reason",
     (E.loc[~E.phys_status.isin(NO_RESULT), "phys_no_result_reason"] == "").all())

_p = E.dropna(subset=["phys_deficiency_kwh_yr"])
rule("every energy group travels with a band",
     all(_p[c + "_lo_kwh_yr"].notna().all() and _p[c + "_hi_kwh_yr"].notna().all()
         for c in ["phys_deficiency", "phys_group_house", "phys_group_heat_pump"]),
     "house, heat pump and total")
rule("lo <= hi on every band, no exceptions",
     bool((_p.phys_deficiency_lo_kwh_yr <= _p.phys_deficiency_hi_kwh_yr).all()
          and (_p.phys_group_house_lo_kwh_yr <= _p.phys_group_house_hi_kwh_yr).all()
          and (_p.phys_group_heat_pump_lo_kwh_yr
               <= _p.phys_group_heat_pump_hi_kwh_yr).all()),
     "checked on %d scored rows" % len(_p))
# ROUND_TOL: lo, point and hi are rounded independently, so the point may sit a
# kWh or two outside its own band. Same tolerance the term-sum rules use.
ROUND_TOL = 2
rule("the total's point sits inside its band, within rounding",
     bool(((_p.phys_deficiency_lo_kwh_yr - _p.phys_deficiency_kwh_yr <= ROUND_TOL)
           & (_p.phys_deficiency_kwh_yr - _p.phys_deficiency_hi_kwh_yr
              <= ROUND_TOL)).all()),
     "tolerance %d kWh/yr" % ROUND_TOL)
# The heat-pump band is DELIBERATELY asymmetric where the installation year is
# unknown: no claim on the point, band widened upward. Measured on this run: 63 rows.
_known = _p[~(_p.phys_heat_pump_point_is_no_claim == True)]
_nc = _p[_p.phys_heat_pump_point_is_no_claim == True]
rule("heat pump: known year is bracketed; unknown year claims nothing",
     bool(((_known.phys_group_heat_pump_lo_kwh_yr
            - _known.phys_group_heat_pump_kwh_yr <= ROUND_TOL)
           & (_known.phys_group_heat_pump_kwh_yr
              - _known.phys_group_heat_pump_hi_kwh_yr <= ROUND_TOL)).all())
     and bool((_nc.phys_group_heat_pump_kwh_yr == 0).all())
     and bool((_nc.phys_group_heat_pump_lo_kwh_yr >= 0).all()),
     "%d known, %d no-claim rows whose band sits above a zero point"
     % (len(_known), len(_nc)))
rule("percent columns agree in sign with the kWh columns",
     bool((np.sign(_p.phys_deficiency_pct_of_reference)
           == np.sign(_p.phys_deficiency_kwh_yr)).all()))
rule("the four terms sum to the deficiency within rounding",
     bool(((_p.phys_term_envelope_kwh_yr + _p.phys_term_emitter_kwh_yr
            + _p.phys_term_dhw_kwh_yr + _p.phys_term_vintage_kwh_yr
            - _p.phys_deficiency_kwh_yr).abs() <= 2).all()))
rule("house + heat pump == total within rounding",
     bool(((_p.phys_group_house_kwh_yr + _p.phys_group_heat_pump_kwh_yr
            - _p.phys_deficiency_kwh_yr).abs() <= 2).all()))
rule("vintage stays INSIDE the headline total (decision 6)",
     bool((_p.phys_group_heat_pump_kwh_yr
           <= _p.phys_deficiency_kwh_yr.abs() + _p.phys_group_house_kwh_yr.abs()).all()))
_k = _p[_p.phys_rank_excludes_vintage == True]
rule("OPTION A: the ranking value drops vintage only for KEEP_IN_LIFE units",
     bool(((_k.phys_rank_value_kwh_yr - (_k.phys_deficiency_kwh_yr
                                         - _k.phys_group_heat_pump_kwh_yr)).abs()
           <= 2).all())
     and bool(((_p[~(_p.phys_rank_excludes_vintage == True)].phys_rank_value_kwh_yr
                - _p[~(_p.phys_rank_excludes_vintage == True)].phys_deficiency_kwh_yr)
               .abs() <= 2).all()),
     "%d rows keep their unit" % len(_k))
rule("scenario columns are prefixed and flagged",
     all(c.startswith("phys_scenario_") for c in E.columns if "capacity" in c)
     and bool(E.phys_scenario_never_sum_into_total.all()))
rule("every confirmed-excess row carries a fleet rank AND an era rank",
     E.loc[E.phys_excess_confirmed == True, ["phys_rank_fleet", "phys_rank_in_era"]]
     .notna().all().all())
rule("HIGH_EXCESS is a strict subset of confirmed excess",
     bool((E.loc[E.phys_status == "HIGH_EXCESS", "phys_excess_confirmed"] == True).all()))
rule("HIGH_EXCESS is the worst quartile of the FLEET, not of an era",
     bool((E.loc[E.phys_status == "HIGH_EXCESS", "phys_rank_fleet"]
           <= np.ceil(n_conf * PRIORITY_FRACTION)).all())
     and E.phys_rank_scope.eq("fleet").all(), "%d confirmed" % n_conf)
rule("the fleet-wide bias note ships on every row", (E.phys_rank_bias_note != "").all())
rule("the heat-pump recommendation uses the declared vocabulary",
     set(E.phys_unit_recommendation.dropna().unique()) <= UNIT_RECOMMENDATIONS)
rule("no vintage claim where the installation year is unknown",
     bool((_p.loc[_p.phys_unit_recommendation == "RECORD_INSTALL_YEAR",
                  "phys_term_vintage_kwh_yr"] == 0).all()),
     "unknown year is a fixable audit gap, not an old unit")
rule("ages are stated as of the data end, not today",
     E.phys_unit_age_reference_year.eq(AGE_REFERENCE_YEAR).all(), str(AGE_REFERENCE_YEAR))
rule("Category B runs on normal-year weather", E.phys_weather_basis.notna().all()
     and bool((_p.phys_hdd_normal_per_day > 0).all()))
rule("appliances are excluded and the level is not a prediction",
     bool(E.phys_appliances_excluded.all()) and bool(E.phys_level_is_not_a_prediction.all()))
rule("visit_status uses the four declared words",
     set(E.visit_status.unique()) <= VISIT_STATES,
     "%s" % dict(E.visit_status.value_counts()))
rule("NO fault column exists anywhere in this export",
     not any("fault" in c for c in E.columns),
     "Aaditya's model is not loaded in this workstream")
rule("the visit axis is flagged hidden from the building pages",
     bool(E.visit_hidden_from_building_pages.all()))
rule("the never-sum flags are set on both never-sum sets",
     bool(E.visit_never_sum_with_phys_deficiency.all())
     and bool(E.phys_scenario_never_sum_into_total.all()))
rule("every model column is prefixed against peer-model collision",
     all(c.startswith(("phys_", "visit_")) for c in E.columns
         if c not in {"household_id", "schema_version", "generated_utc"}))

head("5. WRITE")

E.to_csv(OUT / (SCHEMA_VERSION + ".csv"), index=False, sep=";")
E.to_parquet(OUT / (SCHEMA_VERSION + ".parquet"), index=False)
print("  %s.csv / .parquet   %d rows x %d columns"
      % (SCHEMA_VERSION, len(E), len(E.columns)))
print("  %s stays on disk for one cycle." % PREVIOUS_VERSION)
print("\n  status counts: %s" % dict(E.phys_status.value_counts()))
pr = E[E.phys_status == "HIGH_EXCESS"]
bc = E[E.phys_excess_confirmed == True]
print("  HIGH_EXCESS      %3d households, %8.0f kWh/yr on the lower bound"
      % (len(pr), pr.phys_deficiency_lo_kwh_yr.sum()))
print("  excess confirmed %3d households, %8.0f kWh/yr on the lower bound"
      % (len(bc), bc.phys_deficiency_lo_kwh_yr.sum()))
print("\n  THE THREE GROUPS, fleet totals on the lower bound:")
for g, owner in [("house", "builder"), ("heat_pump", "installer")]:
    c = "phys_group_%s_lo_kwh_yr" % g
    print("    %-10s %8.0f kWh/yr   owner: %s" % (g, E[c].sum(), owner))
print("    %-10s %8.0f kWh/yr" % ("total", E.phys_deficiency_lo_kwh_yr.sum()))
print("\n  heat-pump decision: %s" % dict(E.phys_unit_recommendation.value_counts()))
print("  visit axis (hidden from our pages): %s" % dict(E.visit_status.value_counts()))
print("\n  TOP 12 OF THE ONE FLEET-WIDE LIST:")
top = E[E.phys_status.isin(["HIGH_EXCESS", "EXCESS_CONFIRMED"])].nsmallest(
    12, "phys_rank_fleet")
print("  %-9s %-10s %9s %9s %9s %-20s" % ("house", "era", "house lo", "pump lo",
                                          "rank lo", "unit"))
for _, r in top.iterrows():
    print("  %-9d %-10s %9.0f %9.0f %9.0f %-20s"
          % (r.household_id, r.phys_era, r.phys_group_house_lo_kwh_yr,
             r.phys_group_heat_pump_lo_kwh_yr, r.phys_rank_value_lo_kwh_yr,
             str(r.phys_unit_recommendation)[:20]))

if fails:
    print("\n  %d RULE(S) FAILED - export is NOT valid" % len(fails))
    sys.exit(1)
print("\n  all export rules pass.")
print("\nP11 complete.")
