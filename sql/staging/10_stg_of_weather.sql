SELECT session_key, CAST(date AS TIMESTAMPTZ) AS ts, air_temperature, track_temperature, humidity,
       coalesce(rainfall, 0) > 0 AS raining, wind_speed
FROM raw_of_weather
