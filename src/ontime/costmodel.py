"""Economic scenarios in BRL. No efficacy or customer lifetime value is identified.

Expected net per incoming order = flagged_fraction * (e * V * precision - C).
Thresholds are chosen on the policy validation subset, then frozen for test.
Sensitivity cells repeat this protocol; test is never used to choose a threshold.
"""
from itertools import product
import numpy as np
import pandas as pd
from scipy.stats import beta
from . import config as c


def break_even_effectiveness(cost, value, precision):
    if cost < 0 or value <= 0 or not 0 <= precision <= 1:
        raise ValueError("Invalid economic inputs")
    return float(cost/(value*precision)) if precision > 0 else float("inf")


def economic_value(y, p, threshold, cost, value, effectiveness):
    y, p = np.asarray(y), np.asarray(p)
    selected = p >= threshold
    n, late = int(selected.sum()), int(y[selected].sum())
    precision = late/n if n else 0.0
    return {"threshold": float(threshold), "orders": len(y), "flagged": n, "late_flagged": late,
            "flag_rate": n/len(y), "precision": precision,
            "mean_probability_flagged": float(p[selected].mean()) if n else 0.0,
            "net_per_order": float((effectiveness*value*late-cost*n)/len(y)),
            "predicted_net_per_order": float((effectiveness*value*p[selected].sum()-cost*n)/len(y)),
            "expected_saved": float(effectiveness*late),
            "break_even_effectiveness": break_even_effectiveness(cost, value, precision)}


def threshold_sweep(y, p, cost, value, effectiveness):
    rows = [economic_value(y, p, t, cost, value, effectiveness) for t in c.THRESHOLDS]
    rows.append(economic_value(y, p, 1.01, cost, value, effectiveness))  # no-intervention option
    return pd.DataFrame(rows)


def choose_threshold(table, min_flagged=c.MIN_POLICY_FLAGGED):
    eligible = table.loc[table.flagged >= min_flagged]
    if eligible.empty:
        raise ValueError("Insufficient policy sample to choose an intervention threshold")
    return eligible.sort_values(["net_per_order", "threshold"], ascending=[False, False]).iloc[0]


def sensitivity_grid(y_policy, p_policy, y_test, p_test):
    rows = []
    for cost, value, eff in product(c.COST_GRID, c.VALUE_GRID, c.EFFECTIVENESS_GRID):
        sweep = threshold_sweep(y_policy, p_policy, cost, value, eff)
        candidate = choose_threshold(sweep)
        enabled = candidate.net_per_order > 0
        threshold = float(candidate.threshold) if enabled else 1.01
        result = economic_value(y_test, p_test, threshold, cost, value, eff)
        rows.append({"cost_brl": cost, "value_brl": value, "effectiveness": eff,
                     "validation_enabled": bool(enabled), "validation_candidate_net": float(candidate.net_per_order),
                     **result, "net_positive": bool(result["net_per_order"] > 0)})
    return pd.DataFrame(rows)


def evaluate_costs(y_policy, p_policy, y_test, p_test):
    sweep = threshold_sweep(y_policy, p_policy, c.INTERVENTION_COST, c.PREVENTED_LATE_VALUE, c.EFFECTIVENESS)
    candidate = choose_threshold(sweep)
    threshold = float(candidate.threshold)
    test = economic_value(y_test, p_test, threshold, c.INTERVENTION_COST, c.PREVENTED_LATE_VALUE, c.EFFECTIVENESS)
    predicted_be = break_even_effectiveness(c.INTERVENTION_COST, c.PREVENTED_LATE_VALUE, test["mean_probability_flagged"])
    enabled = bool(candidate.net_per_order > 0)
    grid = sensitivity_grid(y_policy, p_policy, y_test, p_test)
    # Exact binomial precision interval, conditional on frozen flagged set;
    # excludes uncertainty about intervention effectiveness/value/cost and clustering.
    n, k = test["flagged"], test["late_flagged"]
    lower = float(beta.ppf(0.025, k, n-k+1)) if k else 0.0
    upper = float(beta.ppf(0.975, k+1, n-k)) if k < n else 1.0
    summary = {**test, "validation_candidate_net": float(candidate.net_per_order),
               "validation_enabled": enabled, "deployed_policy_net_per_order": test["net_per_order"] if enabled else 0.0,
               "precision_ci_lower": lower, "precision_ci_upper": upper,
               "break_even_lower": break_even_effectiveness(c.INTERVENTION_COST, c.PREVENTED_LATE_VALUE, upper),
               "break_even_upper": break_even_effectiveness(c.INTERVENTION_COST, c.PREVENTED_LATE_VALUE, lower),
               "predicted_break_even_effectiveness": predicted_be,
               "net_positive_cells": int(grid.net_positive.sum()), "sensitivity_cells": int(len(grid)),
               "cost_brl": c.INTERVENTION_COST, "value_brl": c.PREVENTED_LATE_VALUE, "effectiveness": c.EFFECTIVENESS}
    sweep.to_csv(c.TABLES / "threshold_sweep_validation.csv", index=False)
    # Test sweep is descriptive only; this never feeds selection or the decision.
    threshold_sweep(y_test, p_test, c.INTERVENTION_COST, c.PREVENTED_LATE_VALUE, c.EFFECTIVENESS).to_csv(
        c.TABLES / "threshold_sweep_test_diagnostic.csv", index=False)
    grid.to_csv(c.TABLES / "cost_sensitivity.csv", index=False)
    pd.DataFrame([summary]).to_csv(c.TABLES / "cost_summary.csv", index=False)
    return summary
