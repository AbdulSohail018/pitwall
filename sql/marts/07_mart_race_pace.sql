-- Race pace: each driver's median clean lap, as % off the fastest driver in that race.
WITH drv AS (
    SELECT season, round, location, session_key, driver_code, full_name, team_name, team_colour,
           median(lap_duration)   AS median_lap_s,
           count(*)               AS clean_laps
    FROM mart_race_laps
    WHERE session_name = 'Race' AND is_clean
    GROUP BY ALL
    HAVING count(*) >= 10
)
SELECT *,
       round((median_lap_s / min(median_lap_s) OVER (PARTITION BY session_key) - 1) * 100, 3) AS pace_delta_pct,
       rank() OVER (PARTITION BY session_key ORDER BY median_lap_s) AS pace_rank
FROM drv
