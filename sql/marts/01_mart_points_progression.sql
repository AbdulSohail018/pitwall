-- Cumulative championship points per driver after every round (race + sprint), every season.
-- Drivers keep a row for rounds they missed (injury, substitution, team switch) so their total carries forward.
WITH race AS (
    SELECT season, round, driver_id, driver_code, driver_name, constructor_id, constructor_name, points AS race_points
    FROM stg_results
),
sprint AS (
    SELECT season, round, driver_id, sum(points) AS sprint_points FROM stg_sprint GROUP BY ALL
),
first_round AS (
    SELECT season, driver_id, min(round) AS first_round FROM race GROUP BY ALL
),
dense AS (   -- every driver x every completed round of the season from their debut onwards
    SELECT f.season, f.driver_id, r.round
    FROM first_round f
    JOIN (SELECT DISTINCT season, round FROM race) r ON r.season = f.season AND r.round >= f.first_round
),
rounds AS (
    SELECT d.season, d.round, d.driver_id,
           last_value(ra.driver_code IGNORE NULLS) OVER w        AS driver_code,
           last_value(ra.driver_name IGNORE NULLS) OVER w        AS driver_name,
           last_value(ra.constructor_id IGNORE NULLS) OVER w     AS constructor_id,
           last_value(ra.constructor_name IGNORE NULLS) OVER w   AS constructor_name,
           coalesce(ra.race_points, 0)                           AS race_points,
           coalesce(s.sprint_points, 0)                          AS sprint_points,
           coalesce(ra.race_points, 0) + coalesce(s.sprint_points, 0) AS round_points,
           ra.driver_id IS NOT NULL                              AS started
    FROM dense d
    LEFT JOIN race ra USING (season, round, driver_id)
    LEFT JOIN sprint s USING (season, round, driver_id)
    WINDOW w AS (PARTITION BY d.season, d.driver_id ORDER BY d.round ROWS UNBOUNDED PRECEDING)
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
