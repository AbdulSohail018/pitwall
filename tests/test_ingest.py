"""Ingestion tests against a fake HTTP server shaped like the real Jolpica and OpenF1 responses."""
import json
from datetime import datetime, timezone

import httpx
import pandas as pd

from pitwall.ingest import jolpica, openf1
from pitwall.ingest.http import RateLimitedClient

DRIVER = {"driverId": "russell", "code": "RUS", "givenName": "George", "familyName": "Russell",
          "nationality": "British", "dateOfBirth": "1998-02-15", "permanentNumber": "63"}
TEAM = {"constructorId": "mercedes", "name": "Mercedes", "nationality": "German"}
RACE = {"season": "2026", "round": "1", "raceName": "Australian Grand Prix", "date": "2026-03-08", "time": "04:00:00Z",
        "Circuit": {"circuitId": "albert_park", "circuitName": "Albert Park Grand Prix Circuit",
                    "Location": {"lat": "-37.8497", "long": "144.968", "locality": "Melbourne", "country": "Australia"}}}


def mr(total, races=None, **extra):
    return {"MRData": {"total": str(total), "RaceTable": {"Races": races or []}, **extra}}


def jolpica_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/2026.json"):
        body = mr(1, [{**RACE, "Sprint": {"date": "2026-03-07"}}])
    elif path.endswith("/2026/results.json"):
        body = mr(1, [{**RACE, "Results": [{
            "number": "63", "position": "1", "positionText": "1", "points": "25", "grid": "1", "laps": "58",
            "status": "Finished", "Driver": DRIVER, "Constructor": TEAM, "Time": {"millis": "4986801"},
            "FastestLap": {"rank": "6", "lap": "21", "Time": {"time": "1:22.670"}}}]}])
    elif path.endswith("/2026/qualifying.json"):
        body = mr(1, [{**RACE, "QualifyingResults": [{"number": "63", "position": "1", "Driver": DRIVER,
                                                      "Constructor": TEAM, "Q1": "1:19.507", "Q2": "1:18.934",
                                                      "Q3": "1:18.518"}]}])
    elif path.endswith("/2026/sprint.json"):
        body = mr(0)
    elif path.endswith("/2026/1/pitstops.json"):
        body = mr(1, [{**RACE, "PitStops": [{"driverId": "russell", "stop": "1", "lap": "11", "duration": "22.120"}]}])
    elif path.endswith("/2026/driverStandings.json"):
        body = {"MRData": {"StandingsTable": {"StandingsLists": [{"season": "2026", "round": "1", "DriverStandings": [
            {"position": "1", "points": "25", "wins": "1", "Driver": DRIVER, "Constructors": [TEAM]}]}]}}}
    else:
        return httpx.Response(404)
    return httpx.Response(200, json=body)


def test_jolpica_ingest(tmp_path, monkeypatch):
    monkeypatch.setenv("PITWALL_SEASON", "2026")
    client = RateLimitedClient("https://api.test/ergast/f1", 1000, transport=httpx.MockTransport(jolpica_handler))
    counts = jolpica.ingest(client, out=tmp_path, seasons=[2026])
    assert counts["results_2026"] == 1 and counts["sprint_2026"] == 0
    res = pd.read_parquet(tmp_path / "jolpica/results/2026.parquet").iloc[0]
    assert (res.driver_code, res.points, res.grid, res.time_millis) == ("RUS", 25.0, 1, 4986801)
    q = pd.read_parquet(tmp_path / "jolpica/qualifying/2026.parquet").iloc[0]
    assert abs(q.q3 - 78.518) < 1e-9
    assert bool(pd.read_parquet(tmp_path / "jolpica/schedule/2026.parquet").iloc[0].has_sprint)
    assert pd.read_parquet(tmp_path / "jolpica/pitstops/2026.parquet").iloc[0].duration_s == 22.12
    assert not (tmp_path / "jolpica/sprint/2026.parquet").exists()


def test_lap_time_parsing():
    assert jolpica.lap_time_to_seconds("1:22.670") == 82.67
    assert jolpica.lap_time_to_seconds("27.733") == 27.733
    assert jolpica.lap_time_to_seconds("") is None
    assert jolpica.lap_time_to_seconds("bad") is None


SESSIONS = [
    {"session_key": 1, "session_name": "Race", "location": "Melbourne", "is_cancelled": False, "year": 2026,
     "date_start": "2026-03-08T04:00:00+00:00", "date_end": "2026-03-08T06:00:00+00:00"},
    {"session_key": 2, "session_name": "Race", "location": "Sakhir", "is_cancelled": True, "year": 2026,
     "date_start": "2026-04-12T15:00:00+00:00", "date_end": "2026-04-12T17:00:00+00:00"},
    {"session_key": 3, "session_name": "Race", "location": "Yas Marina", "is_cancelled": False, "year": 2026,
     "date_start": "2026-12-06T13:00:00+00:00", "date_end": "2026-12-06T15:00:00+00:00"},
]


def openf1_handler(request: httpx.Request) -> httpx.Response:
    ep = request.url.path.rsplit("/", 1)[-1]
    if ep == "sessions":
        name = request.url.params["session_name"]
        return httpx.Response(200, json=[s for s in SESSIONS if s["session_name"] == name])
    assert request.url.params["session_key"] == "1", "only completed, non-cancelled sessions are fetched"
    data = {
        "laps": [{"session_key": 1, "driver_number": 63, "lap_number": 2, "lap_duration": 81.5,
                  "is_pit_out_lap": False, "segments_sector_1": [2049], "date_start": "2026-03-08T04:05:00+00:00"}],
        "stints": [{"session_key": 1, "driver_number": 63, "stint_number": 1, "compound": "MEDIUM",
                    "lap_start": 1, "lap_end": 20, "tyre_age_at_start": 0}],
    }.get(ep, [])
    return httpx.Response(200, content=json.dumps(data))


def test_openf1_ingest_skips_cancelled_and_future(tmp_path):
    client = RateLimitedClient("https://api.test/v1", 1000, transport=httpx.MockTransport(openf1_handler))
    now = datetime(2026, 11, 6, tzinfo=timezone.utc)
    counts = openf1.ingest(client, out=tmp_path, season=2026, now=now)
    assert counts["sessions"] == 3 and counts["laps"] == 1
    laps = pd.read_parquet(tmp_path / "openf1/session=1/laps.parquet")
    assert "segments_sector_1" not in laps.columns
    assert not (tmp_path / "openf1/session=2").exists()
    assert not (tmp_path / "openf1/session=3").exists()


def test_retry_on_429():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    client = RateLimitedClient("https://api.test", 1000, transport=httpx.MockTransport(handler))
    assert client.get_json("x") == {"ok": True} and calls["n"] == 2
