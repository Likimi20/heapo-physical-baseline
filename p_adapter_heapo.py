"""HEAPO binding #1 - maps protocols.csv onto the roles p_physics.py expects.

This is the ONLY file that knows HEAPO column names. A second dataset gets
p_adapter_<name>.py and nothing in p_physics.py changes.

Traps handled here, not in the physics:
  * protocols.csv is semicolon-delimited, read with sep=None engine='python'
  * Household_ID is float64 with 193 NaN rows - cast to Int64 (parent trap 5)
  * 3 households have multiple visits - first visit used
  * "tick the one that applies" columns are True/NaN with no False level

numpy + pandas only.
"""
import numpy as np
import pandas as pd

ERA_MAP = {
    "< 1975": "pre1975",
    "1976 - 80": "1976_1990", "1981 - 85": "1976_1990", "1986 - 90": "1976_1990",
    "1991 - 95": "1991_2000", "1995 - 00": "1991_2000",
    "2000 - 10": "2001_2010", "> 2010": "post2010",
}
STOREY_COLS = ["GroundFloor", "FirstFloor", "SecondFloor", "TopFloor"]


def load_households(protocols_csv):
    """One row per household, roles only plus identifiers and validation labels."""
    pr = pd.read_csv(protocols_csv, sep=None, engine="python")
    pr["Household_ID"] = pr.Household_ID.astype("Int64")
    hh = (pr[pr.Household_ID.notna()].sort_values("Visit_Date")
          .drop_duplicates("Household_ID", keep="first").copy())

    n = lambda c: pd.to_numeric(hh["Building_FloorAreaHeated_" + c], errors="coerce")
    b = lambda c: hh[c].fillna(False).astype(bool)

    out = pd.DataFrame({
        "Household_ID": hh.Household_ID.astype("int64"),
        "area_m2": n("Total"),
        # FOOTPRINT = LARGEST STOREY, not the ground floor. Household 5661171
        # records ground 10 m2 and first floor 240 m2 - internally consistent
        # with its 250 m2 total, but an upper floor cannot be 24x the ground
        # floor. Using the ground floor gave it a huellzahl of 0.33, i.e. a
        # house with almost no envelope. Caught by p_pipeline_test.py section H.
        "footprint_m2": pd.concat([n(c) for c in STOREY_COLS], axis=1).max(axis=1),
        "n_storeys_above": (pd.concat([n(c) for c in STOREY_COLS], axis=1) > 0).sum(axis=1),
        "heated_basement": (n("Basement") > 0).fillna(False),
        "era_raw": hh.Building_ConstructionYear_Interval,
        "era": hh.Building_ConstructionYear_Interval.map(ERA_MAP),
        "renovation_count": (b("Building_Renovated_Windows").astype(int)
                             + b("Building_Renovated_Walls").astype(int)
                             + b("Building_Renovated_Roof").astype(int)),
        "residents": pd.to_numeric(hh.Building_Residents, errors="coerce"),
        "hp_type": hh.HeatPump_Installation_Type,
        "dhw_electric": b("DHW_Production_ByElectricWaterHeater"),
        # No DHW_Production_* ticked = source UNKNOWN, not heat pump. The physics
        # still scores it as heat-pump DHW, so it must widen the tier.
        "dhw_known": pd.concat([b(c) for c in hh.columns
                                if c.startswith("DHW_Production_By")], axis=1).any(axis=1),
        "installed_kw": pd.to_numeric(hh.HeatPump_Installation_HeatingCapacity,
                                      errors="coerce"),
        # 129/214 recorded. NaN stays NaN: unknown vintage is carried, never defaulted.
        "hp_install_year": pd.to_numeric(hh.HeatPump_Installation_Year, errors="coerce"),
        "building_type": hh.Building_Type,
        "visit_date": pd.to_datetime(hh.Visit_Date, errors="coerce"),
        # PV is three-level: absence is NOT "no PV" (parent trap 3)
        "pv": hh.Building_PVSystem_Available,
        # VALIDATION LABELS - never model inputs
        "label_correctly_planned": hh.HeatPump_Installation_CorrectlyPlanned,
        "label_sizing_direction": hh.HeatPump_Installation_IncorrectlyPlanned_Categorization,
        "label_curve_too_high": hh.HeatPump_HeatingCurveSetting_TooHigh_BeforeVisit,
        "label_limit_too_high": hh.HeatPump_HeatingLimitSetting_TooHigh_BeforeVisit,
        "label_night_setback": hh.HeatPump_NightSetbackSetting_Activated_BeforeVisit,
        "label_curve_changed": hh.HeatPump_HeatingCurveSetting_Changed,
    }, index=hh.index)

    rad = b("HeatDistribution_System_Radiators")
    flo = b("HeatDistribution_System_FloorHeating")
    out["emitter"] = np.select([flo & ~rad, rad & ~flo, rad & flo],
                               ["floor_only", "radiator_only", "both"], default=None)
    # Storey areas must account for the recorded total. 679810 records 160 m2
    # of storeys against a 320 m2 total - half the building is unrecorded, so
    # its footprint is understated and its envelope with it.
    ssum = pd.concat([n(c) for c in ["Basement"] + STOREY_COLS], axis=1).sum(
        axis=1, min_count=1)
    out["storey_sum_m2"] = ssum
    out["storey_reconciles"] = ((ssum / out.area_m2 - 1).abs() <= 0.10)
    out["geometry_complete"] = (out.footprint_m2.notna() & (out.footprint_m2 > 0)
                                & out.storey_reconciles.fillna(False))
    return out.reset_index(drop=True)


