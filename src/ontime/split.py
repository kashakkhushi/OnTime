"""Chronological cohorts and disjoint development subsets, with label maturity."""
import numpy as np
import pandas as pd
from . import config as c


def assign_splits(frame):
    frame = frame.sort_values(["at_purchase_timestamp", "at_order_id"], kind="stable").reset_index(drop=True)
    time = frame.at_purchase_timestamp
    frame["fold"] = np.select([time < pd.Timestamp(c.TRAIN_END), time < pd.Timestamp(c.VALIDATION_END)],
                              ["train", "validation"], default="test")
    return frame


def development_masks(frame):
    t, delivered = frame.at_purchase_timestamp, frame.post_delivery_date
    available = delivered < pd.Timestamp(c.VALIDATION_END)
    return {
        "train": (frame.fold == "train") & (delivered < pd.Timestamp(c.TRAIN_END)),
        "tune": (frame.fold == "validation") & (t < pd.Timestamp(c.CALIBRATION_START)) & available,
        "calibrate": (t >= pd.Timestamp(c.CALIBRATION_START)) & (t < pd.Timestamp(c.POLICY_START)) & available,
        "policy": (t >= pd.Timestamp(c.POLICY_START)) & (t < pd.Timestamp(c.POLICY_END)) & available,
        "test": frame.fold == "test",
    }


def split_report(frame):
    records = []
    for name in ("train", "validation", "test"):
        part = frame.loc[frame.fold == name]
        records.append({"fold": name, "orders": len(part), "late": int(part.is_late.sum()),
                        "late_rate": float(part.is_late.mean()), "start": str(part.at_purchase_timestamp.min()),
                        "end": str(part.at_purchase_timestamp.max())})
    return pd.DataFrame(records)
