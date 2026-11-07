-- Tyre degradation: seconds lost per lap of tyre age, from fuel-corrected clean laps, per stint.
SELECT
    season, round, location, session_key, driver_code, team_name, team_colour, compound, stint_number,
    count(*)                                         AS laps,
    regr_slope(fuel_corrected_s, tyre_age)           AS deg_s_per_lap,
    regr_r2(fuel_corrected_s, tyre_age)              AS r2,
    min(tyre_age) AS age_from, max(tyre_age) AS age_to
FROM mart_race_laps
WHERE session_name = 'Race' AND is_clean AND compound IN ('SOFT', 'MEDIUM', 'HARD')
GROUP BY ALL
HAVING count(*) >= 8
