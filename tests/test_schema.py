import pandas as pd
import pytest
from ontime import config as c
from ontime.features import CATEGORICAL, NUMERIC


@pytest.mark.parametrize("table,column,dtype", [
    ("stg_orders","purchase_ts","TIMESTAMP"),("stg_orders","order_id","VARCHAR"),
    ("stg_items","price","DECIMAL(10,2)"),("stg_items","freight","DECIMAL(10,2)"),
    ("stg_payments","payment_value","DECIMAL(10,2)"),("stg_products","weight_g","DOUBLE"),
    ("stg_reviews","answer_ts","TIMESTAMP"),("stg_customers","zip_prefix","VARCHAR"),
    ("model_fact","at_seller_history_count","BIGINT"),("model_fact","is_late","INTEGER"),
    ("model_fact","post_delivery_date","TIMESTAMP"),("model_fact","at_distance_km","DOUBLE"),
])
def test_expected_dtype(con, table, column, dtype):
    rel = con.table(table)
    assert str(rel.types[rel.columns.index(column)]) == dtype


def test_all_features_exist(frame):
    assert set(CATEGORICAL+NUMERIC) <= set(frame.columns)


def test_prefix_contract(con):
    assert all(col.startswith(("at_", "post_")) or col in ("is_late", "days_late") for col in con.table("order_fact").columns)


def test_exclusion_ladder_accounts_for_every_order(frame, metrics):
    ex = pd.read_csv(c.TABLES / "exclusions.csv")
    assert ex.retained.iloc[-1] == len(frame) == metrics["population"]["orders"]
    assert ex.excluded_at_step.sum()+len(frame) == ex.retained.iloc[0]
    assert (ex.retained.diff().dropna() <= 0).all()


def test_fact_preserves_one_order_grain(con, frame):
    assert frame.at_order_id.is_unique
    assert len(frame) == len(con.table("order_fact").df())


def test_geolocation_reduction(con):
    geo = con.table("geo_centroids").df()
    raw = con.table("stg_geolocation").df()
    assert geo.zip_prefix.is_unique
    assert geo.source_rows.sum() == len(raw)
    chosen = geo.loc[geo.source_rows > 10].iloc[0]
    rows = raw.loc[(raw.zip_prefix == chosen.zip_prefix) & raw.lat.between(-35,6) & raw.lng.between(-75,-30)]
    assert chosen.lat == pytest.approx(rows.lat.median())
    assert chosen.lng == pytest.approx(rows.lng.median())


def test_population_timestamps_and_target(frame):
    assert (frame.at_purchase_timestamp <= frame.post_approved_timestamp).all()
    assert (frame.post_approved_timestamp <= frame.post_carrier_timestamp).all()
    assert (frame.post_carrier_timestamp <= frame.post_delivery_date).all()
    assert ((frame.post_delivery_date > frame.at_estimated_delivery_date).astype(int) == frame.is_late).all()


def test_missing_geo_is_explicit(frame):
    assert (frame.at_distance_km.isna() == frame.at_geo_missing.astype(bool)).all()
    assert (frame.loc[frame.at_geo_missing == 1, "at_distance_band"] == "00_unknown").all()


def test_multiseller_orders_are_retained(frame, metrics):
    assert (frame.at_distinct_sellers > 1).sum() == metrics["population"]["multiseller_orders"] > 0


def test_dq_has_28_named_results(con):
    report = con.table("dq_results").df()
    assert len(report) == 28 and report.check_name.is_unique
    assert (report.violations >= 0).all()
    text = (c.DATA / "dq_report.md").read_text()
    assert all(name in text for name in report.check_name)


def test_review_rollup_does_not_duplicate_orders(con):
    reviews = con.table("review_rollup").df()
    assert reviews.order_id.is_unique
    assert reviews.review_score.dropna().between(1,5).all()
