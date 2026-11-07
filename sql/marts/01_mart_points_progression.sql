-- Cumulative championship points per driver after every round (race + sprint), every season.
WITH race AS (
    SELECT season, round, driver_id, driver_code, driver_name, constructor_id, constructor_name, points AS race_points
    FROM stg_results
),
sprint AS (
    SELECT season, round, driver_id, sum(points) AS sprint_points FROM stg_sprint GROUP BY ALL
),
rounds AS (
    SELECT r.*, coalesce(s.sprint_points, 0) AS sprint_points, r.race_points + coalesce(s.sprint_points, 0) AS round_points
    FROM race r LEFT JOIN sprint s USING (season, round, driver_id)
),
cumulative AS (
    SELECT r.*, sc.race_name, sc.race_date,
           sum(round_points) OVER (PARTITION BY r.season, r.driver_id ORDER BY r.round
                                   ROWS UNBOUNDED PRECEDING) AS cumulative_points
    FROM rounds r
    JOIN stg_schedule sc USING (season, round)
)
SELECT *, rank() OVER (PARTITION BY season, round ORDER BY cumulative_points DESC) AS standing
FROM cumulative
