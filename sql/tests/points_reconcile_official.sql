-- Our points model (race + sprint) must match the official standings exactly.
WITH ours AS (
    SELECT driver_id, cumulative_points AS points FROM mart_points_progression
    WHERE season = {{season}}
      AND round = (SELECT max(round) FROM raw_standings_official WHERE season = {{season}})
)
SELECT o.driver_id, o.points AS official, ours.points AS computed
FROM raw_standings_official o
LEFT JOIN ours USING (driver_id)
WHERE o.season = {{season}}
  AND o.round = (SELECT max(round) FROM raw_standings_official WHERE season = {{season}})
  AND abs(o.points - coalesce(ours.points, 0)) > 0.01
