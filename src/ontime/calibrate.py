"""Isotonic mapping fitted only on its reserved validation period."""
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


def reliability(y, p, bins=10):
    y, p = np.asarray(y), np.asarray(p)
    labels = np.minimum((np.clip(p, 0, 1)*bins).astype(int), bins-1)
    rows = []
    for i in range(bins):
        mask = labels == i
        n = int(mask.sum())
        rows.append({"bin": i, "lower": i/bins, "upper": (i+1)/bins, "orders": n,
                     "mean_prediction": float(p[mask].mean()) if n else np.nan,
                     "observed_rate": float(y[mask].mean()) if n else np.nan})
    return pd.DataFrame(rows)


def ece(y, p, bins=10):
    table = reliability(y, p, bins)
    return float(((table.mean_prediction-table.observed_rate).abs()*table.orders).sum()/len(y))


def fit_isotonic(y, p):
    return IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p, y)
