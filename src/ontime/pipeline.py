"""Offline analysis orchestration; frozen JSON is independent of clock/paths."""
import json
import math
import platform
from importlib.metadata import version
import duckdb
import joblib
import numpy as np
import pandas as pd
from . import config as c
from .split import assign_splits, split_report
from .features import feature_columns
from .models import fit_ladder, score
from .calibrate import fit_isotonic, ece, reliability
from .standardise import standardise
from .decomposition import decompose
from .costmodel import evaluate_costs


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def canonical_json(metrics):
    return json.dumps(json_safe(metrics), indent=2, sort_keys=True, allow_nan=False) + "\n"


def run():
    c.ensure_dirs()
    with duckdb.connect(str(c.DB), config={"threads": 1}) as con:
        frame = assign_splits(con.table("model_fact").df())
        splits = split_report(frame)
        splits.to_csv(c.TABLES / "split_summary.csv", index=False)
        con.register("prediction_cohorts", frame[["at_order_id", "fold"]])
        con.execute((c.SQL / "70_target_audit.sql").read_text())
        target_audit = con.table("target_definition_sensitivity").df()
        target_audit.to_csv(c.TABLES / "target_definition_sensitivity.csv", index=False)
        print(splits.to_string(index=False), flush=True)
        ladder = fit_ladder(frame)
        masks, champion = ladder["masks"], ladder["champion"]
        development = []
        for name, mask in masks.items():
            part = frame.loc[mask]
            development.append({"subset": name, "orders": len(part), "late": int(part.is_late.sum()),
                                "late_rate": float(part.is_late.mean()),
                                "start": str(part.at_purchase_timestamp.min()), "end": str(part.at_purchase_timestamp.max())})
        pd.DataFrame(development).to_csv(c.TABLES / "development_subsets.csv", index=False)
        y = frame.is_late.to_numpy()
        p = ladder["predictions"][champion]
        iso = fit_isotonic(y[masks["calibrate"]], p[masks["calibrate"]])
        calibrated = iso.predict(p)
        test = masks["test"]
        calibration = []
        for label, probs in (("uncalibrated", p), ("isotonic", calibrated)):
            calibration.append({"calibration": label, "model": champion,
                                **score(y[test], probs[test]), "ece_10_bins": ece(y[test], probs[test])})
            reliability(y[test], probs[test]).to_csv(c.TABLES / f"reliability_{label}.csv", index=False)
        pd.DataFrame(calibration).to_csv(c.TABLES / "calibration.csv", index=False)
        ladder["ladder"].to_csv(c.TABLES / "model_ladder.csv", index=False)
        ladder["validation"].to_csv(c.TABLES / "model_validation.csv", index=False)
        exported = frame[["at_order_id", "at_purchase_timestamp", "fold", "is_late"]].copy()
        exported["champion_probability"] = p
        exported["isotonic_probability"] = calibrated
        exported.to_csv(c.OUTPUTS / ".cache" / "predictions.csv", index=False)
        print("Estimating mix-adjusted segments...", flush=True)
        segments, tail = standardise(con, frame)
        decomposition = decompose(con)
        costs = evaluate_costs(y[masks["policy"]], calibrated[masks["policy"]], y[test], calibrated[test])
        population = dict(con.table("population_audit").df().itertuples(index=False, name=None))
        feature_records = []
        for kind in ("distance", "full", "mix", "leaky"):
            cats, nums = feature_columns(kind)
            for column in cats + nums:
                feature_records.append({"matrix": kind, "column": column, "encoding": "one_hot" if column in cats else "median_and_scale"})
        pd.DataFrame(feature_records).to_csv(c.TABLES / "feature_inventory.csv", index=False)
        metrics = {"seed": c.SEED, "split_cutoffs": {"train_end": c.TRAIN_END, "validation_end": c.VALIDATION_END,
                    "calibration_start": c.CALIBRATION_START, "policy_start": c.POLICY_START, "policy_end": c.POLICY_END},
                   "population": population, "splits": splits.to_dict("records"), "development_subsets": development,
                   "target_definition_sensitivity": target_audit.to_dict("records"),
                   "model_ladder": ladder["ladder"].to_dict("records"), "model_validation": ladder["validation"].to_dict("records"),
                   "champion": champion, "champion_reason": ladder["reason"], "calibration": calibration,
                   "top_states": segments.loc[segments.segment_type == "state"].sort_values(["smr", "segment"], ascending=[False, True]).head(5).to_dict("records"),
                   "rio": segments.loc[(segments.segment_type == "state") & (segments.segment == "RJ")].iloc[0].to_dict(),
                   "seller_tail": tail, "decomposition": decomposition, "cost_model": costs,
                   "dq": con.table("dq_results").order("check_name").df().to_dict("records"),
                   "assumptions": {"prior_weight": c.PRIOR_WEIGHT, "cold_late_rate": c.COLD_LATE_RATE,
                       "cold_handling_days": c.COLD_HANDLING_DAYS, "seller_min_orders": c.SELLER_MIN_ORDERS,
                       "seller_fdr": 0.05, "smr_confidence": 0.95, "simplicity_ap_tolerance": c.SIMPLICITY_AP_TOLERANCE,
                       "min_policy_flagged": c.MIN_POLICY_FLAGGED, "figure_count": 8, "figure_dpi": 150,
                       "distance_boundary_km": 200},
                   "environment": {"python": platform.python_version(), **{name: version(name) for name in
                       ("duckdb", "pandas", "numpy", "scikit-learn", "lightgbm", "matplotlib", "scipy", "pytest")}}}
        (c.OUTPUTS / "metrics.json").write_text(canonical_json(metrics), encoding="utf-8", newline="\n")
        joblib.dump({"encoder": ladder["encoder"], "model": ladder["estimator"], "isotonic": iso}, c.OUTPUTS / ".cache" / "champion.joblib")
        print(f"Champion: {champion}; test AP {calibration[0]['pr_auc']:.4f}; cost net/order {costs['net_per_order']:.4f}", flush=True)
    return json_safe(metrics)


if __name__ == "__main__":
    run()
