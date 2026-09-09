-- Expected probabilities come from the pooled, cross-fitted MIX-ONLY model.
-- Every order is counted once. Seller/route attribution uses dominant checkout
-- seller by merchandise value, deterministic ID tie-break (not all item sellers).
CREATE OR REPLACE TABLE order_expected AS
SELECT o.*,p.expected_late::DOUBLE AS expected_late
FROM order_fact o JOIN expected_predictions p ON o.at_order_id=p.at_order_id;
CREATE OR REPLACE TABLE segment_results AS
SELECT 'state' AS segment_type,at_customer_state AS segment,count(*)::BIGINT AS orders,
    sum(is_late)::BIGINT AS observed,sum(expected_late)::DOUBLE AS expected,avg(is_late)::DOUBLE AS raw_late_rate
FROM order_expected GROUP BY at_customer_state
UNION ALL
SELECT 'seller',at_seller_id,count(*),sum(is_late),sum(expected_late),avg(is_late)
FROM order_expected GROUP BY at_seller_id
UNION ALL
SELECT 'route',at_route,count(*),sum(is_late),sum(expected_late),avg(is_late)
FROM order_expected GROUP BY at_route;