def modellable(df):
    """Rows with every REQUIRED role present. Everything else is UNJUDGEABLE."""
    return (df.area_m2.notna() & (df.area_m2 > 0)
            & df.footprint_m2.notna() & (df.footprint_m2 > 0)
            & (df.n_storeys_above > 0)
            & df.residents.notna() & df.era.notna()
            & df.hp_type.isin(["air-source", "ground-source"])
            & df.emitter.notna())


def drop_reasons(df):
    """Why each non-modellable household was dropped. It reaches the output."""
    r = pd.Series("", index=df.index)
    add = lambda m, t: r.mask(m, (r + ";" + t).str.lstrip(";"))
    r = add(~(df.area_m2.notna() & (df.area_m2 > 0)), "no_area")
    r = add(~(df.footprint_m2.notna() & (df.footprint_m2 > 0)), "no_footprint")
    r = add(~(df.n_storeys_above > 0), "no_storeys")
    r = add(df.residents.isna(), "no_residents")
    r = add(df.era.isna(), "no_era")
    r = add(~df.hp_type.isin(["air-source", "ground-source"]), "hp_type_unsupported")
    r = add(df.emitter.isna(), "no_emitter")
    return r


def station_normals(weather_daily_parquet, household_weather_parquet, hdd_col="HDD_12",
                    min_full_days=360):
    """Per household: its station's NORMAL-YEAR HDD per day, and the relative standard
    error of that normal (between-year SD / mean / sqrt(years)). WEATHER ONLY - no
    consumption enters, and the household's record length never does (P18).
    """
    w = pd.read_parquet(weather_daily_parquet, columns=["Weather_ID", "date", hdd_col, "full_day"])
    w["year"] = pd.to_datetime(w.date).dt.year
    yr = w[w.full_day & w[hdd_col].notna()].groupby(["Weather_ID", "year"])[hdd_col].agg(
        ["size", "sum"])
    yr = yr[yr["size"] >= min_full_days]
    yr["annual"] = yr["sum"] * 365 / yr["size"]
    st = yr.groupby("Weather_ID").annual.agg(["size", "mean", "std"])
    st["hdd_normal_per_day"] = st["mean"] / 365
    st["hdd_normal_se_rel"] = st["std"] / st["mean"] / np.sqrt(st["size"])
    st = st.rename(columns={"size": "normal_years"})[
        ["hdd_normal_per_day", "hdd_normal_se_rel", "normal_years"]]
    hw = pd.read_parquet(household_weather_parquet, columns=["Household_ID", "Weather_ID"])
    station = hw.groupby("Household_ID").Weather_ID.agg(lambda s: s.mode().iat[0])
    return (station.rename("Weather_ID").reset_index()
            .merge(st, left_on="Weather_ID", right_index=True, how="left"))


def daily_observations(daily_states_parquet, household_weather_parquet,
                       hdd_col="HDD_12", post_visit_only=False, visits=None):
    """Per-household mean HDD and kWh over usable days.

    Usable day = state_total in {NORMAL, MIXED_ZERO} AND kwh_total not null AND
    HDD not null. Post-visit filtering is applied HERE, in the adapter, because
    "visit" is a HEAPO concept.
    """
    ds = pd.read_parquet(daily_states_parquet,
                         columns=["Household_ID", "date", "state_total", "kwh_total"])
    hw = pd.read_parquet(household_weather_parquet,
                         columns=["Household_ID", "date", hdd_col])
    p = ds.merge(hw, on=["Household_ID", "date"], how="inner")
    p = p[p.state_total.isin(["NORMAL", "MIXED_ZERO"]) & p.kwh_total.notna()
          & p[hdd_col].notna()]
    if post_visit_only:
        if visits is None:
            raise ValueError("post_visit_only requires visits")
        p = p.merge(visits[["Household_ID", "visit_date"]], on="Household_ID",
                    how="inner")
        p = p[p.visit_date.notna() & (pd.to_datetime(p.date) > p.visit_date)]
    g = p.groupby("Household_ID")
    return pd.DataFrame({
        "n_days": g.kwh_total.size(),
        "n_warm": g[hdd_col].apply(lambda s: int((s == 0).sum())),
        "n_cold": g[hdd_col].apply(lambda s: int((s > 0).sum())),
        "hdd_per_day": g[hdd_col].mean(),
        "kwh_per_day": g.kwh_total.mean(),
    }).reset_index()
