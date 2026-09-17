"""Run every test in this workstream, one command, one verdict.

The three test files stay SEPARATE on purpose - each proves a different guarantee and
each keeps its own transcript, so when something breaks you know which guarantee broke
rather than which line of a merged file did. This is only the front door:

  p_pipeline_test.py   the physics and the pipeline            141 checks
  p10_portability.py   the physics layer knows no HEAPO names   23 checks
  p28_page_test.py     the dashboard page actually executes

Run: ../venv_viz/Scripts/python.exe p_test_all.py
Exits non-zero if any suite fails, so it can gate a release or a push.
"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = [
    ("p_pipeline_test.py", "the physics and the pipeline"),
    ("p10_portability.py", "portability: no HEAPO names in the physics layer"),
    ("p28_page_test.py", "the dashboard page executes"),
]

print("=" * 78)
print("ALL TESTS - physical baseline workstream")
print("=" * 78)

results = []
for script, what in SUITES:
    path = HERE / script
    if not path.exists():
        print("\n  %-22s MISSING  %s" % (script, path))
        results.append((script, None, 0.0, "missing"))
        continue
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(path)], cwd=str(HERE),
                          capture_output=True, text=True)
    dt = time.time() - t0
    # Each suite prints its own count line; surface it rather than the whole transcript.
    tail = [ln.strip() for ln in (proc.stdout or "").splitlines()
            if "checks," in ln or "ALL VIEWS EXECUTED" in ln or "FAILURES" in ln]
    summary = tail[-1] if tail else "(no summary line)"
    ok = proc.returncode == 0
    print("\n  %-22s %-5s %5.1fs  %s" % (script, "OK" if ok else "FAIL", dt, what))
    print("      %s" % summary)
    if not ok:
        # On failure the detail is what matters, so print it rather than hide it.
        for ln in (proc.stdout or "").splitlines():
            if "FAIL" in ln or "Error" in ln or "Traceback" in ln:
                print("      %s" % ln.strip())
        if proc.stderr:
            print("      stderr: %s" % proc.stderr.strip().splitlines()[-1])
    results.append((script, ok, dt, summary))

passed = sum(1 for _, ok, _, _ in results if ok)
print("\n" + "=" * 78)
print("%d of %d suites passed, %.1fs total"
      % (passed, len(results), sum(d for _, _, d, _ in results)))
print("=" * 78)
raise SystemExit(0 if passed == len(results) else 1)
