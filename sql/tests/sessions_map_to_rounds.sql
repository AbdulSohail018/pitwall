-- Every finished OpenF1 race session must map to a Jolpica Grand Prix with results.
SELECT s.session_key, s.location, s.round
FROM stg_of_sessions s
WHERE s.session_name = 'Race'
  AND s.session_key IN (SELECT DISTINCT session_key FROM raw_of_laps)
  AND NOT EXISTS (SELECT 1 FROM stg_results r WHERE r.season = s.season AND r.round = s.round)
