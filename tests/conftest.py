"""A small, internally consistent synthetic season used to test every SQL model offline."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

SEASON = 2026
TEAMS = [("mercedes", "Mercedes", "Mercedes", "27F4D2"), ("ferrari", "Ferrari", "Ferrari", "E8002D"),
         ("mclaren", "McLaren", "McLaren", "FF8000")]
DRIVERS = [  # driver_id, code, number, given, family, team index, base pace (s)
    ("russell", "RUS", 63, "George", "Russell", 0, 80.0), ("antonelli", "ANT", 12, "Kimi", "Antonelli", 0, 80.1),
    ("leclerc", "LEC", 16, "Charles", "Leclerc", 1, 80.2), ("hamilton", "HAM", 44, "Lewis", "Hamilton", 1, 80.35),
    ("norris", "NOR", 4, "Lando", "Norris", 2, 80.25), ("piastri", "PIA", 81, "Oscar", "Piastri", 2, 80.3),
]
POINTS = [25, 18, 15, 12, 10, 8]
SPRINT_POINTS = [8, 7, 6, 5, 4, 3]
ROUNDS = [(1, "Australian Grand Prix", "Melbourne", "Australia", "2026-03-08", False),
          (2, "Chinese Grand Prix", "Shanghai", "China", "2026-03-15", True),
          (3, "Japanese Grand Prix", "Suzuka", "Japan", "2026-03-29", False)]
FUTURE = (4, "Abu Dhabi Grand Prix", "Yas Marina", "UAE", "2026-12-06", True)
LAPS = 30


def _driver_cols(d):
    team = TEAMS[d[5]]
    return {"driver_id": d[0], "driver_code": d[1], "driver_number": d[2], "given_name": d[3], "family_name": d[4],
            "nationality": "X", "date_of_birth": "2000-01-01", "constructor_id": team[0], "constructor_name": team[1]}


def build_dataset(root):
    rng = random.Random(7)
    j = root / "jolpica"
    o = root / "openf1"
    for sub in ("schedule", "results", "qualifying", "sprint", "pitstops", "standings_official"):
        (j / sub).mkdir(parents=True, exist_ok=True)
    o.mkdir(parents=True, exist_ok=True)

    schedule = [{"season": SEASON, "round": r, "race_name": n, "circuit_id": loc.lower(), "circuit_name": f"{loc} Circuit",
                 "locality": loc, "country": c, "lat": 0.0, "lon": 0.0, "race_date": dt, "race_time_utc": "05:00:00Z",
                 "has_sprint": sp} for r, n, loc, c, dt, sp in ROUNDS + [FUTURE]]
    pd.DataFrame(schedule).to_parquet(j / "schedule" / f"{SEASON}.parquet")
    # A past season for the history tables.
    pd.DataFrame([{**schedule[0], "season": 2025}]).to_parquet(j / "schedule" / "2025.parquet")

    results, quali, sprint, pits, sessions = [], [], [], [], []
    totals = {d[0]: 0.0 for d in DRIVERS}
    for rnd, name, loc, country, date, has_sprint in ROUNDS:
        order = sorted(DRIVERS, key=lambda d: d[6] + rng.uniform(-0.25, 0.25))
        grid = sorted(DRIVERS, key=lambda d: d[6] + rng.uniform(-0.3, 0.3))
        for pos, d in enumerate(order, 1):
            dnf = rnd == 3 and d[0] == "hamilton"
            pts = 0 if dnf else POINTS[pos - 1]
            totals[d[0]] += pts
            results.append({"season": SEASON, "round": rnd, "race_name": name, **_driver_cols(d),
                            "grid": grid.index(d) + 1, "position": pos, "position_text": "R" if dnf else str(pos),
                            "points": float(pts), "laps": LAPS - (10 if dnf else 0),
                            "status": "Engine" if dnf else "Finished", "time_millis": 5_000_000 + pos * 1000,
                            "fastest_lap_rank": pos, "fastest_lap_time": "1:20.000"})
            pits.append({"season": SEASON, "round": rnd, "driver_id": d[0], "stop": 1, "lap": 15,
                         "duration_s": 21.5 + d[5] * 0.4})
        for qpos, d in enumerate(grid, 1):
            t = 78 + d[6] - 80 + qpos * 0.01
            quali.append({"season": SEASON, "round": rnd, **_driver_cols(d), "position": qpos,
                          "q1": t + 0.5, "q2": t + 0.2, "q3": t if qpos <= 4 else None})
        if has_sprint:
            for spos, d in enumerate(order, 1):
                totals[d[0]] += SPRINT_POINTS[spos - 1]
                sprint.append({"season": SEASON, "round": rnd, "race_name": name, **_driver_cols(d), "grid": spos,
                               "position": spos, "position_text": str(spos), "points": float(SPRINT_POINTS[spos - 1]),
                               "laps": 15, "status": "Finished", "time_millis": None, "fastest_lap_rank": None,
                               "fastest_lap_time": None})

        # OpenF1 race session
        key = 9000 + rnd
        start = datetime.fromisoformat(f"{date}T05:00:00+00:00")
        sessions.append({"session_key": key, "session_name": "Race", "session_type": "Race", "meeting_key": 100 + rnd,
                         "location": loc, "circuit_short_name": loc, "country_name": country, "is_cancelled": False,
                         "date_start": start.isoformat(), "date_end": (start + timedelta(hours=2)).isoformat(),
                         "year": SEASON})
        sdir = o / f"session={key}"
        sdir.mkdir()
        drivers, laps, stints, pit, position = [], [], [], [], []
        for d in DRIVERS:
            team = TEAMS[d[5]]
            drivers.append({"session_key": key, "driver_number": d[2], "name_acronym": d[1],
                            "full_name": f"{d[3]} {d[4]}".upper(), "team_name": team[2], "team_colour": team[3]})
            stints += [{"session_key": key, "driver_number": d[2], "stint_number": 1, "compound": "MEDIUM",
                        "lap_start": 1, "lap_end": 15, "tyre_age_at_start": 0},
                       {"session_key": key, "driver_number": d[2], "stint_number": 2, "compound": "HARD",
                        "lap_start": 16, "lap_end": LAPS, "tyre_age_at_start": 0}]
            pit.append({"session_key": key, "driver_number": d[2], "lap_number": 15, "pit_duration": 22.0,
                        "stop_duration": 2.4 + d[5] * 0.2, "lane_duration": 21.8, "date": None})
            for lap in range(1, LAPS + 1):
                age = lap - 1 if lap <= 15 else lap - 16
                fuel = 0.035 * (LAPS - lap)
                t = d[6] + fuel + 0.05 * age + rng.uniform(-0.15, 0.15) + (3 if lap == 1 else 0) + (20 if lap == 16 else 0)
                ts = start + timedelta(seconds=82 * (lap - 1) + d[6] - 80)
                laps.append({"session_key": key, "driver_number": d[2], "lap_number": lap, "lap_duration": round(t, 3),
                             "duration_sector_1": t / 3, "duration_sector_2": t / 3, "duration_sector_3": t / 3,
                             "is_pit_out_lap": lap == 16, "st_speed": 310.0, "date_start": ts.isoformat()})
            for idx, dd in enumerate(order, 1):
                if dd == d:
                    position.append({"session_key": key, "driver_number": d[2], "position": idx,
                                     "date": (start + timedelta(seconds=30)).isoformat()})
        pd.DataFrame(drivers).to_parquet(sdir / "drivers.parquet")
        pd.DataFrame(laps).to_parquet(sdir / "laps.parquet")
        pd.DataFrame(stints).to_parquet(sdir / "stints.parquet")
        pd.DataFrame(pit).to_parquet(sdir / "pit.parquet")
        pd.DataFrame(position).to_parquet(sdir / "position.parquet")
        pd.DataFrame([{"session_key": key, "date": start.isoformat(), "air_temperature": 22.0,
                       "track_temperature": 35.0, "humidity": 50.0, "rainfall": 0, "wind_speed": 2.0}]
                     ).to_parquet(sdir / "weather.parquet")
        pd.DataFrame([{"session_key": key, "date": start.isoformat(), "lap_number": 5, "category": "SafetyCar",
                       "flag": None, "message": "SAFETY CAR DEPLOYED"}]).to_parquet(sdir / "race_control.parquet")

    fut = datetime.fromisoformat(f"{FUTURE[4]}T13:00:00+00:00")
    sessions.append({"session_key": 9999, "session_name": "Race", "session_type": "Race", "meeting_key": 199,
                     "location": "Yas Marina", "circuit_short_name": "Yas Marina", "country_name": "UAE",
                     "is_cancelled": False, "date_start": fut.isoformat(),
                     "date_end": (fut + timedelta(hours=2)).isoformat(), "year": SEASON})
    pd.DataFrame(results).to_parquet(j / "results" / f"{SEASON}.parquet")
    pd.DataFrame([{**results[0], "season": 2025}] + [{**r, "season": 2025} for r in results[1:6]]
                 ).to_parquet(j / "results" / "2025.parquet")
    pd.DataFrame(quali).to_parquet(j / "qualifying" / f"{SEASON}.parquet")
    pd.DataFrame(sprint).to_parquet(j / "sprint" / f"{SEASON}.parquet")
    pd.DataFrame(pits).to_parquet(j / "pitstops" / f"{SEASON}.parquet")
    standings = sorted(totals.items(), key=lambda kv: -kv[1])
    pd.DataFrame([{"season": SEASON, "round": 3, "driver_id": d, "position": i, "points": p, "wins": 0}
                  for i, (d, p) in enumerate(standings, 1)]).to_parquet(j / "standings_official" / f"{SEASON}.parquet")
    pd.DataFrame(sessions).to_parquet(o / f"sessions_{SEASON}.parquet")
    return totals


@pytest.fixture()
def dataset(tmp_path, monkeypatch):
    monkeypatch.setenv("PITWALL_SEASON", str(SEASON))
    monkeypatch.setenv("PITWALL_MIN_GRID", str(len(DRIVERS)))
    totals = build_dataset(tmp_path)
    return tmp_path, totals
