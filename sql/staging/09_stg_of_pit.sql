-- Stationary time (car stopped) when available, else pit-lane time.
SELECT
    p.session_key, p.driver_number, p.lap_number,
    p.stop_duration  AS stationary_s,
    coalesce(p.lane_duration, p.pit_duration) AS lane_s
FROM raw_of_pit p
WHERE p.lap_number IS NOT NULL
