"""Jolpica-F1 (the Ergast-compatible API): schedule, results, sprints, qualifying, pit stops, standings."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from pitwall.config import DATA_DIR, HISTORY_START, JOLPICA_BASE, current_season
from pitwall.ingest.http import RateLimitedClient

log = logging.getLogger(__name__)
PAGE = 100


def _num(value, cast=float):
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def _paged_races(client: RateLimitedClient, path: str) -> list[dict]:
    """Fetch every page of a race-table endpoint; returns the Races entries (a race may span pages)."""
    races, offset = [], 0
    while True:
        payload = client.get_json(path, params={"limit": PAGE, "offset": offset})
        if not payload:
            break
        data = payload["MRData"]
        races.extend(data.get("RaceTable", {}).get("Races", []))
        offset += PAGE
        if offset >= int(data.get("total", 0)):
            break
    return races


def _race_key(race: dict) -> dict:
    return {"season": int(race["season"]), "round": int(race["round"])}


def parse_schedule(races: list[dict]) -> pd.DataFrame:
    rows = []
    for r in races:
        loc = r["Circuit"]["Location"]
        rows.append({
            **_race_key(r),
            "race_name": r["raceName"],
            "circuit_id": r["Circuit"]["circuitId"],
            "circuit_name": r["Circuit"]["circuitName"],
            "locality": loc.get("locality"),
            "country": loc.get("country"),
            "lat": _num(loc.get("lat")),
            "lon": _num(loc.get("long")),
            "race_date": r["date"],
            "race_time_utc": r.get("time"),
            "has_sprint": "Sprint" in r,
        })
    return pd.DataFrame(rows)


def _driver_cols(row: dict) -> dict:
    d, c = row["Driver"], row["Constructor"]
    return {
        "driver_id": d["driverId"],
        "driver_code": d.get("code"),
        "driver_number": _num(row.get("number") or d.get("permanentNumber"), int),
        "given_name": d.get("givenName"),
        "family_name": d.get("familyName"),
        "nationality": d.get("nationality"),
        "date_of_birth": d.get("dateOfBirth"),
        "constructor_id": c["constructorId"],
        "constructor_name": c["name"],
    }


def parse_results(races: list[dict], key: str = "Results") -> pd.DataFrame:
    rows = []
    for r in races:
        for res in r.get(key, []):
            fl = res.get("FastestLap", {})
            rows.append({
                **_race_key(r),
                "race_name": r["raceName"],
                **_driver_cols(res),
                "grid": _num(res.get("grid"), int),
                "position": _num(res.get("position"), int),
                "position_text": res.get("positionText"),
                "points": _num(res.get("points")),
                "laps": _num(res.get("laps"), int),
                "status": res.get("status"),
                "time_millis": _num(res.get("Time", {}).get("millis"), int),
                "fastest_lap_rank": _num(fl.get("rank"), int),
                "fastest_lap_time": fl.get("Time", {}).get("time"),
            })
    return pd.DataFrame(rows)


def lap_time_to_seconds(text: str | None) -> float | None:
    if not text:
        return None
    try:
        if ":" in text:
            minutes, seconds = text.split(":", 1)
            return int(minutes) * 60 + float(seconds)
        return float(text)
    except ValueError:
        return None


def parse_qualifying(races: list[dict]) -> pd.DataFrame:
    rows = []
    for r in races:
        for q in r.get("QualifyingResults", []):
            times = {k.lower(): lap_time_to_seconds(q.get(k)) for k in ("Q1", "Q2", "Q3")}
            rows.append({**_race_key(r), **_driver_cols(q), "position": _num(q.get("position"), int), **times})
    return pd.DataFrame(rows)


def parse_pitstops(races: list[dict]) -> pd.DataFrame:
    rows = []
    for r in races:
        for p in r.get("PitStops", []):
            rows.append({
                **_race_key(r),
                "driver_id": p["driverId"],
                "stop": _num(p.get("stop"), int),
                "lap": _num(p.get("lap"), int),
                "duration_s": lap_time_to_seconds(p.get("duration")),
            })
    return pd.DataFrame(rows)


def parse_driver_standings(payload: dict) -> pd.DataFrame:
    lists = payload["MRData"]["StandingsTable"]["StandingsLists"]
    if not lists:
        return pd.DataFrame()
    sl = lists[0]
    return pd.DataFrame([{
        "season": int(sl["season"]),
        "round": int(sl["round"]),
        "driver_id": s["Driver"]["driverId"],
        "position": _num(s.get("position"), int),
        "points": _num(s.get("points")),
        "wins": _num(s.get("wins"), int),
    } for s in sl["DriverStandings"]])


def _write(df: pd.DataFrame, path: Path) -> int:
    if df.empty:  # e.g. no sprints before 2021: write nothing rather than a column-less file
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return len(df)


def ingest(client: RateLimitedClient | None = None, out: Path | None = None,
           seasons: list[int] | None = None) -> dict:
    """Fetch history (once) and the current season (every run). Returns row counts."""
    client = client or RateLimitedClient(JOLPICA_BASE, max_per_second=3)
    out = (out or DATA_DIR) / "jolpica"
    season_now = current_season()
    seasons = seasons or list(range(HISTORY_START, season_now + 1))
    counts: dict[str, int] = {}

    for season in seasons:
        is_current = season == season_now
        marker = out / "results" / f"{season}.parquet"
        if marker.exists() and not is_current:
            continue  # past seasons never change
        log.info("jolpica: season %s", season)
        schedule = client.get_json(f"{season}.json", params={"limit": PAGE})
        sched_races = schedule["MRData"]["RaceTable"]["Races"] if schedule else []
        counts[f"schedule_{season}"] = _write(parse_schedule(sched_races), out / "schedule" / f"{season}.parquet")
        counts[f"results_{season}"] = _write(parse_results(_paged_races(client, f"{season}/results.json")), marker)
        counts[f"qualifying_{season}"] = _write(
            parse_qualifying(_paged_races(client, f"{season}/qualifying.json")), out / "qualifying" / f"{season}.parquet")
        sprint = parse_results(_paged_races(client, f"{season}/sprint.json"), key="SprintResults")
        counts[f"sprint_{season}"] = _write(sprint, out / "sprint" / f"{season}.parquet")

        if is_current:
            stops = []
            done_rounds = sorted(pd.read_parquet(marker)["round"].unique()) if counts[f"results_{season}"] else []
            for rnd in done_rounds:
                stops.append(parse_pitstops(_paged_races(client, f"{season}/{rnd}/pitstops.json")))
            pit = pd.concat(stops, ignore_index=True) if stops else pd.DataFrame()
            counts[f"pitstops_{season}"] = _write(pit, out / "pitstops" / f"{season}.parquet")
            standings = client.get_json(f"{season}/driverStandings.json")
            if standings:
                counts[f"standings_{season}"] = _write(parse_driver_standings(standings),
                                                       out / "standings_official" / f"{season}.parquet")
    log.info("jolpica: %d requests", client.requests_made)
    return counts
