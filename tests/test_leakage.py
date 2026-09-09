import numpy as np
import pandas as pd
import pytest
from ontime import config as c
from ontime.features import feature_frame, feature_columns, LEAKY
from ontime.split import development_masks


@pytest.mark.parametrize("kind", ["distance", "full", "mix"])
def test_only_checkout_features(frame, kind):
    X = feature_frame(frame.head(20), kind)
    assert all(name.startswith("at_") for name in X)
    assert not ({"is_late", "days_late", "at_order_id", "at_seller_id", "at_estimated_delivery_date"} & set(X))


def test_leaky_control_is_explicit(frame):
    assert set(LEAKY) <= set(feature_frame(frame.head(20), "leaky"))


def test_post_mutation_does_not_change_checkout_features(frame):
    original = frame.head(50).copy()
    changed = original.copy()
    changed["post_handling_days"] = 9999.0
    changed["post_review_score"] = 1
    changed["is_late"] = 1-original.is_late
    pd.testing.assert_frame_equal(feature_frame(original), feature_frame(changed))


@pytest.mark.parametrize("kind", ["seller", "route", "distance", "global"])
def test_asof_matches_brute_force(frame, kind):
    rng = np.random.default_rng(c.SEED)
    rows = frame.iloc[np.r_[0, rng.choice(len(frame), size=20, replace=False)]]
    keys = {"seller": "at_seller_id", "route": "at_route", "distance": "at_distance_band"}
    for row in rows.itertuples():
        prior = frame.loc[frame.post_delivery_date < row.at_purchase_timestamp]
        global_rate = prior.is_late.mean() if len(prior) else c.COLD_LATE_RATE
        global_handling = prior.post_handling_days.mean() if len(prior) else c.COLD_HANDLING_DAYS
        if kind == "global":
            assert row.at_global_history_count == len(prior)
            assert row.at_global_late_rate == pytest.approx(global_rate)
            assert row.at_global_handling_days == pytest.approx(global_handling)
            continue
        hist = prior.loc[prior[keys[kind]] == getattr(row, keys[kind])]
        expected = (hist.is_late.sum()+c.PRIOR_WEIGHT*global_rate)/(len(hist)+c.PRIOR_WEIGHT)
        assert getattr(row, f"at_{kind}_history_count") == len(hist)
        assert getattr(row, f"at_{kind}_late_rate") == pytest.approx(expected)
        if kind in ("seller", "route"):
            handling = (hist.post_handling_days.sum()+c.PRIOR_WEIGHT*global_handling)/(len(hist)+c.PRIOR_WEIGHT)
            assert getattr(row, f"at_{kind}_mean_handling_days") == pytest.approx(handling)


def test_chronological_nonoverlapping(frame):
    train, val, test = [frame.loc[frame.fold == label] for label in ("train", "validation", "test")]
    assert train.at_purchase_timestamp.max() < val.at_purchase_timestamp.min()
    assert val.at_purchase_timestamp.max() < test.at_purchase_timestamp.min()
    assert sum(map(len, (train,val,test))) == len(frame)
    assert frame.at_order_id.is_unique


def test_development_cohorts_are_disjoint(frame):
    masks = development_masks(frame)
    assert np.column_stack(list(masks.values())).sum(axis=1).max() == 1
    for key in ("tune", "calibrate", "policy"):
        assert (frame.loc[masks[key], "fold"] == "validation").all()
        assert (frame.loc[masks[key], "post_delivery_date"] < pd.Timestamp(c.VALIDATION_END)).all()
    assert (frame.loc[masks["train"], "post_delivery_date"] < pd.Timestamp(c.TRAIN_END)).all()


def test_no_history_cold_start(frame):
    row = frame.iloc[0]
    assert row.at_seller_history_count == 0 and row.at_seller_is_new == 1
    assert row.at_seller_late_rate == c.COLD_LATE_RATE


def test_sql_strict_asof_tie_and_future_exclusion():
    import duckdb
    with duckdb.connect() as connection:
        connection.execute((c.SQL / "tests" / "asof_toy.sql").read_text())
        result = connection.table("toy_result").df()
    assert result["n"].tolist() == [0, 2, 5]
