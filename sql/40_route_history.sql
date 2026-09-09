CREATE OR REPLACE TABLE route_events AS
WITH events AS (SELECT at_route AS route,post_delivery_date AS event_ts,count(*) AS n,sum(is_late) AS late,sum(post_handling_days) AS handling
FROM order_fact GROUP BY route,event_ts)
SELECT route,event_ts,sum(n) OVER w AS n,sum(late) OVER w AS late,sum(handling) OVER w AS handling
FROM events WINDOW w AS(PARTITION BY route ORDER BY event_ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW);
CREATE OR REPLACE TABLE distance_events AS
WITH events AS (SELECT at_distance_band AS band,post_delivery_date AS event_ts,count(*) AS n,sum(is_late) AS late
FROM order_fact GROUP BY band,event_ts)
SELECT band,event_ts,sum(n) OVER w AS n,sum(late) OVER w AS late
FROM events WINDOW w AS(PARTITION BY band ORDER BY event_ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW);
CREATE OR REPLACE TABLE model_fact AS
SELECT o.*,coalesce(r.n,0)::BIGINT AS at_route_history_count,
    ((coalesce(r.late,0)+p.prior_weight*o.at_global_late_rate)/(coalesce(r.n,0)+p.prior_weight))::DOUBLE AS at_route_late_rate,
    ((coalesce(r.handling,0)+p.prior_weight*o.at_global_handling_days)/(coalesce(r.n,0)+p.prior_weight))::DOUBLE AS at_route_mean_handling_days,
    coalesce(d.n,0)::BIGINT AS at_distance_history_count,
    ((coalesce(d.late,0)+p.prior_weight*o.at_global_late_rate)/(coalesce(d.n,0)+p.prior_weight))::DOUBLE AS at_distance_late_rate
FROM fact_seller_history o
ASOF LEFT JOIN route_events r ON o.at_route=r.route AND o.at_purchase_timestamp>r.event_ts
ASOF LEFT JOIN distance_events d ON o.at_distance_band=d.band AND o.at_purchase_timestamp>d.event_ts
CROSS JOIN parameters p ORDER BY o.at_purchase_timestamp,o.at_order_id;
