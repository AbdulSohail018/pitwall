-- Who can still win the current drivers' title, assuming they win every remaining race and sprint.
WITH last_round AS (
    SELECT max(round) AS r FROM stg_results WHERE season = {{season}}
),
remaining AS (
    SELECT count(*) AS races_left,
           count(*) FILTER (WHERE has_sprint AND round NOT IN (SELECT round FROM stg_sprint WHERE season = {{season}})) AS sprints_left
    FROM stg_schedule, last_round WHERE season = {{season}} AND round > last_round.r
),
standings AS (
    SELECT driver_id, driver_code, driver_name, constructor_name, cumulative_points AS points, standing
    FROM mart_points_progression
    WHERE season = {{season}} AND round = (SELECT r FROM last_round)
),
sprint_extra AS (   -- sprints run after the last completed Grand Prix
    SELECT driver_id, sum(points) AS pts FROM stg_sprint
    WHERE season = {{season}} AND round > (SELECT r FROM last_round) GROUP BY ALL
)
SELECT
    s.driver_id, s.driver_code, s.driver_name, s.constructor_name,
    s.points + coalesce(e.pts, 0)                                          AS points,
    max(s.points + coalesce(e.pts, 0)) OVER () - (s.points + coalesce(e.pts, 0)) AS gap_to_leader,
    rm.races_left, rm.sprints_left,
    rm.races_left * {{max_race_points}} + rm.sprints_left * {{max_sprint_points}} AS max_points_available,
    (s.points + coalesce(e.pts, 0)) + rm.races_left * {{max_race_points}} + rm.sprints_left * {{max_sprint_points}}
        >= max(s.points + coalesce(e.pts, 0)) OVER ()                     AS still_in_contention,
    (SELECT r FROM last_round)                                             AS after_round
FROM standings s
CROSS JOIN remaining rm
LEFT JOIN sprint_extra e USING (driver_id)
ORDER BY points DESC
