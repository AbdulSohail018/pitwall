-- Position at the end of each lap: the last position update before the next lap started.
WITH lap_marks AS (
    SELECT session_key, driver_number, lap_number, CAST(date_start AS TIMESTAMPTZ) AS lap_start_ts
    FROM raw_of_laps WHERE date_start IS NOT NULL
),
pos AS (
    SELECT session_key, driver_number, position, CAST(date AS TIMESTAMPTZ) AS ts FROM raw_of_position
)
SELECT m.session_key, m.driver_number, m.lap_number - 1 AS completed_lap, p.position
FROM lap_marks m
ASOF JOIN pos p
  ON p.session_key = m.session_key AND p.driver_number = m.driver_number AND p.ts <= m.lap_start_ts
WHERE m.lap_number > 1
