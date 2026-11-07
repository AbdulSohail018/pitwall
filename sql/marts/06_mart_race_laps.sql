-- Lap-level table for the Race Lab, with driver identity and team colours.
SELECT
    s.season, s.round, s.session_key, s.session_name, s.location,
    d.driver_code, d.full_name, d.team_name, d.team_colour,
    l.* EXCLUDE (session_key)
FROM stg_of_laps l
JOIN stg_of_sessions s USING (session_key)
LEFT JOIN stg_of_drivers d USING (session_key, driver_number)
