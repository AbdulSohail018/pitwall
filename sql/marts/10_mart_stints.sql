SELECT s.season, s.round, s.session_name, s.location, d.driver_code, d.team_name, d.team_colour,
       st.stint_number, st.compound, st.lap_start, st.lap_end, st.tyre_age_at_start,
       st.lap_end - st.lap_start + 1 AS stint_laps
FROM raw_of_stints st
JOIN stg_of_sessions s USING (session_key)
LEFT JOIN stg_of_drivers d USING (session_key, driver_number)
WHERE st.lap_start IS NOT NULL
