"""The portable physics layer. Knows NOTHING about HEAPO.

Every function takes variable ROLES, never dataset column names. A second dataset
supplies its own adapter and nothing in this file changes. If a dataset-specific column
name ever appears here, the separation is broken - p_pipeline_test.py asserts it.

Every constant carries value, band, unit, source and section. A constant with no
source does not ship. Bands are what the UNCERTAINTY ENGINE samples - they are the
published spread, not invented error bars.

numpy only.
"""
import json
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- constants
# The standards registry. Every constant with its band, source, and a STATUS saying
# whether the value was actually found in the cited document. A new region is a new
# file; nothing below changes.
REGION_FILE = Path(__file__).resolve().parent / "constants_ch.json"
_REG = json.loads(REGION_FILE.read_text(encoding="utf-8"))
# (value, lo, hi, unit, source, section)
C = {k: (v["value"], v["lo"], v["hi"], v["unit"], v["source"], v["section"])
     for k, v in _REG["constants"].items()}
STATUS = {k: v["status"] for k, v in _REG["constants"].items()}

ERA_KEYS = {
    "pre1975": "u_era_pre1975", "1976_1990": "u_era_1976_1990",
    "1991_2000": "u_era_1991_2000", "2001_2010": "u_era_2001_2010",
    "post2010": "u_era_post2010",
}
ERA_ORDER = _REG["era_order"]


def value(name):
    return C[name][0]


def band(name):
    return C[name][1], C[name][2]


def sample(name, rng):
    lo, hi = band(name)
    return lo if lo == hi else rng.uniform(lo, hi)


# ---------------------------------------------------------------- geometry
def envelope_area(footprint_m2, n_storeys_above, heated_basement,
                  storey_height, b_ground, perimeter_factor=1.0):
    """Thermal envelope area, b-weighted. Roles in, m2 out.

    Square plan is the MINIMUM perimeter, so perimeter_factor >= 1 widens it.
    A heated basement adds a storey of wall against earth plus moves the lowest
    floor down; both are charged at b_ground.
    """
    per = 4.0 * np.sqrt(footprint_m2) * perimeter_factor
    a_wall_above = per * storey_height * n_storeys_above
    a_wall_bsmt = np.where(heated_basement, per * storey_height, 0.0)
    a_roof = footprint_m2
    a_lowest = footprint_m2
    return a_wall_above + a_roof + b_ground * (a_wall_bsmt + a_lowest)


def ventilation_coefficient(area_m2, n_air, v_net_per_m2, rho_c):
    """W/K. Identical in both baselines, so it CANCELS in the difference."""
    return rho_c * n_air * v_net_per_m2 * area_m2


def heat_loss_coefficient(u_value, a_thermal, h_ventilation):
    """Total specific heat loss, W/K."""
    return u_value * a_thermal + h_ventilation


def design_load_kw(h_total, t_set, t_design):
    return h_total * (t_set - t_design) / 1000.0


# ---------------------------------------------------------------- energy
def heating_electricity(h_total, jaz, hdd_per_day, days=365.0):
    """kWh/yr. h_total W/K -> kWh per degree-day via 24/1000."""
    return (h_total * 24.0 / 1000.0) / jaz * hdd_per_day * days


def dhw_electricity(residents, jaz_dhw, kwh_person_day, days=365.0):
    return kwh_person_day * residents * days / jaz_dhw


# Kept OUT of evaluate(): identical in both baselines so it cancels in the deficiency,
# and drawing it there would shift every existing Monte Carlo stream.
def appliance_electricity(residents, rng=None):
    """kWh/yr of non-heat-pump household electricity, single-family house."""
    S = (lambda n: sample(n, rng)) if rng is not None else value
    extra = np.asarray(residents, dtype=float) - 4.0
    pp = S("appl_efh_per_person")
    step = np.where(extra > 0, pp - value("appl_taper_5plus"), pp)
    return S("appl_efh_4p") + step * extra


