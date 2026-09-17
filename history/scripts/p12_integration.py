"""P12 - integrating Aaditya's fault models. The two-axis 2x2, populated at last.

THE INTEGRATION POINT NAMED SINCE THE WORKSTREAM STARTED. Physics says a building
is materially above what it should consume; the fault model says which controller
setting is wrong. The two compose.

Bundle: ../Heat_Pump_Failure_Prediction/artifacts/models.joblib
  3 model types x (1 binary + 4 multilabel targets), 38 features, seed 42,
  trained 2026-09-10, 89 train / 30 test, base rate 0.854.

FOUR THINGS THIS RUN ESTABLISHES BEFORE POPULATING ANYTHING.

  1. THE AXES ARE NOT INDEPENDENT. 8 of the 38 features are fields the physical
     model also requires - construction year, heated area, residents, HP type,
     heating capacity, both emitter flags, DHW source. So a 2x2 agreement is
     PARTLY MECHANICAL. It is still operationally meaningful, because the two
     cells imply different interventions, but it is NOT two independent
     measurements agreeing and must never be presented as one.

  2. ON AUDITED HOUSEHOLDS THE FAULT IS RECORDED, NOT PREDICTED. All 214 carry
     the inspector's flags. The model exists to extend the fault axis to
     households WITHOUT an audit. So the 2x2 here is built on the RECORDED flags,
     and the model prediction is carried alongside as a comparison - which
     doubles as an out-of-sample check on the model.

  3. 89 OF 119 ARE TRAINING HOUSEHOLDS. Any accuracy on them is optimistic.
     Train and test are reported separately, always.

  4. THE BASE RATE IS 0.854. Predicting "fault" for everyone scores 85.4%.
     Accuracy is close to meaningless here; only per-target discrimination
     against the recorded flag means anything.

THE TEST THAT MATTERS: does the fault model track the RECORDED FAULT, or does it
track the BUILDING? Given the shared inputs it could be learning "old big house"
and scoring well because old big houses more often carry faults. Measured in
section 4 by comparing its correlation with the truth against its correlation
with the physical excess.

numpy + pandas + sklearn (to unpickle only). No fitting here.
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p_physics as ph
from p_adapter_heapo import load_households, modellable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AAD = ROOT / "Heat_Pump_Failure_Prediction"
OUT = HERE / "outputs" / "p12"
for d in [OUT / "data", OUT / "logs", OUT / "figures", OUT / "reports"]:
    d.mkdir(parents=True, exist_ok=True)

NBOOT = 2000
RNG = np.random.default_rng(20260910)
SHARED = ["Building_ConstructionYear", "Building_FloorAreaHeated_Total",
          "Building_Residents", "HeatPump_Installation_Type",
          "HeatPump_Installation_HeatingCapacity",
          "HeatDistribution_System_Radiators",
          "HeatDistribution_System_FloorHeating", "DHW_Production_ByHeatPump"]


class Tee:
    def __init__(self, p):
        self.f = open(p, "w", encoding="utf-8")

    def write(self, s):
        sys.__stdout__.write(s)
        self.f.write(s)

    def flush(self):
        sys.__stdout__.flush()
        self.f.flush()


def head(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    d = pos[:, None] - neg[None, :]
    return ((d > 0).sum() + 0.5 * (d == 0).sum()) / (len(pos) * len(neg))


def auc_ci(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) < 3 or len(neg) < 3:
        return auc(pos, neg), np.nan, np.nan
    b = [auc(RNG.choice(pos, len(pos), True), RNG.choice(neg, len(neg), True))
         for _ in range(NBOOT)]
    return auc(pos, neg), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


sys.stdout = Tee(OUT / "logs" / "p12_run.txt")

head("1. THE TWO SOURCES, AND WHAT THEY SHARE")

# The bundle is NOT self-contained: its pickle references `heapo_core`, so that
# directory must be importable or joblib.load raises ModuleNotFoundError. Worth
# knowing before anyone deploys it somewhere the source tree is absent.
sys.path.insert(0, str(AAD))
B = joblib.load(AAD / "artifacts/models.joblib")
D = pd.read_parquet(AAD / "artifacts/dataset.parquet")
D["Household_ID"] = pd.to_numeric(D.Household_ID, errors="coerce").astype("Int64")
E = pd.read_parquet(HERE / "outputs/export/physical_baseline_v1.parquet")
fc, targets = B["feature_columns"], B["targets"]
print("  fault bundle : %d features, %d targets, %d train / %d test, base rate %.3f"
      % (len(fc), len(targets), len(B["train_ids"]), len(B["test_ids"]),
         B["base_rate"]))
print("  physical export : %d households" % len(E))
print("  fault cohort    : %d households" % len(D))
ov = set(D.Household_ID.dropna().astype(int)) & set(E.household_id)
print("  overlap         : %d  (the fault cohort is a SUBSET of ours)" % len(ov))

print("\n  SHARED INPUTS - %d of %d fault-model features are physical-model roles:"
      % (len(SHARED), len(fc)))
for c in SHARED:
    print("    %s" % c)
print("\n  THE AXES ARE THEREFORE NOT INDEPENDENT. Agreement between them is")
print("  partly mechanical. Operationally meaningful - the cells imply different")
print("  interventions - but NEVER 'two independent methods agreeing'.")

head("2. PREDICT - and keep train and test apart")

X = D.set_index("Household_ID")[fc]
tr, te = set(B["train_ids"]), set(B["test_ids"])
P = pd.DataFrame(index=X.index)
P["split"] = np.where(P.index.isin(tr), "train",
                      np.where(P.index.isin(te), "test", "unused"))
for t in targets:
    for mdl in B["multilabel"]:
        m = B["multilabel"][mdl].get(t) if isinstance(B["multilabel"][mdl], dict) \
            else None
        if m is None:
            continue
        try:
            P["%s__%s" % (mdl, t)] = m.predict_proba(X)[:, 1]
        except Exception as ex:
            print("    could not score %s / %s : %s" % (mdl, t, type(ex).__name__))
print("  split: %s" % dict(P.split.value_counts()))
sc = [c for c in P.columns if "__" in c]
print("  scored columns: %d" % len(sc))

head("3. DOES THE FAULT MODEL BEAT THE BASE RATE ON THE RECORDED FLAG?")

for t in targets:
    truth = D.set_index("Household_ID")[t].reindex(P.index)
    bal = truth.mean()
    print("\n  %s   base rate %.3f" % (t[:58], bal))
    for mdl in ["logistic", "random_forest", "hist_gbm"]:
        col = "%s__%s" % (mdl, t)
        if col not in P:
            continue
        line = "    %-14s" % mdl
        for split in ["train", "test"]:
            s = P[P.split == split]
            y = truth.reindex(s.index)
            ok = y.notna() & s[col].notna()
            a, lo, hi = auc_ci(s.loc[ok & (y == 1), col], s.loc[ok & (y == 0), col])
            line += "  %s AUC %.3f [%.3f,%.3f] n=%d/%d" % (
                split, a, lo, hi, int((ok & (y == 1)).sum()),
                int((ok & (y == 0)).sum()))
        print(line)
print("\n  TRAIN figures are IN-SAMPLE and optimistic - 89 of 119 households.")
print("  Only the TEST column is evidence, and n=30 makes it very wide.")

head("4. THE TEST THAT MATTERS - faults, or buildings?")

M = E.set_index("household_id")
P2 = P.join(M[["phys_deficiency_kwh_yr", "phys_status", "phys_era"]], how="left")
print("  For each target: does the model's score track the RECORDED FAULT, or")
print("  does it track the PHYSICAL EXCESS - i.e. is it finding misconfigured")
print("  controllers, or just old large buildings?\n")
print("  %-52s %10s %10s" % ("", "vs TRUTH", "vs EXCESS"))
rows = []
for t in targets:
    truth = D.set_index("Household_ID")[t].reindex(P2.index)
    col = "hist_gbm__%s" % t
    if col not in P2:
        continue
    ok = truth.notna() & P2[col].notna()
    a_truth = auc(P2.loc[ok & (truth == 1), col], P2.loc[ok & (truth == 0), col])
    s = P2[ok & P2.phys_deficiency_kwh_yr.notna()]
    rho = s[[col, "phys_deficiency_kwh_yr"]].corr(method="spearman").iloc[0, 1] \
        if len(s) > 4 else np.nan
    rows.append((t, a_truth, rho, len(s)))
    print("  %-52s %10.3f %10.3f" % (t[:52], a_truth, rho))
print("\n  (hist_gbm, all households pooled - train-inflated, shown for shape only)")
print("  A model finding FAULTS should track the truth and NOT the excess.")
print("  A model finding BUILDINGS tracks the excess as strongly as the truth.")

head("5. THE 2x2 - built on the RECORDED flag, not the prediction")

rec = D.set_index("Household_ID")[targets]
SETTING = [t for t in targets if "DHW_Storage" not in t]
print("  Setting faults used for axis A (DHW descaling excluded - it is not a")
print("  controller setting and is another project's):")
for t in SETTING:
    print("    %s" % t)
any_set = rec[SETTING].fillna(False).any(axis=1)
E2 = E.set_index("household_id").copy()
E2["setting_fault_flag"] = any_set.reindex(E2.index)
names = rec[SETTING].apply(
    lambda r: "; ".join([c.replace("HeatPump_", "").replace("_BeforeVisit", "")
                         for c in SETTING if r.get(c) == True]), axis=1)
E2["setting_fault_name"] = names.reindex(E2.index).replace("", np.nan)
E2["phys_excess_confirmed"] = E2.phys_excess_confirmed.astype("boolean")

sf = E2.setting_fault_flag.astype("boolean")
px = E2.phys_excess_confirmed
# np.select needs plain bool arrays; nullable booleans raise. Build the mask of
# rows where BOTH axes exist first, so a missing axis never becomes a category.
known = (sf.notna() & px.notna()).to_numpy(bool)
sfb, pxb = sf.fillna(False).to_numpy(bool), px.fillna(False).to_numpy(bool)
E2["combined_category"] = np.where(
    known,
    np.select([sfb & pxb, sfb & ~pxb, ~sfb & pxb, ~sfb & ~pxb],
              ["C", "A", "B", "D"], default=""), "")
E2["combined_category"] = E2.combined_category.replace("", np.nan)
both = E2.combined_category.notna()
print("\n  households where BOTH axes exist: %d of %d" % (int(both.sum()), len(E2)))
ct = pd.crosstab(sf[both], px[both])
print("\n  rows = setting fault recorded, cols = physical excess confirmed")
print(ct.to_string())
print("\n  %s" % dict(E2.combined_category.dropna().value_counts()))
print("    A  setting fault only      -> adjust the setting. Cheap, it sticks.")
print("    B  physical excess only    -> capital work")
print("    C  BOTH                    -> the hard one, see below")
print("    D  neither                 -> no finding on either axis")

head("6. CATEGORY C - compensating or compounding?")

C = E2[E2.combined_category == "C"].copy()
print("  %d households carry both a setting fault and a confirmed excess." % len(C))
print("  COMPENSATING: consumption sits near E_as_built - the house needs the")
print("                heat it is getting. Turning the curve down will not stick.")
print("  COMPOUNDING : consumption exceeds even E_as_built - deficient AND")
print("                over-heated. Fix the setting first, it is free.")
ds = pd.read_parquet(ROOT / "outputs/daily_states.parquet",
                     columns=["Household_ID", "date", "state_total", "kwh_total"])
ds = ds[ds.state_total.isin(["NORMAL", "MIXED_ZERO"]) & ds.kwh_total.notna()]
act = ds.groupby("Household_ID").kwh_total.mean() * 365
C["kwh_actual"] = act.reindex(C.index)
C["ratio_actual_vs_asbuilt"] = C.kwh_actual / C.phys_context_e_as_built_kwh_yr
C["c_state"] = np.where(C.ratio_actual_vs_asbuilt > 1.5, "compounding",
                        "compensating")
print("\n  %s" % dict(C.c_state.value_counts(dropna=False)))
print("  split at actual/E_as_built > 1.5, DECLARED AND ARBITRARY - E_as_built")
print("  excludes appliance electricity, so the ratio is above 1 for everyone and")
print("  no principled cut exists. See P4 section 3. This is a PLACEHOLDER.")

head("7. WRITE BACK INTO THE EXPORT")

E2 = E2.reset_index().rename(columns={"index": "household_id"})
E2["setting_fault_source"] = np.where(
    E2.setting_fault_flag.notna(), "protocol_record", "none")
E2.to_parquet(OUT / "data" / "p12_combined.parquet", index=False)
E2.to_csv(OUT / "data" / "p12_combined.csv", index=False, sep=";")
P.to_csv(OUT / "data" / "p12_fault_predictions.csv", sep=";")
print("  p12_combined.csv     - the export plus the fault axis and the 2x2")
print("  p12_fault_predictions.csv - model scores, with the train/test split")
print("\n  NOT written back into physical_baseline_v1 yet. The setting axis here")
print("  is the PROTOCOL RECORD, which exists only for audited households. Whether")
print("  the shipped export should carry the record, the model prediction, or both")
print("  is a decision, not a default.")
print("\nP12 complete.")
