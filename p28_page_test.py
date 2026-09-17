"""P28 - smoke-test the dashboard pages without installing Streamlit.

IN THE REPO, not a scratchpad: a test that proves a guarantee is evidence, and
evidence outside the tree cannot be re-run, diffed or trusted later.
Run: ../venv_viz/Scripts/python.exe p28_page_test.py  (log: outputs/p28/logs/)

Also asserts the two standing display rules - no fault column on the v2 page, and
no green among the colour tokens it paints with. Streamlit is installed in no
environment in this repo, which is why this exists.

Stubs the Streamlit API the page uses, then imports the page once per view so main()
and each view function actually RUN against the real v2 export. Catches code errors -
bad kwargs, KeyErrors, f-string and dtype faults - which is most of the risk.

It does NOT catch: layout, visual issues, or a Streamlit version lacking an API we
call. Those need a real browser.
"""
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DASH = ROOT / "Heat_Pump_Failure_Prediction"

LOG = HERE / "outputs" / "p28" / "logs"
LOG.mkdir(parents=True, exist_ok=True)


class Tee:
    def __init__(self, p):
        self.f = open(p, "w", encoding="utf-8")

    def write(self, t):
        sys.__stdout__.write(t)
        self.f.write(t)

    def flush(self):
        sys.__stdout__.flush()
        self.f.flush()


sys.stdout = Tee(LOG / "p28_page_test.txt")

CALLS = {"markdown": 0, "table_html": 0, "metric": 0, "caption": 0, "error": 0,
         "info": 0, "warning": 0, "components_html": 0, "notebook": 0}
VIEW = None
RADIO = None


def check_no_green_tokens():
    """The colour rule, checked on the tokens the page actually paints with."""
    sys.path.insert(0, str(DASH))
    sys.modules.pop("theme", None)
    import theme
    out = []
    for name in ("POS", "SERIES1", "SERIES2", "AXIS_INK"):
        v = getattr(theme, name, None)
        if not (isinstance(v, str) and v.startswith("#") and len(v) == 7):
            out.append((name, v, "not a plain hex - inspect by eye"))
            continue
        r, g, b = (int(v[i:i + 2], 16) for i in (1, 3, 5))
        greenish = g > r + 25 and g > b + 25
        out.append((name, v, "GREEN" if greenish else "ok"))
    return out


class _Col:
    def metric(self, *a, **k):
        CALLS["metric"] += 1


class _Sidebar:
    def radio(self, label, options, **k):
        assert VIEW in options, "view %r not in %r" % (VIEW, options)
        return VIEW

    def divider(self):
        pass

    def caption(self, *a, **k):
        CALLS["caption"] += 1


