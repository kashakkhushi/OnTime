"""Indirect standardisation: descriptive association, not causal attribution."""
import numpy as np
import pandas as pd
from scipy.stats import chi2, poisson
from threadpoolctl import threadpool_limits
from . import config as c
from .features import feature_frame, encoder
from .models import logistic


def smr_interval(observed, expected, alpha=0.05):
    o, e = np.asarray(observed, dtype=float), np.asarray(expected, dtype=float)
    if np.any(e <= 0) or np.any(o < 0):
        raise ValueError("Expected counts must be positive and observed counts nonnegative")
    lower = np.where(o == 0, 0.0, chi2.ppf(alpha/2, 2*np.maximum(o, 1))/2/e)
    upper = chi2.ppf(1-alpha/2, 2*(o+1))/2/e
    return o/e, lower, upper


def bh_adjust(p_values):
    p = np.asarray(p_values)
    order = np.argsort(p, kind="stable")
    ranked = p[order]*len(p)/np.arange(1, len(p)+1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1].clip(0, 1)
    result = np.empty_like(adjusted)
    result[order] = adjusted
    return result


def expected_lateness(frame):
    """Five interleaved folds spanning the pooled period, ONLY for description.

    This is not the forecasting split. Sorting first and holding every fifth
    order out avoids own-outcome fitting without a random train/test split.
    No geography, seller identifier/history, promise, or post_* column is used.
    """
    frame = frame.sort_values(["at_purchase_timestamp", "at_order_id"], kind="stable")
    X, y = feature_frame(frame, "mix"), frame.is_late.to_numpy()
    fold = np.arange(len(frame)) % 5
    expected = np.empty(len(frame))
    with threadpool_limits(limits=1):
        for k in range(5):
            train, held = fold != k, fold == k
            enc = encoder("mix")
            model = logistic(C=1.0)
            model.fit(enc.fit_transform(X.loc[train]), y[train])
            expected[held] = model.predict_proba(enc.transform(X.loc[held]))[:, 1]
    return pd.DataFrame({"at_order_id": frame.at_order_id.to_numpy(), "expected_late": expected})


def standardise(con, frame):
    expected = expected_lateness(frame)
    con.register("expected_predictions", expected)
    con.execute((c.SQL / "50_segments.sql").read_text())
    result = con.table("segment_results").order("segment_type,segment").df()
    result["smr"], result["ci_lower"], result["ci_upper"] = smr_interval(result.observed, result.expected)
    result["excess_late_orders"] = result.observed-result.expected
    result["p_excess"] = poisson.sf(result.observed-1, result.expected)
    result["q_excess"] = np.nan
    result["seller_tail"] = False
    eligible = (result.segment_type == "seller") & (result.orders >= c.SELLER_MIN_ORDERS)
    result.loc[eligible, "q_excess"] = bh_adjust(result.loc[eligible, "p_excess"].to_numpy())
    result.loc[eligible, "seller_tail"] = (result.loc[eligible, "q_excess"] <= 0.05) & (result.loc[eligible, "ci_lower"] > 1)
    for kind in ("state", "seller", "route"):
        part = result.loc[result.segment_type == kind].sort_values(["smr", "segment"], ascending=[False, True])
        part.to_csv(c.TABLES / f"smr_{kind}.csv", index=False)
    tail = result.loc[result.seller_tail]
    totals = result.loc[result.segment_type == "seller"]
    summary = {"sellers": int(len(tail)), "eligible_sellers": int(eligible.sum()),
               "total_sellers": int(len(totals)), "orders": int(tail.orders.sum()),
               "order_share": float(tail.orders.sum()/len(frame)), "late": int(tail.observed.sum()),
               "raw_late_rate": float(tail.observed.sum()/tail.orders.sum()) if len(tail) else 0.0,
               "expected": float(tail.expected.sum()), "excess_late_orders": float(tail.excess_late_orders.sum()),
               "pooled_late_rate": float(frame.is_late.mean()),
               "smr": float(tail.observed.sum()/tail.expected.sum()) if len(tail) else 0.0}
    if len(tail):
        _, lo, hi = smr_interval(tail.observed.sum(), tail.expected.sum())
        summary.update(ci_lower=float(lo), ci_upper=float(hi))
    pd.DataFrame([summary]).to_csv(c.TABLES / "seller_tail_summary.csv", index=False)
    tail.sort_values("excess_late_orders", ascending=False).to_csv(c.TABLES / "seller_tail.csv", index=False)
    positive = totals.sort_values(["excess_late_orders", "segment"], ascending=[False, True]).copy()
    positive["positive_excess"] = positive.excess_late_orders.clip(lower=0)
    positive["seller_share"] = np.arange(1, len(positive)+1)/len(positive)
    positive["cumulative_positive_excess_share"] = positive.positive_excess.cumsum()/positive.positive_excess.sum()
    positive.to_csv(c.TABLES / "seller_pareto.csv", index=False)
    return result, summary
