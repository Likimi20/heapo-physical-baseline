"""P22 - one more notebook search: the envelope area split (wall / roof / floor / window).

Every envelope-mean U depends on it, and the live split .50/.22/.18/.10 carries the dead
TABULA-CH citation. NotebookLM research (outputs/p22/data/research/r4_areas.json) found 10
candidates; argued and imported: TABULA Scientific Report Germany (IWU), TEP Energy
INSPIRE final report, SIA Harmonisierung status report, SCCER-JASM. Skipped: an MFH
reference building, blogs, Wikipedia, a COVID occupancy paper.

The question is restricted to the non-AI sources, as in P21.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p21_notebook_research as nr

OUT = nr.HERE / "outputs" / "p22" / "data"
PICK = [(1, "TABULA Scientific Report DE, EFH component area ratios"),
        (3, "SIA Harmonisierung status report, TEP model indicators"),
        (7, "TEP INSPIRE final report, component area estimates"),
        (9, "SCCER-JASM, Wuest Partner EBF mapping")]
Q = {"q14_area_split":
     "For single-family houses (Swiss if available, otherwise German or TABULA European "
     "typology), what are the areas of the thermal envelope components relative to the "
     "energy reference or heated floor area: opaque external walls, windows, roof or top "
     "ceiling, and floor or cellar ceiling? Give each component's share of the total "
     "envelope area, the window-to-wall or window-to-floor ratio, the envelope-to-floor "
     "ratio (A/A_E, Gebaeudehuellzahl), and how these vary by construction period."}

if __name__ == "__main__":
    src = json.load(open(OUT / "research" / "r4_areas.json", encoding="utf-8"))["sources"]
    log = []
    for i, why in PICK:
        s = src[i - 1]
        r = nr.cli("source", "add", "-n", nr.NB, "--json", "--timeout", "180", s["url"], timeout=400)
        log.append({"title": s["title"], "url": s["url"], "why": why, "ok": r.returncode == 0})
        print("%-5s %s" % ("ok" if r.returncode == 0 else "FAIL", s["title"][:80]), flush=True)
    json.dump(log, open(OUT / "import_log.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    nr.OUT, nr.Q = OUT, Q
    nr.ask(list(Q))
