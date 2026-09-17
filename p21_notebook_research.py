"""P21 - search the verified notebook for a real Swiss typology and every other open value.

Step 1 (done by CLI, saved in outputs/p21/data/research/): NotebookLM web research, three
queries, 30 candidates, NOTHING imported automatically.
Step 2 `add`: import only the candidates argued to be primary Swiss or standards
documents, plus the primary documents already read outside the notebook in P14-P20.
Step 3 `ask`: every question is RESTRICTED to all sources EXCEPT the three
NotebookLM-generated "Research report" files, so no answer can be circular.

Usage: python p21_notebook_research.py add | ask [question_id ...]
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "p21" / "data"
OUT.mkdir(parents=True, exist_ok=True)
CLI = str(Path.home() / "AppData/Local/Packages/PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0"
          / "LocalCache/local-packages/Python313/Scripts/notebooklm.exe")
NB = "b02e42f0-3416-487a-a8eb-2046dfcf24a2"

# (research file, index) chosen from the candidates, and why
PICK = [("r1_typology", 1, "BFE official, U-values by construction period"),
        ("r1_typology", 6, "TEP Energy building-stock model, SIA Effizienzpfad"),
        ("r1_typology", 8, "SIA Grundlagenbericht SIA 2024"),
        ("r1_typology", 10, "ETH/CEPE Jakob-Jochem, EFH by construction period"),
        ("r2_envelope", 3, "FHNW prebound effect, measured U and basement b"),
        ("r2_envelope", 4, "EnFK Checkliste Waermebruecken, official Swiss proof"),
        ("r2_envelope", 8, "Kanton Uri Anhang 1a, legal U limits from SIA 380/1"),
        ("r2_envelope", 9, "GEAK checklist, b-factors"),
        ("r2_envelope", 10, "prEN 12831-1:2025 preview, design heat load"),
        ("r3_usage", 3, "IEA HPT Annex 46, heat pump water heaters, DHW demand"),
        ("r3_usage", 7, "RISE, field experience Swiss residential heat pumps"),
        ("r3_usage", 8, "Purdue, field performance Swiss heat pumps heating + DHW"),
        ("r3_usage", 9, "OST Feldmessungen 2021/22"),
        ("r3_usage", 10, "Energiehub, Heizleistungsbedarf, Zurich design temperature")]
EXTRA = [
    ("TABULA Common Calculation Method",
     "https://episcope.eu/fileadmin/tabula/public/docs/report/TABULA_CommonCalculationMethod.pdf"),
    ("BFH Waermebrueckenkatalog 2013",
     "https://www.bfh.ch/.documents/ris/2009-484.698.880/BFHID-1286002156-15/Waermebrueckenkatalog.pdf"),
    ("BFE Faktenblatt typischer Haushalt 2021", "https://pubdb.bfe.admin.ch/de/publication/download/10559"),
    ("SAFE Nipkow 2013 typischer Haushalt-Stromverbrauch",
     "https://www.energieeffizienz.ch/dam/studien/2013_typischer_haushalt_stromverbrauch_d/pdf_de/"
     "SAFE_typischer_Haushaltstromverbrauch_12_2013/Der%20typische%20Haushalt-SV-SAFE-Dez-2013.pdf"),
    ("OST Feldmessungen 2019/20", "https://www.ost.ch/fileadmin/dateiliste/3_forschung_dienstleistung/"
     "institute/ies/wpz/sonstige_wichtige_dokumente/2020_jahresbericht_feldmessungen.pdf"),
    ("OST Feldmessungen 2020/21", "https://www.ost.ch/fileadmin/dateiliste/3_forschung_dienstleistung/"
     "institute/ies/wpz/sonstige_wichtige_dokumente/2021_bericht_feldmessungen.pdf"),
    ("FAWA Schlussbericht 2004", "https://www.fws.ch/wp-content/uploads/2018/06/FAWA_Schlussbericht.pdf"),
]

IMPORT_LOGS = [HERE / "outputs/p21/data/import_log.json", HERE / "outputs/p22/data/import_log.json"]
EXTRA_VETTED_URLS = {
    "https://geothermie-schweiz.ch/wp_live/wp-content/uploads/2019/09/Bericht_LCC_EWS_2.pdf"}

TAIL = (" Answer ONLY from the sources. For every number give the source title and the "
        "table, section or page, the building type (single-family or not) and the year of the "
        "data. If the sources do not contain it, say 'not in the sources'.")
Q = {
    "q7_u_by_era": "Give U-values (W/m2K) for existing Swiss residential buildings, ideally "
                   "single-family houses, by construction period: walls, roofs, windows, floors, "
                   "and any area-weighted envelope mean or specific heat loss per period "
                   "(e.g. before 1920, 1920-45, 1946-60, 1961-70, 1971-80, 1981-90, 1991-2000, "
                   "2001-10, after 2010). Also the legal U limits that applied in each period.",
    "q8_envelope": "What do the sources give for (a) thermal bridge surcharges or linear psi "
                   "values used in Swiss proofs (SIA 380/1, EnFK checklist), (b) temperature "
                   "reduction factors b for floors against ground or unheated cellars, and "
                   "measured versus default b, (c) minimum air change rate for design heat load?",
    "q9_prebound": "What do the sources say about the prebound effect, or measured versus "
                   "calculated consumption or U-values in existing old buildings, and about "
                   "real indoor temperatures? Give the size of the effect by building age.",
    "q10_design_load": "What specific design heat load (W/m2 of energy reference area) or "
                       "Heizleistungsbedarf do the sources give by building age or standard, and "
                       "what design outdoor temperature for Zurich?",
    "q11_jaz_vintage": "How does field seasonal performance (JAZ/SPF) of Swiss heat pumps depend "
                       "on installation year or age, source type and distribution system? Give "
                       "values with years and sample sizes, including DHW-mode performance.",
    "q13_tep_charts": "In 'Erweiterung des Gebaeudeparkmodells gemaess SIA-Effizienzpfad Energie' "
                      "(TEP Energy 2016), Abbildung 30 to 33 show mean U-values of walls, windows, "
                      "roofs and cellar ceilings by construction period (vor 1920, 1920-1946, "
                      "1947-1975, 1976-1990, 1991-2009) for building types including EFH. Read the "
                      "EFH bars: give each value with its standard deviation where shown. Also any "
                      "table in that report or in Jakob (2002/2008) listing EFH U-values by period.",
    "q12_usage":"What do the sources give for standard usage: indoor setpoint, air change "
                 "rate, internal gains, and domestic hot water demand per person (litres or "
                 "kWh per day, at what temperature)?",
}


def cli(*args, timeout=300):
    return subprocess.run([CLI, *args], capture_output=True, text=True, encoding="utf-8",
                          timeout=timeout)


def add():
    log = []
    todo = []
    for f, i, why in PICK:
        s = json.load(open(OUT / "research" / (f + ".json"), encoding="utf-8"))["sources"][i - 1]
        todo.append((s["title"][:80], s["url"], why))
    todo += [(t, u, "primary document already read in P14-P20") for t, u in EXTRA]
    for title, url, why in todo:
        r = cli("source", "add", "-n", NB, "--json", "--timeout", "180", url, timeout=400)
        ok = r.returncode == 0
        log.append({"title": title, "url": url, "why": why, "ok": ok,
                    "out": (r.stdout or r.stderr)[-400:]})
        print("%-5s %-70s %s" % ("ok" if ok else "FAIL", title[:70], "" if ok else r.stderr[-200:]))
    json.dump(log, open(OUT / "import_log.json", "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)


def allowed_sources():
    r = cli("source", "list", "-n", NB, "--json")
    raw = r.stdout
    d = json.loads(raw[raw.index("{"):])
    if d.get("error"):
        raise SystemExit("notebooklm: %s\n-> run 'notebooklm login' in a terminal, then rerun."
                         % d.get("message", d))
    src = d["sources"]
    json.dump(src, open(OUT / "sources_after_import.json", "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    # VETTED WHITELIST (2026-09-11): the research runs flooded the notebook with all 30
    # candidates, duplicated, incl. blogs and errored items. Ask only: sources that existed
    # before this session's research, plus the ones argued and imported (import logs),
    # plus the ZHAW report. One copy per URL, ready only, AI-generated reports never.
    vetted = set(EXTRA_VETTED_URLS)
    for f in IMPORT_LOGS:
        if f.exists():
            vetted |= {r["url"] for r in json.load(open(f, encoding="utf-8")) if r.get("ok")}
    ok, seen = [], set()
    for s in sorted(src, key=lambda s: s["created_at"]):
        key = s["url"] or s["title"]
        if (s["title"].startswith("Research report") or s.get("status") != "ready"
                or key in seen):
            continue
        if s["created_at"] < "2026-09-11T17" or s["url"] in vetted:
            ok.append(s)
            seen.add(key)
    print("sources: %d in notebook, %d vetted and asked, %d excluded (unvetted, duplicate, error, AI)"
          % (len(src), len(ok), len(src) - len(ok)))
    pending = [s["title"][:60] for s in src if s.get("status") != "ready"]
    print("sources total %d, not ready: %s" % (len(src), pending or "none"))
    return [s["id"] for s in ok], {s["id"]: s["title"] for s in src}


def ask(ids):
    allow, titles = allowed_sources()
    print("asking over %d sources (AI-generated reports excluded)" % len(allow))
    for qid in ids:
        args = ["ask", "-n", NB, "--json"]
        for sid in allow:
            args += ["-s", sid]
        r = cli(*args, Q[qid] + TAIL, timeout=400)
        (OUT / (qid + ".json")).write_text(r.stdout or r.stderr, encoding="utf-8")
        try:
            d = json.loads(r.stdout)
        except json.JSONDecodeError:
            print("\n##### %s non-JSON rc=%d\n%s" % (qid, r.returncode, (r.stdout or r.stderr)[:2000]))
            continue
        cited = {}
        for ref in d.get("references", []):
            t = titles.get(ref["source_id"], "?")[:60]
            cited[t] = cited.get(t, 0) + 1
        print("\n##### %s   cited: %s\n%s" % (qid, cited, d.get("answer", "")))


if __name__ == "__main__":
    if sys.argv[1] == "add":
        add()
    else:
        ask(sys.argv[2:] or list(Q))
