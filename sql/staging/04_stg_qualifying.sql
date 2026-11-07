SELECT
    season, round, driver_id, driver_code, constructor_id, constructor_name,
    position AS quali_position,
    q1, q2, q3,
    coalesce(q3, q2, q1)            AS best_quali_s
FROM raw_qualifying
