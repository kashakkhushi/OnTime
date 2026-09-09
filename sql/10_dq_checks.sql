-- Exactly 28 named assertions; count affected records or excess duplicate keys.
CREATE OR REPLACE TABLE dq_results AS
SELECT '01_orders_pk' AS check_name, (count(*)-count(DISTINCT order_id))::BIGINT AS violations FROM stg_orders
UNION ALL SELECT '02_items_composite_pk', count(*)-count(DISTINCT (order_id,item_id)) FROM stg_items
UNION ALL SELECT '03_payments_composite_pk', count(*)-count(DISTINCT (order_id,payment_sequence)) FROM stg_payments
UNION ALL SELECT '04_reviews_candidate_pk', count(*)-count(DISTINCT review_id) FROM stg_reviews
UNION ALL SELECT '05_customers_pk', count(*)-count(DISTINCT customer_id) FROM stg_customers
UNION ALL SELECT '06_sellers_pk', count(*)-count(DISTINCT seller_id) FROM stg_sellers
UNION ALL SELECT '07_products_pk', count(*)-count(DISTINCT product_id) FROM stg_products
UNION ALL SELECT '08_geolocation_zip_candidate_pk', count(*)-count(DISTINCT zip_prefix) FROM stg_geolocation
UNION ALL SELECT '09_translation_pk', count(*)-count(DISTINCT category) FROM stg_translation
UNION ALL SELECT '10_order_customer_fk', count(*) FROM stg_orders o LEFT JOIN stg_customers c USING(customer_id) WHERE c.customer_id IS NULL
UNION ALL SELECT '11_item_product_fk', count(*) FROM stg_items i LEFT JOIN stg_products p USING(product_id) WHERE p.product_id IS NULL
UNION ALL SELECT '12_item_seller_fk', count(*) FROM stg_items i LEFT JOIN stg_sellers s USING(seller_id) WHERE s.seller_id IS NULL
UNION ALL SELECT '13_purchase_before_approval', count(*) FROM stg_orders WHERE purchase_ts > approved_ts
UNION ALL SELECT '14_approval_before_carrier', count(*) FROM stg_orders WHERE approved_ts > carrier_ts
UNION ALL SELECT '15_carrier_before_customer', count(*) FROM stg_orders WHERE carrier_ts > delivery_ts
UNION ALL SELECT '16_checkout_identifiers_nonnull', count(*) FROM stg_orders o LEFT JOIN stg_customers c USING(customer_id) WHERE o.order_id IS NULL OR o.customer_id IS NULL OR purchase_ts IS NULL OR estimated_ts IS NULL OR c.state IS NULL
UNION ALL SELECT '17_delivered_timestamps_complete', count(*) FROM stg_orders WHERE order_status='delivered' AND (purchase_ts IS NULL OR approved_ts IS NULL OR carrier_ts IS NULL OR delivery_ts IS NULL OR estimated_ts IS NULL)
UNION ALL SELECT '18_freight_nonnegative', count(*) FROM stg_items WHERE freight < 0 OR freight IS NULL
UNION ALL SELECT '19_price_positive', count(*) FROM stg_items WHERE price <= 0 OR price IS NULL
UNION ALL SELECT '20_weight_positive', count(*) FROM stg_products WHERE weight_g <= 0 OR weight_g IS NULL
UNION ALL SELECT '21_dimensions_positive', count(*) FROM stg_products WHERE length_cm <= 0 OR height_cm <= 0 OR width_cm <= 0 OR length_cm IS NULL OR height_cm IS NULL OR width_cm IS NULL
UNION ALL SELECT '22_category_translation_coverage', count(*) FROM stg_products p LEFT JOIN stg_translation t USING(category) WHERE t.category IS NULL
UNION ALL SELECT '23_customer_zip_coverage', count(*) FROM stg_customers c LEFT JOIN geo_centroids g USING(zip_prefix) WHERE g.lat IS NULL OR g.lng IS NULL
UNION ALL SELECT '24_seller_zip_coverage', count(*) FROM stg_sellers s LEFT JOIN geo_centroids g USING(zip_prefix) WHERE g.lat IS NULL OR g.lng IS NULL
UNION ALL SELECT '25_duplicate_item_lines', count(*)-count(DISTINCT (order_id,item_id,product_id,seller_id,shipping_limit_ts,price,freight)) FROM stg_items
UNION ALL SELECT '26_delivered_without_delivery', count(*) FROM stg_orders WHERE order_status='delivered' AND delivery_ts IS NULL
UNION ALL SELECT '27_delivery_without_delivered', count(*) FROM stg_orders WHERE order_status<>'delivered' AND delivery_ts IS NOT NULL
UNION ALL SELECT '28_order_has_items_and_payment', count(*) FROM stg_orders o WHERE NOT EXISTS (SELECT 1 FROM stg_items i WHERE i.order_id=o.order_id) OR NOT EXISTS (SELECT 1 FROM stg_payments p WHERE p.order_id=o.order_id);
