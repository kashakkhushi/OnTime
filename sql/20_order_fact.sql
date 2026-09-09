-- Never join raw one-to-many tables straight into an order fact.
CREATE OR REPLACE TABLE clean_items AS SELECT DISTINCT * FROM stg_items;
CREATE OR REPLACE TABLE item_rollup AS
WITH seller_totals AS (
    SELECT order_id, seller_id, sum(price) AS seller_price FROM clean_items GROUP BY order_id,seller_id
), dominant_seller AS (
    SELECT order_id, seller_id FROM seller_totals
    QUALIFY row_number() OVER(PARTITION BY order_id ORDER BY seller_price DESC,seller_id)=1
), dominant_category AS (
    SELECT i.order_id, coalesce(t.category_english,p.category,'unknown') AS category, sum(i.price) AS category_price
    FROM clean_items i LEFT JOIN stg_products p USING(product_id) LEFT JOIN stg_translation t ON p.category=t.category
    GROUP BY i.order_id, coalesce(t.category_english,p.category,'unknown')
    QUALIFY row_number() OVER(PARTITION BY i.order_id ORDER BY category_price DESC,coalesce(t.category_english,p.category,'unknown'))=1
)
SELECT i.order_id, d.seller_id, dc.category, count(*)::INTEGER AS item_count,
    count(DISTINCT i.seller_id)::INTEGER AS seller_count,
    sum(i.price)::DECIMAL(18,2) AS total_price, sum(i.freight)::DECIMAL(18,2) AS total_freight,
    max(CASE WHEN p.weight_g > 0 THEN p.weight_g END)::DOUBLE AS max_weight_g,
    max(CASE WHEN p.length_cm>0 AND p.height_cm>0 AND p.width_cm>0
        THEN p.length_cm*p.height_cm*p.width_cm END)::DOUBLE AS max_volume_cm3,
    count(*) FILTER(WHERE p.product_id IS NULL OR s.seller_id IS NULL OR i.price<=0 OR i.freight<0 OR i.price IS NULL OR i.freight IS NULL)::INTEGER AS bad_items
FROM clean_items i LEFT JOIN stg_products p USING(product_id) LEFT JOIN stg_sellers s USING(seller_id)
JOIN dominant_seller d ON i.order_id=d.order_id JOIN dominant_category dc ON i.order_id=dc.order_id
GROUP BY i.order_id,d.seller_id,dc.category;

CREATE OR REPLACE TABLE payment_rollup AS
SELECT order_id, payment_type, installments FROM stg_payments
QUALIFY row_number() OVER(PARTITION BY order_id ORDER BY payment_value DESC,payment_sequence,payment_type,installments)=1;
CREATE OR REPLACE TABLE review_rollup AS
SELECT order_id, review_score FROM stg_reviews
QUALIFY row_number() OVER(PARTITION BY order_id ORDER BY answer_ts DESC NULLS LAST,creation_ts DESC NULLS LAST,review_id DESC,review_score DESC)=1;

CREATE OR REPLACE TABLE eligibility AS
SELECT o.*,
    CASE WHEN o.order_status<>'delivered' THEN 1
         WHEN purchase_ts IS NULL OR approved_ts IS NULL OR carrier_ts IS NULL OR delivery_ts IS NULL OR estimated_ts IS NULL THEN 2
         WHEN NOT(purchase_ts<=approved_ts AND approved_ts<=carrier_ts AND carrier_ts<=delivery_ts AND purchase_ts<=estimated_ts) THEN 3
         WHEN c.customer_id IS NULL OR c.state IS NULL OR i.order_id IS NULL OR i.bad_items>0 THEN 4
         ELSE 5 END::INTEGER AS first_failed_step
FROM stg_orders o LEFT JOIN stg_customers c USING(customer_id) LEFT JOIN item_rollup i USING(order_id);

CREATE OR REPLACE TABLE exclusions AS
WITH steps AS (
    SELECT * FROM (VALUES (0,'loaded orders'),(1,'delivered status'),(2,'complete timestamps'),
                         (3,'monotone timestamps and valid promise'),(4,'customer and valid items')) s(step,filter)
), counts AS (
    SELECT step,filter,(SELECT count(*) FROM eligibility WHERE first_failed_step>step)::BIGINT AS retained FROM steps
)
SELECT step,filter,retained,coalesce(lag(retained) OVER(ORDER BY step)-retained,0)::BIGINT AS excluded_at_step FROM counts ORDER BY step;

