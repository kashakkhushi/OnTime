"""Explicit checkout allowlist; identifiers and timestamps are never predictors.

The dump is not versioned. Product/seller/customer attributes, quoted freight,
promise, and the selected payment plan are assumed fixed and available at checkout.
Histories update on delivery events, including events inside validation and test.
"""
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATEGORICAL = ["at_month", "at_weekday", "at_customer_state", "at_customer_region", "at_seller_state",
               "at_category", "at_payment_type", "at_distance_band", "at_freight_class"]
NUMERIC = ["at_hour", "at_days_to_christmas", "at_brazil_holiday", "at_item_count", "at_distinct_sellers",
           "at_total_price", "at_total_freight", "at_freight_to_price", "at_max_weight_g", "at_max_volume_cm3",
           "at_installments", "at_distance_km", "at_geo_missing", "at_promise_days",
           "at_global_late_rate", "at_global_handling_days", "at_global_history_count",
           "at_seller_history_count", "at_seller_late_rate", "at_seller_mean_handling_days", "at_seller_is_new",
           "at_route_history_count", "at_route_late_rate", "at_route_mean_handling_days",
           "at_distance_history_count", "at_distance_late_rate"]
LEAKY = ["post_approval_days", "post_handling_days", "post_linehaul_days", "post_total_days", "post_review_score"]
MIX_CATEGORICAL = ["at_category", "at_distance_band", "at_freight_class", "at_month"]
MIX_NUMERIC = ["at_item_count"]


def feature_columns(kind="full"):
    if kind == "distance":
        return ["at_distance_band"], []
    if kind == "mix":
        return MIX_CATEGORICAL.copy(), MIX_NUMERIC.copy()
    if kind == "leaky":
        return CATEGORICAL.copy(), NUMERIC + LEAKY
    if kind != "full":
        raise ValueError(kind)
    return CATEGORICAL.copy(), NUMERIC.copy()


def feature_frame(frame, kind="full"):
    cats, nums = feature_columns(kind)
    result = frame[cats + nums].copy()
    if kind != "leaky" and any(not name.startswith("at_") for name in result.columns):
        raise ValueError("A post-checkout feature entered a legitimate matrix")
    for name in cats:
        result[name] = result[name].fillna("unknown").astype(str)
    for name in nums:
        result[name] = result[name].astype(float).replace([np.inf, -np.inf], np.nan)
    return result


def encoder(kind="full"):
    cats, nums = feature_columns(kind)
    transforms = [("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=True), cats)]
    if nums:
        transforms.append(("numeric", Pipeline([
            ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scale", StandardScaler()),
        ]), nums))
    return ColumnTransformer(transforms, sparse_threshold=1.0)


def haversine(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lng2-lng1)/2)**2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
