SELECT session_key, driver_number, lap_number, lap_duration FROM stg_of_laps
WHERE is_clean AND (lap_duration < 55 OR lap_duration > 180)
