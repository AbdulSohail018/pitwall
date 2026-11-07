SELECT s.season, s.round, s.session_name, s.location, d.driver_code, d.team_name, d.team_colour,
       p.completed_lap AS lap, p.position
FROM stg_of_position p
JOIN stg_of_sessions s USING (session_key)
LEFT JOIN stg_of_drivers d USING (session_key, driver_number)
WHERE p.position IS NOT NULL