# ------------------------------------------------- weather sampling error
# hdd_per_day * 365 assumes the recorded days are a fair sample of a year. They
# are not: records are holey and start/end mid-season, so a 1-1.5 year record
# covers TWO winters and one summer and reads far too cold.
#
# Measured on 1,032 households carrying at least one COMPLETE calendar year, as
# (hdd_per_day * 365) / (mean HDD over complete years). WEATHER ONLY - no
# consumption enters, so the calibration rule is not engaged.
#
# bin -> (median ratio, p2.5, p97.5) of estimate/truth
HDD_SAMPLING = [
    (548,   (1.252, 1.156, 1.328)),   # 365-548 days: 25% TOO HIGH
    (730,   (0.956, 0.928, 1.158)),
    (1095,  (1.112, 0.982, 1.223)),
    (10**9, (1.077, 0.962, 1.145)),
]


def hdd_correction(n_days, rng=None):
    """Divide hdd_per_day by this to remove the record-length bias."""
    for cut, (med, lo, hi) in HDD_SAMPLING:
        if n_days <= cut:
            return med if rng is None else rng.uniform(lo, hi)
    return 1.0


def u_as_built(era, renovation_count, rng=None):
    """U for the house as it is.

    A renovated house sits somewhere between its own era and a newer one, and no
    source supplies renovated-state U. So renovation WIDENS the band toward the
    next-newer era rather than applying an unsourced modifier. That is the honest
    move and it is what the tier system exists for.
    """
    i = ERA_ORDER.index(era)
    lo, hi = band(ERA_KEYS[era])
    if renovation_count > 0:
        steps = 1 if renovation_count == 1 else 2
        j = min(i + steps, len(ERA_ORDER) - 1)
        lo = band(ERA_KEYS[ERA_ORDER[j]])[0]
    if rng is None:
        # Bands may be asymmetric (split sensitivity, P22), so the midpoint is not the value.
        return value(ERA_KEYS[era]) if renovation_count == 0 else 0.5 * (lo + hi)
    return rng.uniform(lo, hi)


JAZ_KEYS = {("air-source", "floor_only"): "jaz_ashp_floor",
            ("air-source", "both"): "jaz_ashp_lowrad",
            ("air-source", "radiator_only"): "jaz_ashp_rad",
            ("ground-source", "floor_only"): "jaz_gshp_floor",
            ("ground-source", "both"): "jaz_gshp_lowrad",
            ("ground-source", "radiator_only"): "jaz_gshp_rad"}
JAZ_HOTWATER_KEYS = {"air-source": "jaz_dhw_hp", "ground-source": "jaz_dhw_gshp"}


def jaz_for(hp_type, emitter, rng=None):
    """Field seasonal performance, SPACE HEATING ONLY. Returns (jaz, is_derived).

    Every cell is published (OST P+I 2020 Tab 1 / RISE 2023 Tab 1), none derived.
    """
    key = JAZ_KEYS[(hp_type, emitter)]
    return (sample(key, rng) if rng is not None else value(key)), False


def vintage_factor(hp_type, year, rng=None):
    """JAZ of this unit relative to the table's ~2017 installations (P23).

    Linear from FAWA-era installations (factor < 1) to the table (1.0), flat outside
    - never extrapolated. FAWA saw no ageing loss over 9 years, so this is technology
    vintage, not wear. Unknown year: point 1.0 (no claim), the draw spans the range.
    """
    key = "jaz_vintage_old_air" if hp_type == "air-source" else "jaz_vintage_old_ground"
    f_old = sample(key, rng) if rng is not None else value(key)
    if year != year:
        if rng is None:
            return 1.0
        t = rng.uniform(0.0, 1.0)
    else:
        y0, y1 = value("jaz_vintage_year_old"), value("jaz_vintage_year_new")
        t = min(max((year - y0) / (y1 - y0), 0.0), 1.0)
    return f_old + (1.0 - f_old) * t


