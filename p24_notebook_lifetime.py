"""P24 - heat-pump service life, from the verified notebook (AI reports excluded).

Miguel 2026-09-11: term_vintage should become a RECOMMENDATION - replace the unit only if
it is out of its life cycle or close to it. That needs a sourced service life.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p21_notebook_research as nr

nr.OUT = nr.HERE / "outputs" / "p24" / "data"
nr.OUT.mkdir(parents=True, exist_ok=True)
nr.Q = {"q15_lifetime":
        "What service life, technical lifetime, useful life or replacement interval do the "
        "sources give for heat pumps (air-to-water, brine-to-water / ground-source), for the "
        "borehole or ground loop, and for other heating system components? Also any "
        "statement on when replacing an operating heat pump before the end of its life is "
        "or is not economic, and on efficiency loss with operating age."}

if __name__ == "__main__":
    nr.ask(list(nr.Q))
