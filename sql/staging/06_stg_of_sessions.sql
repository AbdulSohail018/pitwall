-- OpenF1 sessions mapped to Jolpica rounds.
-- Non-cancelled races in date order line up with the Jolpica calendar; sprints share the race weekend's meeting_key.
WITH races AS (
    SELECT session_key, meeting_key, year AS season,
           row_number() OVER (PARTITION BY year ORDER BY date_start) AS round
    FROM raw_of_sessions
    WHERE session_name = 'Race' AND NOT coalesce(is_cancelled, false)
)
SELECT
    s.session_key, s.session_name, s.meeting_key, s.year AS season, r.round,
    s.location, s.circuit_short_name, s.country_name,
    CAST(s.date_start AS TIMESTAMPTZ) AS date_start,
    CAST(s.date_end   AS TIMESTAMPTZ) AS date_end
FROM raw_of_sessions s
JOIN races r ON r.meeting_key = s.meeting_key
WHERE NOT coalesce(s.is_cancelled, false)
