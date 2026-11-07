-- At most 10% of clean laps in a session may be missing tyre information.
SELECT session_key, avg((compound IS NULL)::INT) AS missing_share
FROM stg_of_laps WHERE is_clean GROUP BY ALL HAVING avg((compound IS NULL)::INT) > 0.10
