-- Weather and neutralisations per race session.
WITH wx AS (
    SELECT session_key, round(avg(air_temperature), 1) AS air_c, round(avg(track_temperature), 1) AS track_c,
           round(max(track_temperature), 1) AS track_max_c, bool_or(raining) AS rain
    FROM stg_of_weather GROUP BY ALL
),
neutral AS (
    SELECT session_key,
           count(*) FILTER (WHERE neutralisation = 'SC') AS safety_cars,
           count(*) FILTER (WHERE neutralisation = 'VSC') AS virtual_safety_cars,
           count(*) FILTER (WHERE neutralisation = 'RED FLAG') AS red_flags
    FROM stg_of_race_control GROUP BY ALL
)
SELECT s.season, s.round, s.session_name, s.location, s.country_name, s.date_start,
       w.air_c, w.track_c, w.track_max_c, coalesce(w.rain, false) AS rain,
       coalesce(n.safety_cars, 0) AS safety_cars, coalesce(n.virtual_safety_cars, 0) AS virtual_safety_cars,
       coalesce(n.red_flags, 0) AS red_flags
FROM stg_of_sessions s
LEFT JOIN wx w USING (session_key)
LEFT JOIN neutral n USING (session_key)