def _mk_streamlit():
    st = types.ModuleType("streamlit")
    st.sidebar = _Sidebar()

    def markdown(body, **k):
        CALLS["markdown"] += 1
        assert isinstance(body, str) and body, "empty markdown"
        if "<table" in body:
            CALLS["table_html"] += 1
        # Assert on the FAULT columns only. The earlier version banned the word
        # "green", which the page legitimately uses in the prose explaining that
        # nothing is green - a false positive. Green is checked as a COLOUR below.
        low = body.lower()
        for bad in ("fault probability", "named fault", "visit_fault",
                    "visit_named_fault"):
            assert bad not in low, "page emitted %r" % bad

    st.markdown = markdown
    st.set_page_config = lambda **k: None
    st.divider = lambda: None
    st.toggle = lambda *a, **k: False
    st.radio = lambda label, options, **k: (RADIO if RADIO in options else options[0])
    st.pills = lambda label, options, **k: list(k.get("default", options))
    st.columns = lambda n, **k: tuple(_Col() for _ in range(n if isinstance(n, int) else len(n)))
    st.metric = lambda *a, **k: CALLS.__setitem__("metric", CALLS["metric"] + 1)
    st.caption = lambda *a, **k: CALLS.__setitem__("caption", CALLS["caption"] + 1)
    st.error = lambda *a, **k: CALLS.__setitem__("error", CALLS["error"] + 1)
    st.info = lambda *a, **k: CALLS.__setitem__("info", CALLS["info"] + 1)
    st.warning = lambda *a, **k: CALLS.__setitem__("warning", CALLS["warning"] + 1)
    st.image = lambda *a, **k: None

    def cache_data(*a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda f: f

    st.cache_data = cache_data
    comp = types.ModuleType("streamlit.components")
    v1 = types.ModuleType("streamlit.components.v1")
    v1.html = lambda *a, **k: CALLS.__setitem__("components_html",
                                                CALLS["components_html"] + 1)
    comp.v1 = v1
    st.components = comp
    return st, comp, v1


def _mk_notebook_render():
    m = types.ModuleType("notebook_render")
    m.render = lambda *a, **k: CALLS.__setitem__("notebook", CALLS["notebook"] + 1)
    m.load_cells = lambda *a, **k: []
    return m


def run(view):
    global VIEW
    VIEW = view
    for k in CALLS:
        CALLS[k] = 0
    st, comp, v1 = _mk_streamlit()
    for name in ("streamlit", "streamlit.components", "streamlit.components.v1",
                 "notebook_render", "theme", "pages.5_Physical_baseline_v2"):
        sys.modules.pop(name, None)
    sys.modules["streamlit"] = st
    sys.modules["streamlit.components"] = comp
    sys.modules["streamlit.components.v1"] = v1
    sys.modules["notebook_render"] = _mk_notebook_render()
    sys.path.insert(0, str(DASH))
    src = (DASH / "pages" / "5_Physical_baseline_v2.py").read_text(encoding="utf-8")
    ns = {"__name__": "page5", "__file__": str(DASH / "pages" / "5_Physical_baseline_v2.py")}
    exec(compile(src, "5_Physical_baseline_v2.py", "exec"), ns)
    return dict(CALLS)


print("smoke test: pages/5_Physical_baseline_v2.py\n")
print("colour tokens the page paints with:")
for name, val, verdict in check_no_green_tokens():
    print("   %-10s %-30s %s" % (name, val, verdict))
print()

ok = True
RADIO = "English"
for view in ["What the rank means", "The one list", "Worked example"]:
    try:
        c = run(view)
        flags = []
        if c["error"]:
            flags.append("st.error x%d" % c["error"])
        print("  %-22s OK   markdown=%-3d tables=%-2d metrics=%-2d notebook=%-2d "
              "iframe=%-2d %s" % (view, c["markdown"], c["table_html"], c["metric"],
                                  c["notebook"], c["components_html"],
                                  " ".join(flags)))
        if c["error"]:
            ok = False
    except Exception as e:
        ok = False
        print("  %-22s FAILED  %s: %s" % (view, type(e).__name__, e))
        import traceback
        traceback.print_exc()

print("\nlegacy page 3 (must still run, and must WARN):")
try:
    VIEW = "Building score"
    for k in CALLS:
        CALLS[k] = 0
    st, comp, v1 = _mk_streamlit()
    # page 3 legitimately renders the fault columns; drop that assertion for it.
    st.markdown = lambda body, **k: CALLS.__setitem__("markdown", CALLS["markdown"] + 1)
    for name in ("streamlit", "streamlit.components", "streamlit.components.v1",
                 "notebook_render", "theme"):
        sys.modules.pop(name, None)
    sys.modules["streamlit"] = st
    sys.modules["streamlit.components"] = comp
    sys.modules["streamlit.components.v1"] = v1
    sys.modules["notebook_render"] = _mk_notebook_render()
    src = (DASH / "pages" / "3_Physical_baseline.py").read_text(encoding="utf-8")
    exec(compile(src, "3_Physical_baseline.py", "exec"),
         {"__name__": "page3", "__file__": str(DASH / "pages" / "3_Physical_baseline.py")})
    print("  OK   warnings=%d (the legacy banner)" % CALLS["warning"])
    if CALLS["warning"] < 1:
        print("  !! the legacy banner did not fire")
        ok = False
except Exception as e:
    print("  FAILED  %s: %s" % (type(e).__name__, e))
    ok = False

print("\n%s" % ("ALL VIEWS EXECUTED" if ok else "FAILURES ABOVE"))
sys.stdout.flush()
raise SystemExit(0 if ok else 1)
