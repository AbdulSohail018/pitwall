-- Guard the round mapping: OpenF1's race location must belong to the Jolpica race's country.
SELECT s.season, s.round, s.location, s.country_name, sc.country
FROM stg_of_sessions s
JOIN stg_schedule sc USING (season, round)
WHERE s.session_name = 'Race'
  AND NOT (lower(sc.country) IN (lower(s.country_name), 'usa', 'uk', 'uae')
           OR lower(sc.locality) LIKE '%' || lower(split_part(s.location, ' ', 1)) || '%'
           OR lower(s.location) LIKE '%' || lower(sc.locality) || '%'
           OR lower(sc.circuit_name) LIKE '%' || lower(split_part(s.circuit_short_name, ' ', 1)) || '%')
