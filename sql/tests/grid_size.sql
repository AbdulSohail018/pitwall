-- A completed Grand Prix should have a full field (allowing for very old or disrupted events).
SELECT season, round, count(*) AS cars FROM stg_results GROUP BY ALL HAVING count(*) < {{min_grid}}
