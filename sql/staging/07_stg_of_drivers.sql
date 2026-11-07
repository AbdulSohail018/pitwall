SELECT DISTINCT ON (session_key, driver_number)
    session_key, driver_number, name_acronym AS driver_code, full_name, team_name,
    '#' || coalesce(nullif(team_colour, ''), '888888') AS team_colour
FROM raw_of_drivers
ORDER BY session_key, driver_number
