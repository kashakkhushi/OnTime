# Data-quality report

Counts refer to staging records, before filters.
FAIL is a recorded data finding, not an ignored pipeline error.

| Assertion | Violations | Result |
|---|---:|---|
| 01_orders_pk | 0 | PASS |
| 02_items_composite_pk | 0 | PASS |
| 03_payments_composite_pk | 0 | PASS |
| 04_reviews_candidate_pk | 814 | FAIL |
| 05_customers_pk | 0 | PASS |
| 06_sellers_pk | 0 | PASS |
| 07_products_pk | 0 | PASS |
| 08_geolocation_zip_candidate_pk | 981,148 | FAIL |
| 09_translation_pk | 0 | PASS |
| 10_order_customer_fk | 0 | PASS |
| 11_item_product_fk | 0 | PASS |
| 12_item_seller_fk | 0 | PASS |
| 13_purchase_before_approval | 0 | PASS |
| 14_approval_before_carrier | 1,359 | FAIL |
| 15_carrier_before_customer | 23 | FAIL |
| 16_checkout_identifiers_nonnull | 0 | PASS |
| 17_delivered_timestamps_complete | 23 | FAIL |
| 18_freight_nonnegative | 0 | PASS |
| 19_price_positive | 0 | PASS |
| 20_weight_positive | 6 | FAIL |
| 21_dimensions_positive | 2 | FAIL |
| 22_category_translation_coverage | 623 | FAIL |
| 23_customer_zip_coverage | 280 | FAIL |
| 24_seller_zip_coverage | 8 | FAIL |
| 25_duplicate_item_lines | 0 | PASS |
| 26_delivered_without_delivery | 8 | FAIL |
| 27_delivery_without_delivered | 6 | FAIL |
| 28_order_has_items_and_payment | 776 | FAIL |

## Resolution policy

Geolocation is many observations per zip, not a unique-zip dimension: median valid coordinates collapse it.
Reviews are not keyed uniquely by review_id: choose latest answer per order with deterministic ties.
Delivered/complete/monotone and valid item linkage filters are counted in outputs/tables/exclusions.csv.
Missing/invalid weights and dimensions become null plus imputation indicators; missing categories and coordinates retain explicit unknown groups.
Missing payments become unknown; payments never multiply order rows. Price/freight violations exclude affected orders.
Duplicate item lines are removed before item aggregation; inconsistent duplicate keys would fail the uniqueness test.
