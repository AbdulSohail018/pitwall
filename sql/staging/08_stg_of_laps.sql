-- Every timed lap with its tyre, plus flags used to decide which laps are representative of pace.
WITH pit_in AS (
    SELECT DISTINCT session_key, driver_number, lap_number FROM raw_of_pit WHERE lap_number IS NOT NULL
),
laps AS (
    SELECT
        l.session_key, l.driver_number, l.lap_number, l.lap_duration,
        l.duration_sector_1 AS s1, l.duration_sector_2 AS s2, l.duration_sector_3 AS s3,
        l.st_speed, coalesce(l.is_pit_out_lap, false) AS is_out_lap,
        p.lap_number IS NOT NULL AS is_in_lap,
        st.compound,
        st.stint_number,
        st.tyre_age_at_start + (l.lap_number - st.lap_start) AS tyre_age
    FROM raw_of_laps l
    LEFT JOIN pit_in p ON p.session_key = l.session_key AND p.driver_number = l.driver_number
                      AND p.lap_number = l.lap_number
    LEFT JOIN raw_of_stints st ON st.session_key = l.session_key AND st.driver_number = l.driver_number
                              AND l.lap_number BETWEEN st.lap_start AND st.lap_end
),
bounds AS (
    -- The 107% rule of thumb: laps far off the session's quick laps are traffic, SC/VSC or incidents.
    SELECT session_key, quantile_cont(lap_duration, 0.05) AS fast_ref, max(lap_number) AS race_laps
    FROM laps WHERE lap_duration IS NOT NULL GROUP BY session_key
)
SELECT
    l.*,
    b.race_laps,
    l.lap_duration - {{fuel_correction}} * (b.race_laps - l.lap_number) AS fuel_corrected_s,
    (l.lap_number > 1 AND NOT l.is_out_lap AND NOT l.is_in_lap AND l.lap_duration IS NOT NULL
        AND l.lap_duration <= b.fast_ref * 1.07)                     AS is_clean
FROM laps l
JOIN bounds b USING (session_key)
