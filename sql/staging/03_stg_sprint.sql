SELECT
    season, round, driver_id, driver_code, constructor_id, constructor_name,
    position, coalesce(points, 0) AS points, nullif(grid, 0) AS grid, status
FROM raw_sprint
