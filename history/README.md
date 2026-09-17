# history/ — superseded stages, kept as the audit trail

Moved here 2026-09-11 (Miguel: "anything old or not relevant anymore, archive it").
**Nothing here is live. Nothing here reproduces unchanged:** the scripts use paths
relative to the project root and constants from registries that no longer exist.
Read them as records. Their findings are in CLAUDE.md.

| stage | what it was | superseded by |
|---|---|---|
| P2 two baselines | first two-baseline run | VOID since P4 (dead balance-temperature route) |
| P3 geometry | audited per-storey geometry | folded into `p_physics` / adapter |
| P4 deficiency | first end-to-end run | VOID since P6 (HDD bias, footprint fix) |
| P5 bands | Monte Carlo band on old constants | `p11_export.py` recomputes its own bands |
| P6 window & PV | HDD bias correction, PV decision | P18 / P22 normal-year HDD; PV rule still stands (CLAUDE.md) |
| P7 compensation | C-class mechanism test: NOT SHOWN | a record; re-test needs the new constants |
| P8 capacity | capacity-cost scenario | old design load (−10 °C, n 0.7); recompute if shipped |
| P9 envelope validation | rank validation ρ 0.536 | P17 / P20 / P21 validations on sourced constants |
| P12 integration | fault models, 2x2 | P13 (fault shown, never gates) |
| P14 level check | appliance term | finding kept; the function stays in `p_physics` |
| P15 design load | EN 12831 conventions | decided in P21/P22 (T_design −8 °C, n 0.6) |
| P16 thermal bridges | ΔU_tb scenarios | adopted in P22 |
| P17 slope step | free heating-season step, band | adopted in P13 v2 |
| P18 normal-year HDD | station normals | adopted in P22 (`station_normals`) |
| P20 / P21 scenario scripts | sourced JAZ / U scenarios | adopted in P22; their reports stay in `outputs/p20`, `outputs/p21` as evidence |
| `outputs/p13_v1` | P13 v1 queue (point estimate, all days) | P13 v2 |
