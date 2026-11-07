SELECT * FROM mart_title_math WHERE gap_to_leader < 0 OR max_points_available < 0
UNION ALL
SELECT * FROM mart_title_math WHERE (SELECT count(*) FILTER (WHERE gap_to_leader = 0) FROM mart_title_math) = 0
