"""P22 - apply Miguel's decisions of 2026-09-11 to the standards registry.

Deterministic: rerunning reproduces constants_ch.json. The registry keeps the PUBLISHED
inputs (TEP element U-values, MuKEn limits, the area split) under "inputs"; the envelope
means are DERIVED here and re-derived by p_pipeline_test.py section K to prove they match.

Decisions applied (sources in outputs/p21/reports/p21_findings.md):
  1 as-built U from TEP Energy 2016 (BFE), EFH, Abb. 30-33; post-2010 = MuKEn band
  2 heating JAZ = OST P+I 2020 / RISE 2023 heating-only column, DHW JAZ by pump type
  3 b_ground 0.5, band 0.5-0.8 (measured FHNW 2017 -> normative SIA 380/1)
  4 thermal bridge surcharge 0.10 on both baselines (TABULA CCM)
  5 DHW demand 2.61 kWh/person/day (FAWA; SIA 385/2 via IEA Annex 46)
  6 design outdoor temperature -8 C (EnDK 2014; CEPE 2002 / SIA 382/4)
  7 air change 0.6 (TABULA Common Calculation Method, European standard method)
"""
import json
from pathlib import Path

import numpy as np

REG = Path(__file__).resolve().parent / "constants_ch.json"
P21 = " See outputs/p21/reports/p21_findings.md."

INPUTS = {
    "tep2016_efh": {
        "source": "TEP Energy 2016, Erweiterung des Gebaeudeparkmodells gemaess SIA-Effizienzpfad "
                  "Energie, BFE Schlussbericht, sec. 3.2.1, Abb. 30-33, EFH (mean, SD)",
        "status": "VERIFIED",
        "note": "Read off bar charts by the notebook (q13, outputs/p21/data/); passes the report's "
                "own text check (roof -58% / cellar -42% vs ~60/40%). Approximate to ~0.05.",
        "periods": {
            "pre1920":   {"wall": [.86, .10], "window": [2.20, .20], "roof": [.75, .15], "floor": [.67, .03]},
            "1920_1946": {"wall": [.90, .10], "window": [2.09, .20], "roof": [.71, .15], "floor": [.67, .03]},
            "1947_1975": {"wall": [.95, .20], "window": [1.98, .20], "roof": [.70, .05], "floor": [.70, .05]},
            "1976_1990": {"wall": [.65, .15], "window": [1.75, .20], "roof": [.60, .10], "floor": [.60, .10]},
            "1991_2009": {"wall": [.27, .07], "window": [1.40, .20], "roof": [.25, .06], "floor": [.35, .06]}}},
    "pre1975_stock_share": {
        "source": "TEP Energy 2016, Tabelle 19, EFH floor-area share by period",
        "status": "VERIFIED", "value": {"pre1920": 13, "1920_1946": 20, "1947_1975": 27}},
    "muken": {
        "source": "EnDK / Energiehub Gebaeude 2014, Heizleistungsbedarf, Abb. 13 (MuKEn limits)",
        "status": "VERIFIED",
        "value": {"2008": {"wall": .20, "roof": .20, "floor": .25, "window": 1.3},
                  "2014": {"wall": .17, "roof": .17, "floor": .25, "window": 1.0}}},
}
AREA_SPLIT = {
    "source": "TEP Energy / INSPIRE International Final Report (2015), Table 15, pp. 42-43, "
              "Swiss reference SFH (Ott et al. 2011, SIA 2009)",
    "status": "VERIFIED",
    "note": "Read in the primary PDF: facade excl. windows 206 m2, pitched roof 120, cellar "
            "ceiling 80, windows 3.3+8.3+13.2+8.3 = 33.1; envelope 439.1 m2 on 210 m2 GHFA. "
            "Replaces .50/.22/.18/.10, which carried the dead TABULA-CH citation. Found via "
            "notebook q14 (outputs/p22/data/q14_area_split.json).",
    "value": {"wall": 0.469, "roof": 0.273, "floor": 0.182, "window": 0.075},
    "alternative": {
        "source": "TABULA Scientific Report Germany (IWU 2012), Section 6.2, Table 25, SFH I <=1978",
        "note": "Band only: every derived U band is widened to cover the value under this split.",
        "value": {"wall": 0.395, "roof": 0.290, "floor": 0.240, "window": 0.075}}}


def envelope(el, w):
    m = sum(w[k] * el[k][0] for k in w)
    sd = float(np.sqrt(sum((w[k] * el[k][1]) ** 2 for k in w)))
    return m, sd


