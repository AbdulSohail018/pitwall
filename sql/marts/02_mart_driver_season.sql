-- One row per driver per season: the core scorecard.
WITH quali AS (
    SELECT season, driver_id, count(*) FILTER (WHERE quali_position = 1) AS poles,
           avg(quali_position) AS avg_quali_position
    FROM stg_qualifying GROUP BY ALL
),
sprint AS (SELECT season, driver_id, sum(points) AS sprint_points FROM stg_sprint GROUP BY ALL),
team AS (
    SELECT DISTINCT ON (season, driver_id) season, driver_id, constructor_id, constructor_name
    FROM stg_results ORDER BY season, driver_id, round DESC
)
SELECT
    r.season, r.driver_id, any_value(r.driver_code) AS driver_code, any_value(r.driver_name) AS driver_name,
    t.constructor_id, t.constructor_name,
    count(*)                                                         AS starts,
    sum(r.points) + coalesce(any_value(s.sprint_points), 0)          AS points,
    count(*) FILTER (WHERE r.position = 1)                           AS wins,
    count(*) FILTER (WHERE r.position <= 3)                          AS podiums,
    coalesce(any_value(q.poles), 0)                                  AS poles,
    count(*) FILTER (WHERE r.fastest_lap)                            AS fastest_laps,
    count(*) FILTER (WHERE NOT r.finished_running)                   AS dnfs,
    round(avg(r.grid), 2)                                            AS avg_grid,
    round(avg(r.position) FILTER (WHERE r.is_classified), 2)         AS avg_finish,
    round(avg(r.grid - r.position) FILTER (WHERE r.is_classified AND r.grid IS NOT NULL), 2) AS avg_positions_gained,
    round(any_value(q.avg_quali_position), 2)                        AS avg_quali_position,
    round((sum(r.points) + coalesce(any_value(s.sprint_points), 0)) / count(*), 2) AS points_per_start
FROM stg_results r
LEFT JOIN quali q USING (season, driver_id)
LEFT JOIN sprint s USING (season, driver_id)
LEFT JOIN team t USING (season, driver_id)
GROUP BY r.season, r.driver_id, t.constructor_id, t.constructor_name
