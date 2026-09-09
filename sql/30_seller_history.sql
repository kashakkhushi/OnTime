-- Collapse simultaneous delivery events BEFORE cumulative windows. Strict ASOF
-- inequality excludes all events at exactly the new order's purchase timestamp.
CREATE OR REPLACE TABLE global_events AS
WITH events AS (SELECT post_delivery_date AS event_ts,count(*) AS n,sum(is_late) AS late,sum(post_handling_days) AS handling
FROM order_fact GROUP BY event_ts)
SELECT event_ts,sum(n) OVER w AS n,sum(late) OVER w AS late,sum(handling) OVER w AS handling
FROM events WINDOW w AS(ORDER BY event_ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW);
CREATE OR REPLACE TABLE seller_events AS
WITH events AS (SELECT at_seller_id AS seller_id,post_delivery_date AS event_ts,count(*) AS n,sum(is_late) AS late,sum(post_handling_days) AS handling
FROM order_fact GROUP BY seller_id,event_ts)
SELECT seller_id,event_ts,sum(n) OVER w AS n,sum(late) OVER w AS late,sum(handling) OVER w AS handling
FROM events WINDOW w AS(PARTITION BY seller_id ORDER BY event_ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW);
CREATE OR REPLACE TABLE fact_seller_history AS
WITH global_prior AS (
SELECT o.*,
    coalesce(g.late/nullif(g.n,0),(SELECT cold_late_rate FROM parameters))::DOUBLE AS at_global_late_rate,
    coalesce(g.handling/nullif(g.n,0),(SELECT cold_handling_days FROM parameters))::DOUBLE AS at_global_handling_days,
    coalesce(g.n,0)::BIGINT AS at_global_history_count
FROM order_fact o ASOF LEFT JOIN global_events g ON o.at_purchase_timestamp>g.event_ts
)
SELECT o.*,coalesce(s.n,0)::BIGINT AS at_seller_history_count,
    ((coalesce(s.late,0)+p.prior_weight*o.at_global_late_rate)/(coalesce(s.n,0)+p.prior_weight))::DOUBLE AS at_seller_late_rate,
    ((coalesce(s.handling,0)+p.prior_weight*o.at_global_handling_days)/(coalesce(s.n,0)+p.prior_weight))::DOUBLE AS at_seller_mean_handling_days,
    (s.n IS NULL)::INTEGER AS at_seller_is_new
FROM global_prior o ASOF LEFT JOIN seller_events s ON o.at_seller_id=s.seller_id AND o.at_purchase_timestamp>s.event_ts
CROSS JOIN parameters p ORDER BY o.at_purchase_timestamp,o.at_order_id;