# ---------------------------------------------------------------- the model
def evaluate(h, rng=None):
    """One household, one draw. `h` is a dict of ROLES.

    Required roles: area_m2, footprint_m2, n_storeys_above, heated_basement,
    era, renovation_count, hp_type, emitter, residents, dhw_electric, and either
    hdd_normal_per_day (station normal year, preferred - record length never
    enters) or hdd_per_day + n_days (record mean, P6-corrected).
    Returns the two baselines and the decomposed difference.
    """
    S = (lambda n: sample(n, rng)) if rng is not None else value
    hn = h.get("hdd_normal_per_day")
    if hn is not None and hn == hn:
        hdd = hn
        if rng is not None:
            se = h.get("hdd_normal_se_rel", 0.0)
            hdd *= rng.uniform(1 - 2 * se, 1 + 2 * se)
    else:
        hdd = h["hdd_per_day"] / hdd_correction(h.get("n_days", 10**9), rng)

    sh, bg = S("storey_height"), S("b_ground")
    pf = S("perimeter_factor")
    a_th = envelope_area(h["footprint_m2"], h["n_storeys_above"],
                         h["heated_basement"], sh, bg, pf)
    h_vent = ventilation_coefficient(h["area_m2"], S("n_air"),
                                     S("v_net_per_m2"), S("rho_c"))

    u_ab = u_as_built(h["era"], h["renovation_count"], rng)
    u_rf = S("u_reference")
    # One draw for both baselines: thermal bridging is real but cancels in the difference.
    dtb = S("du_thermal_bridge")
    H_ab = heat_loss_coefficient(u_ab + dtb, a_th, h_vent)
    H_rf = heat_loss_coefficient(u_rf + dtb, a_th, h_vent)

    jaz_new, derived = jaz_for(h["hp_type"], h["emitter"], rng)
    # The reference gets a current unit; only the as-built JAZ carries its vintage.
    vf = vintage_factor(h["hp_type"], h["hp_install_year"], rng) if "hp_install_year" in h else 1.0
    jaz_ab = jaz_new * vf
    jaz_rf, _ = jaz_for(h["hp_type"], "floor_only", rng)
    jdhw = S(JAZ_HOTWATER_KEYS[h["hp_type"]])
    kpd = S("dhw_kwh_person_day")

    heat_ab = heating_electricity(H_ab, jaz_ab, hdd)
    heat_rf = heating_electricity(H_rf, jaz_rf, hdd)
    dhw_ab = dhw_electricity(h["residents"], 1.0 if h["dhw_electric"] else jdhw, kpd)
    dhw_rf = dhw_electricity(h["residents"], jdhw, kpd)

    term_env = heating_electricity(H_ab - H_rf, jaz_ab, hdd)
    term_vint = (H_rf * 24.0 / 1000.0) * (1 / jaz_ab - 1 / jaz_new) * hdd * 365
    term_emit = (H_rf * 24.0 / 1000.0) * (1 / jaz_new - 1 / jaz_rf) * hdd * 365
    term_dhw = dhw_ab - dhw_rf

    return {
        "a_thermal": a_th, "huellzahl": a_th / h["area_m2"],
        "u_as_built": u_ab, "H_as_built": H_ab, "H_reference": H_rf,
        "jaz_as_built": jaz_ab, "jaz_derived": derived,
        "hdd_corrected": hdd, "design_kw": design_load_kw(H_ab, S("t_set"), S("t_design")),
        "E_as_built": heat_ab + dhw_ab, "E_reference": heat_rf + dhw_rf,
        "deficiency": (heat_ab + dhw_ab) - (heat_rf + dhw_rf),
        "term_envelope": term_env, "term_emitter": term_emit, "term_dhw": term_dhw,
        "term_vintage": term_vint, "vintage_factor": vf,
    }


def completeness_tier(h):
    """How much of this household's estimate came from real audit values.

    T1 no renovation ambiguity, full geometry, known DHW source
    T2 one widening source
    T3 two or more
    """
    n = 0
    if h["renovation_count"] > 0:
        n += 1
    if not h.get("geometry_complete", True):
        n += 1
    if not h.get("dhw_known", True):
        n += 1
    if "hp_install_year" in h and h["hp_install_year"] != h["hp_install_year"]:
        n += 1
    return "T1" if n == 0 else ("T2" if n == 1 else "T3")
