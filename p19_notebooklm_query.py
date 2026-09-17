"""P19 - query the project's verified-source notebook for the registry constants.

Root CLAUDE.md, "References - verified sources only": the Fraunhofer ISE NotebookLM
notebook is the source of record for physics constants and standards. Answers are
grounded ONLY in the documents uploaded there. When it has no source, that is the
finding - nothing falls back to training knowledge.

Driven through the notebooklm CLI (the MCP server is configured but not loaded in
this session). Every question and raw JSON answer is written to disk, so a claim in
the registry can be traced to the exact answer and its citations.

Usage: python p19_notebooklm_query.py [question_id ...]   (default: all)
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs" / "p19" / "data" / "notebooklm"
OUT.mkdir(parents=True, exist_ok=True)
CLI = (Path.home() / "AppData/Local/Packages/PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0"
       / "LocalCache/local-packages/Python313/Scripts/notebooklm.exe")
NOTEBOOK = "b02e42f0-3416-487a-a8eb-2046dfcf24a2"

TAIL = (" Answer ONLY from the uploaded sources. For every number give the source title and "
        "the section, table or page. If the sources do not contain it, say explicitly "
        "'not in the sources' rather than estimating.")

Q = {
    "q1_u_by_era": "What U-values (W/m2K) do the sources give for existing residential "
                   "buildings by construction period - walls, roofs, windows, floors, or an "
                   "area-weighted envelope mean - for periods such as before 1975, 1976-1990, "
                   "1991-2000, 2001-2010 and after 2010? Swiss data preferred, German or "
                   "Central European otherwise.",
    "q2_spf_emitter": "What seasonal performance factors (SPF / JAZ) do field measurements "
                      "report for air-source and ground-source heat pumps, split by heat "
                      "distribution system (underfloor heating versus radiators) or by supply "
                      "temperature? Give sample sizes and whether the building is new or "
                      "renovated.",
    "q3_dhw": "What do the sources give for domestic hot water: heat pump SPF in DHW mode, "
              "and DHW energy demand per person per day (kWh or litres at what temperature "
              "rise)?",
    "q4_tb_ground_air": "What default thermal bridge surcharge (delta U_WB or delta U_tb, "
                        "W/m2K) do the sources give; what temperature correction or reduction "
                        "factor (b or f_g) for floors against ground or unheated cellars; and "
                        "what minimum air change rate for heat load calculation (EN 12831)?",
    "q5_hdd_climate": "How do the sources define heating degree days (base temperature, "
                      "heating limit, SIA 381/3 or 20/12 convention), the design outdoor "
                      "temperature, the indoor setpoint, and the standard air change rate "
                      "used in building energy calculations?",
    "q6_prior_work": "What prior work in the sources builds physics-based or hybrid "
                     "expected-consumption baselines for heat pumps from smart meter data, or "
                     "uses such baselines for fault detection? Include anything on the HEAPO "
                     "dataset, the performance gap or prebound effect, and heat pump "
                     "oversizing or cycling losses.",
}


def ask(qid, text):
    r = subprocess.run([str(CLI), "ask", "-n", NOTEBOOK, "--json", text + TAIL],
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    raw = r.stdout.strip()
    (OUT / (qid + ".json")).write_text(raw or r.stderr, encoding="utf-8")
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        print("\n##### %s  (non-JSON output, rc=%d)\n%s" % (qid, r.returncode, (raw or r.stderr)[:3000]))
        return
    ans = d.get("answer") or d.get("text") or d.get("response") or ""
    print("\n##### %s\n%s" % (qid, ans))
    refs = d.get("references") or d.get("citations") or []
    for ref in refs:
        print("   ref:", json.dumps(ref, ensure_ascii=False)[:300])


if __name__ == "__main__":
    for qid in (sys.argv[1:] or list(Q)):
        ask(qid, Q[qid])
