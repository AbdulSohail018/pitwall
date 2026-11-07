-- Team pace per round = the team's quicker car. Feeds the season pace heatmap.
SELECT season, round, location, team_name, any_value(team_colour) AS team_colour,
       min(pace_delta_pct) AS pace_delta_pct
FROM mart_race_pace
GROUP BY ALL
