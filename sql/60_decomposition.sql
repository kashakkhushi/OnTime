-- Descriptive benchmark: on-time median stage durations in the same distance
-- band. These are not observed intervention counterfactuals or carrier SLAs.
CREATE OR REPLACE TABLE stage_baselines AS
SELECT at_distance_band,median(post_handling_days)::DOUBLE AS baseline_handling,
    median(post_linehaul_days)::DOUBLE AS baseline_linehaul
FROM order_fact WHERE is_late=0 GROUP BY at_distance_band;
CREATE OR REPLACE TABLE stage_attribution AS
WITH excess AS (
    SELECT o.at_order_id,o.at_distance_band,o.days_late,o.post_handling_days,o.post_linehaul_days,
        greatest(0,o.post_handling_days-b.baseline_handling)::DOUBLE AS excess_handling,
        greatest(0,o.post_linehaul_days-b.baseline_linehaul)::DOUBLE AS excess_linehaul
    FROM order_fact o JOIN stage_baselines b USING(at_distance_band) WHERE o.is_late=1
), fractions AS (
    SELECT *, CASE WHEN excess_handling+excess_linehaul>0 THEN excess_handling/(excess_handling+excess_linehaul)
        ELSE post_handling_days/nullif(post_handling_days+post_linehaul_days,0) END::DOUBLE AS handling_share
    FROM excess
)
SELECT *,days_late*handling_share AS handling_late_days,
    days_late*(1-handling_share) AS linehaul_late_days,
    (excess_handling+excess_linehaul=0)::INTEGER AS fallback_used
FROM fractions;
CREATE OR REPLACE TABLE decomposition AS
SELECT a.at_distance_band,count(*)::BIGINT AS late_orders,sum(a.days_late)::DOUBLE AS late_days,
    sum(a.handling_late_days)::DOUBLE AS handling_late_days,sum(a.linehaul_late_days)::DOUBLE AS linehaul_late_days,
    sum(a.linehaul_late_days)/sum(a.days_late)::DOUBLE AS linehaul_share,
    avg(a.post_handling_days)::DOUBLE AS mean_handling_days,avg(a.post_linehaul_days)::DOUBLE AS mean_linehaul_days,
    sum(a.fallback_used)::BIGINT AS fallback_orders,
    max(b.baseline_handling)::DOUBLE AS baseline_handling,max(b.baseline_linehaul)::DOUBLE AS baseline_linehaul
FROM stage_attribution a JOIN stage_baselines b USING(at_distance_band) GROUP BY a.at_distance_band ORDER BY a.at_distance_band;
CREATE OR REPLACE TABLE review_summary AS
SELECT is_late,count(*)::BIGINT AS orders,count(post_review_score)::BIGINT AS reviewed_orders,
    count(*) FILTER(WHERE post_review_score IN (1,2))::BIGINT AS low_review_orders,
    count(*) FILTER(WHERE post_review_score IN (1,2))::DOUBLE/nullif(count(post_review_score),0) AS low_review_rate,
    avg(post_review_score)::DOUBLE AS mean_review_score
FROM order_fact GROUP BY is_late ORDER BY is_late;
