-- Current-season teammate battles: qualifying, race and points.
WITH q AS (
    SELECT round, constructor_id, driver_id, driver_code, quali_position,
           CASE WHEN q3 IS NOT NULL THEN 3 WHEN q2 IS NOT NULL THEN 2 ELSE 1 END AS seg, q1, q2, q3
    FROM stg_qualifying WHERE season = {{season}}
),
qpair AS (
    SELECT a.constructor_id, a.driver_id AS a_id, b.driver_id AS b_id,
           (a.quali_position < b.quali_position)::INT AS a_quali_win,
           CASE least(a.seg, b.seg) WHEN 3 THEN (a.q3 - b.q3) / b.q3 WHEN 2 THEN (a.q2 - b.q2) / b.q2
                ELSE (a.q1 - b.q1) / b.q1 END * 100 AS a_gap_pct
    FROM q a JOIN q b ON a.round = b.round AND a.constructor_id = b.constructor_id AND a.driver_id < b.driver_id
),
r AS (SELECT round, constructor_id, driver_id, position, is_classified FROM stg_results WHERE season = {{season}}),
rpair AS (
    SELECT a.constructor_id, a.driver_id AS a_id, b.driver_id AS b_id,
           (a.position < b.position)::INT AS a_race_win
    FROM r a JOIN r b ON a.round = b.round AND a.constructor_id = b.constructor_id AND a.driver_id < b.driver_id
    WHERE a.is_classified AND b.is_classified
),
pairs AS (
    SELECT constructor_id, a_id, b_id,
           sum(a_quali_win) AS a_quali, count(*) - sum(a_quali_win) AS b_quali,
           round(median(a_gap_pct), 3) AS a_median_quali_gap_pct
    FROM qpair GROUP BY ALL
),
races AS (
    SELECT constructor_id, a_id, b_id, sum(a_race_win) AS a_race, count(*) - sum(a_race_win) AS b_race
    FROM rpair GROUP BY ALL
),
pts AS (SELECT driver_id, driver_code, driver_name, points, starts FROM mart_driver_season WHERE season = {{season}})
SELECT
    p.constructor_id, cs.constructor_name,
    pa.driver_code AS driver_a, pb.driver_code AS driver_b,
    pa.driver_name AS driver_a_name, pb.driver_name AS driver_b_name,
    p.a_quali, p.b_quali, coalesce(r.a_race, 0) AS a_race, coalesce(r.b_race, 0) AS b_race,
    pa.points AS a_points, pb.points AS b_points, p.a_median_quali_gap_pct
FROM pairs p
LEFT JOIN races r USING (constructor_id, a_id, b_id)
JOIN pts pa ON pa.driver_id = p.a_id
JOIN pts pb ON pb.driver_id = p.b_id
LEFT JOIN mart_constructor_season cs ON cs.season = {{season}} AND cs.constructor_id = p.constructor_id
WHERE p.a_quali + p.b_quali >= 3          -- ignore one-off substitutes
ORDER BY cs.standing
