-- One row per driver per Grand Prix (main race).
SELECT
    r.season, r.round, r.race_name, r.driver_id, r.driver_code, r.driver_number,
    r.given_name || ' ' || r.family_name                       AS driver_name,
    r.family_name, r.nationality, r.constructor_id, r.constructor_name,
    nullif(r.grid, 0)                                          AS grid,          -- 0 = pit-lane start
    r.position,
    r.position_text,
    coalesce(r.points, 0)                                      AS points,
    r.laps, r.status,
    -- Classified finishers have a numeric position_text; R/D/W/N/E/F mean retired/disqualified/etc.
    regexp_matches(r.position_text, '^[0-9]+$')                AS is_classified,
    (r.status = 'Finished' OR r.status LIKE '+%' OR r.status = 'Lapped') AS finished_running,
    r.fastest_lap_rank = 1                                     AS fastest_lap,
    s.race_date
FROM raw_results r
LEFT JOIN stg_schedule s USING (season, round)
