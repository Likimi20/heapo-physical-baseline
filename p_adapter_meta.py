"""Binding #3 - HEAPO meta_data.csv. A REAL second source that CORRECTLY REFUSES.

This adapter exists to be run and to FAIL CLEANLY. meta_data.csv covers 1,358 of
the 1,408 households - six times the protocol cohort - and it cannot drive this
model, because it records no construction era, no per-storey geometry and no
heating capacity.

That is the portability contract WORKING, not failing. A contract that only ever
says yes is decoration. This one says no, names the missing roles, and says so
before a single number is computed.

It also states the boundary between the two workstreams in code: meta_data is what
the PEER model runs on - the generic instrument, any fleet, no site visit. The
physical model needs someone to have walked through the building. That is the
whole generic-versus-specific split, made machine-checkable.

numpy + pandas only.
"""
import numpy as np
import pandas as pd

REQUIRED = ["area_m2", "footprint_m2", "n_storeys_above", "heated_basement",
            "era", "renovation_count", "residents", "hp_type", "emitter",
            "dhw_electric"]

# Roles meta_data cannot supply, and why. Stated up front, not discovered.
UNSUPPLIABLE = {
    "era": "no construction or installation year exists in meta_data.csv",
    "footprint_m2": "no per-storey areas - only one whole-dwelling living area",
    "n_storeys_above": "no storey information of any kind",
    "heated_basement": "no basement information of any kind",
    "renovation_count": "no renovation flags",
}


def to_roles(meta_csv):
    """Map what meta_data CAN supply. Missing roles stay NaN - never invented."""
    m = pd.read_csv(meta_csv, sep=None, engine="python")
    b = lambda c: m[c].fillna(False).astype(bool)
    rad, flo = b("Survey_HeatDistribution_System_Radiator"), \
        b("Survey_HeatDistribution_System_FloorHeating")
    out = pd.DataFrame({
        "Household_ID": pd.to_numeric(m.Household_ID, errors="coerce").astype("Int64"),
        "area_m2": pd.to_numeric(m.Survey_Building_LivingArea, errors="coerce"),
        "residents": pd.to_numeric(m.Survey_Building_Residents, errors="coerce"),
        "hp_type": m.Survey_HeatPump_Installation_Type,
        "dhw_electric": b("Survey_DHW_Production_ByElectricWaterHeater"),
    })
    out["emitter"] = np.select([flo & ~rad, rad & ~flo, rad & flo],
                               ["floor_only", "radiator_only", "both"], default=None)
    for r in UNSUPPLIABLE:
        out[r] = np.nan
    return out


def contract_report(df):
    """Which required roles this source supplies, and which it cannot."""
    rows = []
    for r in REQUIRED:
        present = int(df[r].notna().sum()) if r in df.columns else 0
        rows.append({"role": r, "n_present": present,
                     "pct": round(100 * present / len(df), 1),
                     "status": "OK" if present > 0 else "MISSING",
                     "why_missing": UNSUPPLIABLE.get(r, "")})
    return pd.DataFrame(rows)
