-- Our points model (race + sprint) must match the official standings exactly.
-- Jolpica can stamp the standings with the next round as soon as that weekend has started
-- (e.g. after qualifying), before any race result exists, so compare against our latest
-- completed round that is not after the official one.
WITH official AS (
    SELECT * FROM raw_standings_official
    WHERE season = {{season}}
      AND round = (SELECT max(round) FROM raw_standings_official WHERE season = {{season}})
),
ours AS (
    SELECT driver_id, cumulative_points AS points FROM mart_points_progression
    WHERE season = {{season}}
      AND round = (SELECT max(round) FROM mart_points_progression
                   WHERE season = {{season}} AND round <= (SELECT max(round) FROM official))
)
SELECT o.driver_id, o.points AS official, ours.points AS computed
FROM official o
LEFT JOIN ours USING (driver_id)
WHERE abs(o.points - coalesce(ours.points, 0)) > 0.01
