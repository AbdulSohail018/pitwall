SELECT season, round, driver_id FROM stg_results
WHERE driver_id IS NULL OR constructor_id IS NULL OR points IS NULL OR status IS NULL
