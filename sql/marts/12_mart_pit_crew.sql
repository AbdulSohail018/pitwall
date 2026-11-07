-- Pit crew performance. Stationary time (OpenF1) is the crew's work; pit-lane time (Jolpica) adds the drive through.
WITH stationary AS (
    SELECT d.team_name, any_value(d.team_colour) AS team_colour,
           median(p.stationary_s) AS median_stationary_s, min(p.stationary_s) AS best_stationary_s,
           count(*) AS stops_timed
    FROM stg_of_pit p
    JOIN stg_of_sessions s USING (session_key)
    JOIN stg_of_drivers d USING (session_key, driver_number)
    WHERE s.season = {{season}} AND s.session_name = 'Race' AND p.stationary_s BETWEEN 1.5 AND 8
    GROUP BY ALL
),
lane AS (
    SELECT r.constructor_name, median(p.pit_lane_s) AS median_lane_s, min(p.pit_lane_s) AS best_lane_s,
           count(*) AS stops
    FROM stg_pitstops p JOIN stg_results r USING (season, round, driver_id)
    WHERE p.season = {{season}}
    GROUP BY ALL
)
SELECT l.constructor_name AS team, s.team_colour, l.stops, round(l.median_lane_s, 3) AS median_lane_s,
       round(l.best_lane_s, 3) AS best_lane_s,
       round(s.median_stationary_s, 3) AS median_stationary_s, round(s.best_stationary_s, 3) AS best_stationary_s,
       s.stops_timed
FROM lane l
LEFT JOIN stationary s
  ON lower(replace(s.team_name, ' ', '')) LIKE '%' || lower(replace(split_part(l.constructor_name, ' ', 1), ' ', '')) || '%'
ORDER BY median_lane_s