CREATE OR REPLACE TABLE order_fact AS
WITH assembled AS (
SELECT o.order_id AS at_order_id, o.purchase_ts AS at_purchase_timestamp,
    o.estimated_ts AS at_estimated_delivery_date,
    date_part('month',o.purchase_ts)::INTEGER AS at_month,
    date_part('dow',o.purchase_ts)::INTEGER AS at_weekday,
    date_part('hour',o.purchase_ts)::INTEGER AS at_hour,
    date_diff('day',CAST(o.purchase_ts AS DATE),
        CASE WHEN strftime(o.purchase_ts,'%m-%d')<='12-25' THEN make_date(year(o.purchase_ts)::INTEGER,12,25)
             ELSE make_date(year(o.purchase_ts)::INTEGER+1,12,25) END)::INTEGER AS at_days_to_christmas,
    -- Federal fixed-date holidays applicable in 2016–2018; optional/local holidays excluded.
    (strftime(o.purchase_ts,'%m-%d') IN ('01-01','04-21','05-01','09-07','10-12','11-02','11-15','12-25'))::INTEGER AS at_brazil_holiday,
    c.state AS at_customer_state,
    CASE WHEN c.state IN ('SP','RJ','MG','ES') THEN 'Southeast'
         WHEN c.state IN ('PR','SC','RS') THEN 'South'
         WHEN c.state IN ('DF','GO','MT','MS') THEN 'Central-West'
         WHEN c.state IN ('AC','AM','AP','PA','RO','RR','TO') THEN 'North' ELSE 'Northeast' END::VARCHAR AS at_customer_region,
    i.seller_id AS at_seller_id, s.state AS at_seller_state,
    s.state || '->' || c.state AS at_route,
    i.item_count AS at_item_count, i.seller_count AS at_distinct_sellers,
    i.total_price AS at_total_price, i.total_freight AS at_total_freight,
    (i.total_freight/nullif(i.total_price,0))::DOUBLE AS at_freight_to_price,
    CASE WHEN i.total_freight<=15 THEN '01_low_0_15' WHEN i.total_freight<=30 THEN '02_mid_15_30' ELSE '03_high_30_plus' END::VARCHAR AS at_freight_class,
    i.max_weight_g AS at_max_weight_g, i.max_volume_cm3 AS at_max_volume_cm3, i.category AS at_category,
    coalesce(p.payment_type,'unknown') AS at_payment_type, p.installments AS at_installments,
    CASE WHEN sg.lat IS NULL OR cg.lat IS NULL THEN NULL ELSE haversine_km(sg.lat,sg.lng,cg.lat,cg.lng) END::DOUBLE AS at_distance_km,
    (sg.lat IS NULL OR cg.lat IS NULL)::INTEGER AS at_geo_missing,
    (epoch(o.estimated_ts-o.purchase_ts)/86400)::DOUBLE AS at_promise_days,
    (epoch(o.approved_ts-o.purchase_ts)/86400)::DOUBLE AS post_approval_days,
    (epoch(o.carrier_ts-o.purchase_ts)/86400)::DOUBLE AS post_handling_days,
    (epoch(o.delivery_ts-o.carrier_ts)/86400)::DOUBLE AS post_linehaul_days,
    (epoch(o.delivery_ts-o.purchase_ts)/86400)::DOUBLE AS post_total_days,
    o.approved_ts AS post_approved_timestamp, o.carrier_ts AS post_carrier_timestamp,
    o.delivery_ts AS post_delivery_date, r.review_score AS post_review_score,
    (o.delivery_ts>o.estimated_ts)::INTEGER AS is_late,
    greatest(0,epoch(o.delivery_ts-o.estimated_ts)/86400)::DOUBLE AS days_late
FROM eligibility o JOIN stg_customers c USING(customer_id) JOIN item_rollup i USING(order_id)
JOIN stg_sellers s ON i.seller_id=s.seller_id
LEFT JOIN geo_centroids cg ON c.zip_prefix=cg.zip_prefix LEFT JOIN geo_centroids sg ON s.zip_prefix=sg.zip_prefix
LEFT JOIN payment_rollup p USING(order_id) LEFT JOIN review_rollup r USING(order_id)
WHERE o.first_failed_step=5
)
SELECT *, CASE WHEN at_distance_km IS NULL THEN '00_unknown' WHEN at_distance_km<=200 THEN '01_0_200'
    WHEN at_distance_km<=500 THEN '02_200_500' WHEN at_distance_km<=1000 THEN '03_500_1000'
    WHEN at_distance_km<=2000 THEN '04_1000_2000' ELSE '05_2000_plus' END::VARCHAR AS at_distance_band
FROM assembled ORDER BY at_purchase_timestamp,at_order_id;

CREATE OR REPLACE TABLE population_audit AS
SELECT 'raw_geolocation_rows' AS statistic,count(*)::DOUBLE AS value FROM stg_geolocation
UNION ALL SELECT 'distinct_zip_prefixes',count(*) FROM geo_centroids
UNION ALL SELECT 'invalid_geolocation_rows',count(*) FROM stg_geolocation WHERE NOT(lat BETWEEN -35 AND 6 AND lng BETWEEN -75 AND -30) OR lat IS NULL OR lng IS NULL
UNION ALL SELECT 'multiseller_orders',count(*) FROM order_fact WHERE at_distinct_sellers>1
UNION ALL SELECT 'multiitem_orders',count(*) FROM order_fact WHERE at_item_count>1
UNION ALL SELECT 'unknown_distance_orders',count(*) FROM order_fact WHERE at_geo_missing=1
UNION ALL SELECT 'missing_review_orders',count(*) FROM order_fact WHERE post_review_score IS NULL
UNION ALL SELECT 'multiple_review_orders',count(*) FROM (SELECT order_id FROM stg_reviews GROUP BY order_id HAVING count(*)>1)
UNION ALL SELECT 'orders',count(*) FROM order_fact
UNION ALL SELECT 'late_orders',sum(is_late) FROM order_fact
UNION ALL SELECT 'late_rate',avg(is_late) FROM order_fact
UNION ALL SELECT 'min_purchase_year',min(year(at_purchase_timestamp)) FROM order_fact
UNION ALL SELECT 'max_purchase_year',max(year(at_purchase_timestamp)) FROM order_fact;
CREATE OR REPLACE TABLE monthly_rates AS
SELECT date_trunc('month',at_purchase_timestamp)::DATE AS month,count(*)::BIGINT AS orders,sum(is_late)::BIGINT AS late,avg(is_late)::DOUBLE AS late_rate
FROM order_fact GROUP BY month ORDER BY month;
CREATE OR REPLACE TABLE review_distribution AS
SELECT is_late,coalesce(post_review_score,0)::INTEGER AS review_score,count(*)::BIGINT AS orders,
    count(*)::DOUBLE/sum(count(*)) OVER(PARTITION BY is_late) AS share_all
FROM order_fact GROUP BY is_late,coalesce(post_review_score,0) ORDER BY is_late,review_score;
