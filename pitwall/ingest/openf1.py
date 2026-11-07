"""OpenF1: lap-by-lap timing, tyre stints, pit stops, weather, race control and positions."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from pitwall.config import DATA_DIR, OPENF1_BASE, current_season
from pitwall.ingest.http import RateLimitedClient

log = logging.getLogger(__name__)

ENDPOINTS = ["drivers", "laps", "stints", "pit", "weather", "race_control", "position"]
DROP_COLUMNS = {"segments_sector_1", "segments_sector_2", "segments_sector_3", "headshot_url"}
# Recently finished sessions are re-fetched for a few days in case data is corrected.
REFRESH_WINDOW = timedelta(days=4)
SETTLE_TIME = timedelta(hours=2)


def completed_sessions(sessions: list[dict], now: datetime) -> list[dict]:
    done = []
    for s in sessions:
        if s.get("is_cancelled"):
            continue
        end = datetime.fromisoformat(s["date_end"])
        if end + SETTLE_TIME < now:
            done.append(s)
    return sorted(done, key=lambda s: s["date_start"])


def _frame(records: list[dict] | None) -> pd.DataFrame:
    df = pd.DataFrame(records or [])
    return df.drop(columns=[c for c in DROP_COLUMNS if c in df.columns])


def ingest(client: RateLimitedClient | None = None, out: Path | None = None, season: int | None = None,
           now: datetime | None = None) -> dict:
    client = client or RateLimitedClient(OPENF1_BASE, max_per_second=2.5)
    out = (out or DATA_DIR) / "openf1"
    season = season or current_season()
    now = now or datetime.now(timezone.utc)
    counts: dict[str, int] = {}

    sessions: list[dict] = []
    for name in ("Race", "Sprint"):
        sessions += client.get_json("sessions", params={"year": season, "session_name": name}) or []
    if not sessions:
        log.warning("openf1: no sessions for %s", season)
        return counts
    sess_df = _frame(sessions)
    out.mkdir(parents=True, exist_ok=True)
    sess_df.to_parquet(out / f"sessions_{season}.parquet", index=False)
    counts["sessions"] = len(sess_df)

    for s in completed_sessions(sessions, now):
        key = s["session_key"]
        target = out / f"session={key}"
        recent = now - datetime.fromisoformat(s["date_end"]) < REFRESH_WINDOW
        if (target / "laps.parquet").exists() and not recent:
            continue
        log.info("openf1: %s %s (%s)", s["location"], s["session_name"], key)
        target.mkdir(parents=True, exist_ok=True)
        for ep in ENDPOINTS:
            df = _frame(client.get_json(ep, params={"session_key": key}))
            if df.empty:
                continue
            df.to_parquet(target / f"{ep}.parquet", index=False)
            counts[f"{ep}"] = counts.get(ep, 0) + len(df)
    log.info("openf1: %d requests", client.requests_made)
    return counts