def derive_u(inputs):
    """Envelope-mean U per HEAPO era, (value, lo, hi). Pure function of the inputs.

    Value and SD band from the primary split; the band is widened to cover the value
    under the alternative split, so split uncertainty is carried, not hidden.
    """
    main = _derive(inputs, inputs["area_split"]["value"])
    alt = inputs["area_split"].get("alternative")
    if not alt:
        return main
    other = _derive(inputs, alt["value"])
    return {e: (main[e][0], round(min(main[e][1], other[e][0]), 4),
                round(max(main[e][2], other[e][0]), 4)) for e in main}


def _derive(inputs, w):
    tep = inputs["tep2016_efh"]["periods"]
    sh = inputs["pre1975_stock_share"]["value"]
    tot = sum(sh.values())
    pm = sum(sh[p] / tot * envelope(tep[p], w)[0] for p in sh)
    psd = sum(sh[p] / tot * envelope(tep[p], w)[1] for p in sh)
    out = {"pre1975": (pm, psd)}
    out["1976_1990"] = envelope(tep["1976_1990"], w)
    out["1991_2000"] = out["2001_2010"] = envelope(tep["1991_2009"], w)
    mk = inputs["muken"]["value"]
    m08 = sum(w[k] * mk["2008"][k] for k in w)
    m14 = sum(w[k] * mk["2014"][k] for k in w)
    res = {e: (round(m, 4), round(m - s, 4), round(m + s, 4)) for e, (m, s) in out.items()}
    res["post2010"] = (round((m08 + m14) / 2, 4), round(m14, 4), round(m08, 4))
    res["reference"] = (round(m14, 4), round(m14, 4), round(m14, 4))
    return res


def put(K, key, v, lo, hi, unit, source, section, status, note):
    K[key] = {"value": v, "lo": lo, "hi": hi, "unit": unit, "source": source,
              "section": section, "status": status, "note": note}


