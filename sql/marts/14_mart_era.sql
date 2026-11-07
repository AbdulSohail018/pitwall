-- One row per season: how dominant was the best team, how many winners, how close was the title.
WITH drivers AS (
    SELECT season, driver_name, points, row_number() OVER (PARTITION BY season ORDER BY points DESC, wins DESC) AS pos
    FROM mart_driver_season
),
teams AS (
    SELECT season, constructor_name, wins, row_number() OVER (PARTITION BY season ORDER BY points DESC) AS pos
    FROM mart_constructor_season
),
races AS (
    SELECT season, count(DISTINCT round) AS races, count(DISTINCT driver_id) FILTER (WHERE position = 1) AS winners
    FROM stg_results GROUP BY ALL
)
SELECT r.season, r.races, r.winners,
       c1.driver_name AS champion, c1.points AS champion_points, c1.points - c2.points AS title_margin,
       t1.constructor_name AS top_team, t1.wins AS top_team_wins,
       round(100.0 * t1.wins / r.races, 1) AS top_team_win_share_pct
FROM races r
JOIN drivers c1 ON c1.season = r.season AND c1.pos = 1
JOIN drivers c2 ON c2.season = r.season AND c2.pos = 2
JOIN teams t1 ON t1.season = r.season AND t1.pos = 1
ORDER BY r.season
