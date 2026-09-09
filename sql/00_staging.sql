-- Raw tables persist exact CSV text; every downstream column has explicit typing.
CREATE OR REPLACE TABLE parameters AS SELECT * FROM runtime_config;
CREATE OR REPLACE TABLE raw_orders AS SELECT * FROM read_csv('data/raw/olist_orders_dataset.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE raw_items AS SELECT * FROM read_csv('data/raw/olist_order_items_dataset.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE raw_payments AS SELECT * FROM read_csv('data/raw/olist_order_payments_dataset.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE raw_reviews AS SELECT * FROM read_csv('data/raw/olist_order_reviews_dataset.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE raw_customers AS SELECT * FROM read_csv('data/raw/olist_customers_dataset.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE raw_sellers AS SELECT * FROM read_csv('data/raw/olist_sellers_dataset.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE raw_products AS SELECT * FROM read_csv('data/raw/olist_products_dataset.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE raw_geolocation AS SELECT * FROM read_csv('data/raw/olist_geolocation_dataset.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE raw_translation AS SELECT * FROM read_csv('data/raw/product_category_name_translation.csv', header=true, all_varchar=true);

CREATE OR REPLACE VIEW stg_orders AS SELECT
    CAST(order_id AS VARCHAR) AS order_id, CAST(customer_id AS VARCHAR) AS customer_id,
    CAST(order_status AS VARCHAR) AS order_status,
    CAST(order_purchase_timestamp AS TIMESTAMP) AS purchase_ts,
    CAST(order_approved_at AS TIMESTAMP) AS approved_ts,
    CAST(order_delivered_carrier_date AS TIMESTAMP) AS carrier_ts,
    CAST(order_delivered_customer_date AS TIMESTAMP) AS delivery_ts,
    CAST(order_estimated_delivery_date AS TIMESTAMP) AS estimated_ts FROM raw_orders;
CREATE OR REPLACE VIEW stg_items AS SELECT
    CAST(order_id AS VARCHAR) AS order_id, CAST(order_item_id AS INTEGER) AS item_id,
    CAST(product_id AS VARCHAR) AS product_id, CAST(seller_id AS VARCHAR) AS seller_id,
    CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_ts,
    CAST(price AS DECIMAL(10,2)) AS price, CAST(freight_value AS DECIMAL(10,2)) AS freight
    FROM raw_items;
CREATE OR REPLACE VIEW stg_payments AS SELECT
    CAST(order_id AS VARCHAR) AS order_id, CAST(payment_sequential AS INTEGER) AS payment_sequence,
    CAST(payment_type AS VARCHAR) AS payment_type,
    CAST(payment_installments AS INTEGER) AS installments,
    CAST(payment_value AS DECIMAL(10,2)) AS payment_value FROM raw_payments;
CREATE OR REPLACE VIEW stg_reviews AS SELECT
    CAST(review_id AS VARCHAR) AS review_id, CAST(order_id AS VARCHAR) AS order_id,
    CAST(review_score AS INTEGER) AS review_score,
    CAST(review_comment_title AS VARCHAR) AS review_title,
    CAST(review_comment_message AS VARCHAR) AS review_message,
    CAST(review_creation_date AS TIMESTAMP) AS creation_ts,
    CAST(review_answer_timestamp AS TIMESTAMP) AS answer_ts FROM raw_reviews;
CREATE OR REPLACE VIEW stg_customers AS SELECT
    CAST(customer_id AS VARCHAR) AS customer_id, CAST(customer_unique_id AS VARCHAR) AS unique_customer_id,
    lpad(CAST(customer_zip_code_prefix AS VARCHAR), 5, '0') AS zip_prefix,
    CAST(customer_city AS VARCHAR) AS city, CAST(customer_state AS VARCHAR) AS state FROM raw_customers;
CREATE OR REPLACE VIEW stg_sellers AS SELECT
    CAST(seller_id AS VARCHAR) AS seller_id,
    lpad(CAST(seller_zip_code_prefix AS VARCHAR), 5, '0') AS zip_prefix,
    CAST(seller_city AS VARCHAR) AS city, CAST(seller_state AS VARCHAR) AS state FROM raw_sellers;
CREATE OR REPLACE VIEW stg_products AS SELECT
    CAST(product_id AS VARCHAR) AS product_id, CAST(product_category_name AS VARCHAR) AS category,
    CAST(product_name_lenght AS INTEGER) AS name_length,
    CAST(product_description_lenght AS INTEGER) AS description_length,
    CAST(product_photos_qty AS INTEGER) AS photos,
    CAST(product_weight_g AS DOUBLE) AS weight_g,
    CAST(product_length_cm AS DOUBLE) AS length_cm, CAST(product_height_cm AS DOUBLE) AS height_cm,
    CAST(product_width_cm AS DOUBLE) AS width_cm FROM raw_products;
CREATE OR REPLACE VIEW stg_geolocation AS SELECT
    lpad(CAST(geolocation_zip_code_prefix AS VARCHAR), 5, '0') AS zip_prefix,
    CAST(geolocation_lat AS DOUBLE) AS lat, CAST(geolocation_lng AS DOUBLE) AS lng,
    CAST(geolocation_city AS VARCHAR) AS city, CAST(geolocation_state AS VARCHAR) AS state FROM raw_geolocation;
CREATE OR REPLACE VIEW stg_translation AS SELECT
    CAST(product_category_name AS VARCHAR) AS category,
    CAST(product_category_name_english AS VARCHAR) AS category_english FROM raw_translation;

-- Broad Brazil bounding box rejects implausible coordinates, without silently
-- discarding their zip keys. All-invalid prefixes keep null centroids.
CREATE OR REPLACE TABLE geo_centroids AS SELECT zip_prefix,
    median(CASE WHEN lat BETWEEN -35 AND 6 AND lng BETWEEN -75 AND -30 THEN lat END)::DOUBLE AS lat,
    median(CASE WHEN lat BETWEEN -35 AND 6 AND lng BETWEEN -75 AND -30 THEN lng END)::DOUBLE AS lng,
    count(*)::BIGINT AS source_rows
FROM stg_geolocation GROUP BY zip_prefix;

CREATE OR REPLACE MACRO haversine_km(lat1, lng1, lat2, lng2) AS
    6371.0088 * 2 * asin(sqrt(least(1.0, greatest(0.0,
      sin(radians(lat2-lat1)/2)^2 + cos(radians(lat1))*cos(radians(lat2))*sin(radians(lng2-lng1)/2)^2))));
