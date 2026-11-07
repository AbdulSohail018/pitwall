-- One row per Grand Prix on the calendar.
SELECT
    season, round, race_name, circuit_id, circuit_name, locality, country, lat, lon,
    CAST(race_date AS DATE)                                    AS race_date,
    coalesce(has_sprint, false)                                AS has_sprint
FROM raw_schedule
