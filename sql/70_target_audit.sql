-- Sensitivity only; the model target remains strict TIMESTAMP > TIMESTAMP.
CREATE OR REPLACE TABLE target_definition_sensitivity AS
SELECT p.fold,count(*)::BIGINT AS orders,sum(o.is_late)::BIGINT AS timestamp_late,
    sum((CAST(o.post_delivery_date AS DATE)>CAST(o.at_estimated_delivery_date AS DATE))::INTEGER)::BIGINT AS calendar_date_late,
    sum((o.is_late=1 AND CAST(o.post_delivery_date AS DATE)=CAST(o.at_estimated_delivery_date AS DATE))::INTEGER)::BIGINT AS same_promised_day_late,
    avg(o.is_late)::DOUBLE AS timestamp_late_rate,
    avg((CAST(o.post_delivery_date AS DATE)>CAST(o.at_estimated_delivery_date AS DATE))::INTEGER)::DOUBLE AS calendar_late_rate
FROM order_fact o JOIN prediction_cohorts p USING(at_order_id) GROUP BY p.fold ORDER BY p.fold;