if __name__ == "__main__":
    reg = json.load(open(REG, encoding="utf-8"))
    K = reg["constants"]
    inp = reg.setdefault("inputs", {})
    inp.update(INPUTS)
    inp["area_split"] = AREA_SPLIT
    U = derive_u(inp)
    split_note = " Inherits area_split status: %s." % inp["area_split"]["status"]
    for era in ["pre1975", "1976_1990", "1991_2000", "2001_2010"]:
        v, lo, hi = U[era]
        put(K, "u_era_" + era, v, lo, hi, "W/m2K", "derived: TEP Energy 2016 EFH x area_split",
            "Abb. 30-33 +/- aggregated SD; pre-1975 pooled by Tabelle 19 shares", "DERIVED",
            "TEP pools 1991-2009, so 1991_2000 = 2001_2010." + split_note + P21)
    v, lo, hi = U["post2010"]
    put(K, "u_era_post2010", v, lo, hi, "W/m2K", "derived: MuKEn 2014 (lo) to MuKEn 2008 (hi) x area_split",
        "EnDK 2014 Abb. 13", "DERIVED", "Legal limits, not a measured stock." + split_note + P21)
    v, lo, hi = U["reference"]
    put(K, "u_reference", v, lo, hi, "W/m2K", "derived: MuKEn 2014 limits x area_split",
        "EnDK 2014 Abb. 13", "DERIVED",
        "Code-compliant today. Band pending a sourced split range." + split_note + P21)
    OST = "OST WPZ Buchs P+I 11/12-2020 Tabelle 1; RISE IEA HPC 2023 Paper 478 Table 1"
    for key, v, lo in [("jaz_ashp_floor", 3.7, 3.5), ("jaz_ashp_lowrad", 3.3, 3.1),
                       ("jaz_ashp_rad", 2.9, 2.8), ("jaz_gshp_floor", 5.7, 4.9),
                       ("jaz_gshp_lowrad", 5.0, 4.6), ("jaz_gshp_rad", 4.4, 4.3)]:
        put(K, key, v, lo, v, "-", OST, "value = heating-only column; lo = heating & TWW column",
            "VERIFIED", "Space heating only; DHW is a separate term. N=26 (RISE)." + P21)
    put(K, "jaz_dhw_hp", 2.8, 2.5, 2.9, "-", "OST P+I 2020 Abb. 3; OST Feldmessungen 2021/22 sec. 2.2",
        "air-source DHW: JAZ 2.8 (2018), JAZ+ 2.9 / WNG 2.5 (2021/22)", "VERIFIED",
        "AIR-SOURCE DHW JAZ (key name kept for compatibility)." + P21)
    put(K, "jaz_dhw_gshp", 3.3, 2.9, 3.3, "-", "OST P+I 2020 Abb. 3; OST Feldmessungen 2021/22 sec. 2.2",
        "ground-source DHW: JAZ 3.3 (2018, RISE 3.2), JAZ+ 3.3 / WNG 2.9 (2021/22)", "VERIFIED", P21.strip())
    put(K, "b_ground", 0.5, 0.5, 0.8, "-",
        "Hoffmann & Geissler, FHNW, Energy Procedia 122 (2017); TABULA CCM eq. 4",
        "measured 0.51, recommended 0.5 for existing buildings (lo); SIA 380/1:2015 0.7/0.8 (hi)",
        "VERIFIED", P21.strip())
    put(K, "du_thermal_bridge", 0.10, 0.05, 0.10, "W/m2K", "TABULA Common Calculation Method (IEE TABULA)",
        "eq. 4 / Table 3 and worked example: 0.10 original, 0.05 advanced refurbishment", "VERIFIED",
        "Applied with ONE draw to both baselines: cancels in the deficiency." + P21)
    put(K, "dhw_kwh_person_day", 2.61, 2.33, 3.20, "kWh/p/d",
        "FAWA 2004 Table 3 p.44 (3,811 kWh/yr, 4-person EFH); SIA 385/2 via IEA HPT Annex 46 Table 1",
        "value FAWA measured; band SIA 385/2 simple 40 L to high 55 L at dT 50 K", "VERIFIED",
        "dT 50 K is a physics assumption, not stated in the sources." + P21)
    put(K, "t_design", -8.0, -8.0, -8.0, "degC", "EnDK / Energiehub 2014 Abb. 43-44; CEPE ETH 2002 sec. 4.2.10",
        "Zurich 'Klima A, kalt' -8 C; SIA 382/4 -8 C", "VERIFIED", "Affects design_kw only." + P21)
    put(K, "n_air", 0.6, 0.6, 0.6, "1/h",
        "TABULA Common Calculation Method (IEE TABULA) - European standard method",
        "Table 1: n_air,use 0.4 + n_air,infiltration 0.2", "VERIFIED",
        "Replaces SIA 380/1 0.7, which is not in the verified notebook." + P21)
    VNOTE = (" Ratio = older units' field JAZ / the table's. FAWA saw no ageing loss over 9 "
             "operating years, so this is technology vintage. P23 (outputs/p23/).")
    put(K, "jaz_vintage_old_air", 0.794, 0.794, 0.871, "-",
        "FAWA 2004 fleet mean (air 2.7, 1996-2003) / OST P+I 2020 Abb. 3 total (air 3.4); hi vs OST 2021/22 WNG 3.10",
        "notebook q2 / q11 (sources 13, 15, OST 2021/22)", "DERIVED", VNOTE)
    put(K, "jaz_vintage_old_ground", 0.761, 0.761, 0.827, "-",
        "FAWA 2004 fleet mean (ground 3.5, 1996-2003) / OST P+I 2020 Abb. 3 total (ground 4.6); hi vs OST 2021/22 WNG 4.23",
        "notebook q2 / q11 (sources 13, 15, OST 2021/22)", "DERIVED", VNOTE)
    put(K, "jaz_vintage_year_old", 1999.0, 1999.0, 1999.0, "year",
        "FAWA 2004: installations 1996-2003", "midpoint", "DERIVED", VNOTE)
    put(K, "jaz_vintage_year_new", 2017.0, 2017.0, 2017.0, "year",
        "OST WPZ field programme: new installations 2015-2019", "midpoint", "DERIVED", VNOTE)
    ZHAW = ("Hubbuch & Vecsei, ZHAW Institut fuer Facility Management, 'Lebenszykluskosten von "
            "Waermepumpen' (for SIG Geneve), Weibull fit + Kaplan-Meier on Swiss owner survey")
    LNOTE = (" value = expected life, lo/hi = +/- 1 SD of the life distribution. Read in the "
             "primary PDF and confirmed in notebook b02e42f0 (q15, source Bericht_LCC_EWS_2). "
             "The same report also gives expert opinion (air 18+/-3, ground 20+/-4) and its LCC "
             "baseline (air 16, ground 23); the survey fit is used because it rests on measured "
             "failures - sensitivity in P24.")
    put(K, "hp_service_life_ground", 26.7, 22.0, 31.4, "yr", ZHAW,
        "Tabelle 4.7: expected 26.7 +/- 0.8 yr, SD 4.7 +/- 0.6 yr, k = 7; N = 223", "VERIFIED",
        "Borehole assumed 50 yr (SIA 384/6), so a unit replacement keeps the probe." + LNOTE)
    put(K, "hp_service_life_air", 20.0, 13.0, 27.0, "yr", ZHAW,
        "Tabelle 4.8: expected 20 +/- 2 yr, SD 7 +/- 2 yr, k = 3.0; N = 53 (43 from one firm)",
        "VERIFIED", "Authors: less reliable than ground-source." + LNOTE)
    reg["applied"] = {"date": "2026-09-11", "by": "p22_registry.py",
                      "decisions": "Miguel 2026-09-11: 1-6 yes, 7 yes as European standard method"}
    json.dump(reg, open(REG, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for e, t in U.items():
        print("  %-10s %s" % (e, t))
