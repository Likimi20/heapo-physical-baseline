"""P24c - clean notebook b02e42f0: duplicates, failed imports, unvetted research sources.

Authorised by Miguel 2026-09-12 ("yes delete the duplicates and the unchecked sources").
The three web-research runs imported all 30 candidates, several times over: 105 sources
against 42 before.

KEPT
  * everything that existed before this session's research (created_at < CUTOFF),
    INCLUDING the three NotebookLM-generated "Research report" files - Miguel's own
    earlier material. They stay excluded from questions by allowed_sources(), not deleted.
  * the sources argued and imported in P21/P22 (their import logs) and the ZHAW report -
    one copy per URL, the earliest READY one.

DELETED
  * further copies of a URL already kept
  * entries whose status is not "ready" (failed imports)
  * research-run sources that were never on the argued list

Guard: nothing created before CUTOFF is ever deleted, and the run aborts if that is
violated. Every deletion is printed with its reason first. The final list is saved.

Usage: python p24_notebook_cleanup.py --apply     (without --apply: plan only)
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p21_notebook_research as nr

CUTOFF = "2026-09-11T17"
OUT = HERE / "outputs" / "p24" / "data"


def source_list():
    r = nr.cli("source", "list", "-n", nr.NB, "--json")
    d = json.loads(r.stdout[r.stdout.index("{"):])
    if d.get("error"):
        raise SystemExit("notebooklm: %s" % d.get("message"))
    return d["sources"]


def plan(src):
    vetted = set(nr.EXTRA_VETTED_URLS)
    for f in nr.IMPORT_LOGS:
        if f.exists():
            vetted |= {r["url"] for r in json.load(open(f, encoding="utf-8")) if r.get("ok")}
    keep, drop, seen = [], [], set()
    for s in sorted(src, key=lambda s: s["created_at"]):
        key = s["url"] or s["title"]
        old = s["created_at"] < CUTOFF
        if old:
            keep.append((s, "pre-session"))
            seen.add(key)
            continue
        if s.get("status") != "ready":
            drop.append((s, "failed import (%s)" % s.get("status")))
        elif key in seen:
            drop.append((s, "duplicate copy"))
        elif s["url"] in vetted:
            keep.append((s, "argued and imported"))
            seen.add(key)
        else:
            drop.append((s, "unvetted research result"))
    return keep, drop


if __name__ == "__main__":
    src = source_list()
    keep, drop = plan(src)
    print("notebook holds %d sources: keep %d, delete %d\n" % (len(src), len(keep), len(drop)))
    for s, why in drop:
        print("  DELETE  %-52s %-24s %s" % (s["title"][:52], why, s["created_at"][:16]))
    bad = [s for s, _ in drop if s["created_at"] < CUTOFF]
    if bad:
        raise SystemExit("ABORT: %d pre-session sources in the delete list" % len(bad))
    if "--apply" not in sys.argv:
        print("\nplan only. Rerun with --apply to delete.")
        raise SystemExit(0)
    ok = 0
    for s, why in drop:
        r = nr.cli("source", "delete", "-n", nr.NB, s["id"], "--yes", timeout=120)
        ok += r.returncode == 0
        if r.returncode != 0:
            print("  FAILED %s: %s" % (s["id"][:8], (r.stderr or r.stdout)[-160:]))
    print("\ndeleted %d of %d" % (ok, len(drop)))
    after = source_list()
    json.dump(after, open(OUT / "notebook_sources_after_cleanup.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print("notebook now holds %d sources; list saved." % len(after))
    for s in sorted(after, key=lambda s: s["created_at"]):
        print("  %-58s %s" % (s["title"][:58], s["created_at"][:16]))
