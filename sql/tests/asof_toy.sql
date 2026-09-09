CREATE TABLE toy_orders AS SELECT * FROM (VALUES (1,10),(2,11),(3,21)) AS t(id,purchase_time);
CREATE TABLE toy_events AS SELECT * FROM (VALUES (10,2),(20,5),(30,1000)) AS t(event_time,n);
CREATE TABLE toy_result AS SELECT o.id,coalesce(e.n,0) AS n
FROM toy_orders o ASOF LEFT JOIN toy_events e ON o.purchase_time>e.event_time ORDER BY o.id;
