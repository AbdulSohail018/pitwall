-- Six-axis driver profile for the current season, as percentiles (100 = best on the grid).
WITH pace AS (
    SELECT driver_code, avg(pace_delta_pct) AS pace FROM mart_race_pace WHERE season = {{season}} GROUP BY ALL
),
consistency AS (
    SELECT driver_code, median(sd) AS lap_sd FROM (
        SELECT driver_code, session_key, stint_number, stddev_samp(fuel_corrected_s) AS sd
        FROM mart_race_laps WHERE season = {{season}} AND session_name = 'Race' AND is_clean
        GROUP BY ALL HAVING count(*) >= 6
    ) GROUP BY ALL
),
base AS (
    SELECT d.driver_code, d.driver_name, d.constructor_name, d.starts,
           d.avg_quali_position, p.pace, c.lap_sd, d.avg_positions_gained,
           1 - d.dnfs / d.starts AS finish_rate, d.points_per_start
    FROM mart_driver_season d
    LEFT JOIN pace p USING (driver_code)
    LEFT JOIN consistency c USING (driver_code)
    WHERE d.season = {{season}} AND d.starts >= 3
)
SELECT driver_code, driver_name, constructor_name, starts,
    round(100 * (1 - percent_rank() OVER (ORDER BY avg_quali_position)), 0)       AS qualifying,
    round(100 * (1 - percent_rank() OVER (ORDER BY pace NULLS LAST)), 0)          AS race_pace,
    round(100 * (1 - percent_rank() OVER (ORDER BY lap_sd NULLS LAST)), 0)        AS consistency,
    round(100 * percent_rank() OVER (ORDER BY avg_positions_gained NULLS FIRST), 0) AS racecraft,
    round(100 * percent_rank() OVER (ORDER BY finish_rate), 0)                    AS reliability,
    round(100 * percent_rank() OVER (ORDER BY points_per_start), 0)               AS scoring,
    avg_quali_position, round(pace, 3) AS pace_delta_pct, round(lap_sd, 3) AS lap_sd_s,
    avg_positions_gained, round(finish_rate, 3) AS finish_rate, points_per_start
FROM base
