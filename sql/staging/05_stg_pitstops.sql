-- Jolpica pit-lane times (entry to exit), current season.
SELECT season, round, driver_id, stop, lap, duration_s AS pit_lane_s
FROM raw_pitstops
WHERE duration_s BETWEEN 10 AND 60          -- longer values are red-flag stoppages, not pit stops
