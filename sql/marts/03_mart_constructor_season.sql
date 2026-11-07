WITH race AS (
    SELECT season, constructor_id, any_value(constructor_name) AS constructor_name, sum(points) AS race_points,
           count(*) FILTER (WHERE position = 1) AS wins, count(*) FILTER (WHERE position <= 3) AS podiums
    FROM stg_results GROUP BY ALL
),
sprint AS (SELECT season, constructor_id, sum(points) AS sprint_points FROM stg_sprint GROUP BY ALL)
SELECT r.season, r.constructor_id, r.constructor_name,
       r.race_points + coalesce(s.sprint_points, 0) AS points, r.wins, r.podiums,
       rank() OVER (PARTITION BY r.season ORDER BY r.race_points + coalesce(s.sprint_points, 0) DESC) AS standing
FROM race r LEFT JOIN sprint s USING (season, constructor_id)
