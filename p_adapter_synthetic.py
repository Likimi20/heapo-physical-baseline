"""Binding #2 - SYNTHETIC, for the round-trip test.

Deliberately uses column names in a DIFFERENT LANGUAGE AND SHAPE from HEAPO, so
that if p_physics.py has quietly grown a HEAPO assumption this binding breaks.

Houses are constructed with KNOWN properties so the physics can be checked against
answers derived by hand, not against itself.

numpy + pandas only.
"""
import numpy as np
import pandas as pd

# German column names, metric suffixes, a different era encoding, and area given
# per storey as a LIST rather than one column per floor.
ERA_CODE = {10: "pre1975", 20: "1976_1990", 30: "1991_2000",
            40: "2001_2010", 50: "post2010"}
EMIT_CODE = {"FBH": "floor_only", "HK": "radiator_only", "MIX": "both"}
WP_CODE = {"L/W": "air-source", "S/W": "ground-source"}


def make_frame(seed=20260910, n=120):
    """A synthetic fleet in a foreign schema."""
    rng = np.random.default_rng(seed)
    ns = rng.integers(1, 4, n)
    fp = rng.uniform(60, 160, n).round(0)
    return pd.DataFrame({
        "GebaeudeNr": np.arange(1000, 1000 + n),
        "Baujahr_Klasse": rng.choice(list(ERA_CODE), n),
        "Geschossflaechen_m2": [list(np.round(rng.uniform(.8, 1.0, k) * f, 0))
                                for k, f in zip(ns, fp)],
        "Keller_beheizt": rng.random(n) < 0.4,
        "Sanierung_Anzahl": rng.integers(0, 4, n),
        "Bewohner": rng.integers(1, 6, n),
        "WP_Typ": rng.choice(list(WP_CODE), n),
        "Abgabe": rng.choice(list(EMIT_CODE), n),
        "WW_elektrisch": rng.random(n) < 0.25,
        "HGT12_pro_Tag": rng.uniform(2.5, 5.5, n).round(3),
        "Messtage": rng.integers(200, 2000, n),
    })


def to_roles(df):
    """Foreign schema -> the roles p_physics expects. The ONLY mapping code."""
    areas = df.Geschossflaechen_m2
    return pd.DataFrame({
        "Household_ID": df.GebaeudeNr,
        "area_m2": [float(np.sum(a)) for a in areas],
        "footprint_m2": [float(np.max(a)) for a in areas],
        "n_storeys_above": [len(a) for a in areas],
        "heated_basement": df.Keller_beheizt.astype(bool),
        "era": df.Baujahr_Klasse.map(ERA_CODE),
        "renovation_count": df.Sanierung_Anzahl.clip(0, 3),
        "residents": df.Bewohner.astype(float),
        "hp_type": df.WP_Typ.map(WP_CODE),
        "emitter": df.Abgabe.map(EMIT_CODE),
        "dhw_electric": df.WW_elektrisch.astype(bool),
        "hdd_per_day": df.HGT12_pro_Tag.astype(float),
        "n_days": df.Messtage.astype(int),
        "geometry_complete": True,
    })
