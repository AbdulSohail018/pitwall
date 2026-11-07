SELECT session_key, CAST(date AS TIMESTAMPTZ) AS ts, lap_number, category, flag, message,
    CASE
        WHEN message ILIKE '%VIRTUAL SAFETY CAR DEPLOYED%' THEN 'VSC'
        WHEN message ILIKE '%SAFETY CAR DEPLOYED%'         THEN 'SC'
        WHEN flag = 'RED'                                  THEN 'RED FLAG'
        ELSE NULL
    END AS neutralisation
FROM raw_of_race_control
