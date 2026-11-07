-- Each driver appears once per Grand Prix.
SELECT season, round, driver_id, count(*) FROM stg_results GROUP BY ALL HAVING count(*) > 1
