"""DuckDB warehouse: raw parquet → staging views → marts, plus SQL data-quality tests.

    python -m pitwall.warehouse          # build and print row counts
    python -m pitwall.warehouse --test   # build, then run every test in sql/tests (exit 1 on failure)
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

import duckdb

from pitwall.config import (
    DATA_DIR,
    FUEL_CORRECTION_S_PER_LAP,
    MAX_RACE_POINTS,
    MAX_SPRINT_POINTS,
    SQL_DIR,
    current_season,
)

log = logging.getLogger(__name__)

# raw view name -> (glob relative to DATA_DIR, columns to use if no file exists yet)
RAW_SOURCES: dict[str, tuple[str, str]] = {
    "raw_schedule": ("jolpica/schedule/*.parquet",
                     "season INT, round INT, race_name VARCHAR, circuit_id VARCHAR, circuit_name VARCHAR, "
                     "locality VARCHAR, country VARCHAR, lat DOUBLE, lon DOUBLE, race_date VARCHAR, "
                     "race_time_utc VARCHAR, has_sprint BOOLEAN"),
    "raw_results": ("jolpica/results/*.parquet", None),
    "raw_sprint": ("jolpica/sprint/*.parquet", None),
    "raw_qualifying": ("jolpica/qualifying/*.parquet",
                       "season INT, round INT, driver_id VARCHAR, driver_code VARCHAR, constructor_id VARCHAR, "
                       "constructor_name VARCHAR, position INT, q1 DOUBLE, q2 DOUBLE, q3 DOUBLE"),
    "raw_pitstops": ("jolpica/pitstops/*.parquet",
                     "season INT, round INT, driver_id VARCHAR, stop INT, lap INT, duration_s DOUBLE"),
    "raw_standings_official": ("jolpica/standings_official/*.parquet",
                               "season INT, round INT, driver_id VARCHAR, position INT, points DOUBLE, wins INT"),
    "raw_of_sessions": ("openf1/sessions_*.parquet", None),
    "raw_of_drivers": ("openf1/session=*/drivers.parquet", None),
    "raw_of_laps": ("openf1/session=*/laps.parquet", None),
    "raw_of_stints": ("openf1/session=*/stints.parquet", None),
    "raw_of_pit": ("openf1/session=*/pit.parquet", None),
    "raw_of_weather": ("openf1/session=*/weather.parquet", None),
    "raw_of_race_control": ("openf1/session=*/race_control.parquet", None),
    "raw_of_position": ("openf1/session=*/position.parquet", None),
}

RESULT_COLUMNS = ("season INT, round INT, race_name VARCHAR, driver_id VARCHAR, driver_code VARCHAR, "
                  "driver_number INT, given_name VARCHAR, family_name VARCHAR, nationality VARCHAR, "
                  "date_of_birth VARCHAR, constructor_id VARCHAR, constructor_name VARCHAR, grid INT, position INT, "
                  "position_text VARCHAR, points DOUBLE, laps INT, status VARCHAR, time_millis BIGINT, "
                  "fastest_lap_rank INT, fastest_lap_time VARCHAR")
EMPTY_FALLBACK = {"raw_results": RESULT_COLUMNS, "raw_sprint": RESULT_COLUMNS}

# OpenF1 tables used by staging, with minimal columns for an empty warehouse.
OPENF1_EMPTY = {
    "raw_of_sessions": "session_key BIGINT, session_name VARCHAR, session_type VARCHAR, meeting_key BIGINT, "
                       "location VARCHAR, circuit_short_name VARCHAR, country_name VARCHAR, date_start VARCHAR, "
                       "date_end VARCHAR, is_cancelled BOOLEAN, year INT",
    "raw_of_drivers": "session_key BIGINT, driver_number INT, name_acronym VARCHAR, full_name VARCHAR, "
                      "team_name VARCHAR, team_colour VARCHAR",
    "raw_of_laps": "session_key BIGINT, driver_number INT, lap_number INT, lap_duration DOUBLE, "
                   "duration_sector_1 DOUBLE, duration_sector_2 DOUBLE, duration_sector_3 DOUBLE, "
                   "is_pit_out_lap BOOLEAN, st_speed DOUBLE, date_start VARCHAR",
    "raw_of_stints": "session_key BIGINT, driver_number INT, stint_number INT, compound VARCHAR, lap_start INT, "
                     "lap_end INT, tyre_age_at_start INT",
    "raw_of_pit": "session_key BIGINT, driver_number INT, lap_number INT, pit_duration DOUBLE, "
                  "stop_duration DOUBLE, lane_duration DOUBLE, date VARCHAR",
    "raw_of_weather": "session_key BIGINT, date VARCHAR, air_temperature DOUBLE, track_temperature DOUBLE, "
                      "humidity DOUBLE, rainfall DOUBLE, wind_speed DOUBLE",
    "raw_of_race_control": "session_key BIGINT, date VARCHAR, lap_number INT, category VARCHAR, flag VARCHAR, "
                           "message VARCHAR",
    "raw_of_position": "session_key BIGINT, driver_number INT, position INT, date VARCHAR",
}
EMPTY_FALLBACK.update(OPENF1_EMPTY)


def _register_raw(con: duckdb.DuckDBPyConnection, data_dir: Path) -> None:
    for view, (pattern, columns) in RAW_SOURCES.items():
        files = sorted(data_dir.glob(pattern))
        base = f"{view}__base"
        if files:
            paths = ", ".join(f"'{p.as_posix()}'" for p in files)
            con.execute(f"CREATE OR REPLACE VIEW {base} AS SELECT * FROM read_parquet([{paths}], union_by_name=true)")
        else:
            con.execute(f"CREATE OR REPLACE TABLE {base} ({columns or EMPTY_FALLBACK[view]})")
        # Guarantee the columns staging relies on exist, even if a source omitted them.
        expected = OPENF1_EMPTY.get(view)
        have = {r[0] for r in con.execute(f"DESCRIBE {base}").fetchall()}
        extra = []
        if expected:
            for col in expected.split(","):
                name, dtype = col.split()
                if name not in have:
                    extra.append(f"CAST(NULL AS {dtype}) AS {name}")
        select = "*" + (", " + ", ".join(extra) if extra else "")
        con.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT {select} FROM {base}")


def _run_sql_dir(con: duckdb.DuckDBPyConnection, folder: Path, params: dict) -> list[str]:
    built = []
    for path in sorted(folder.glob("*.sql")):
        sql = path.read_text()
        for key, value in params.items():
            sql = sql.replace("{{" + key + "}}", str(value))
        name = re.sub(r"^\d+_", "", path.stem)  # "01_stg_schedule.sql" builds table stg_schedule
        try:
            con.execute(f"CREATE OR REPLACE TABLE {name} AS {sql}")
        except duckdb.Error as exc:
            raise RuntimeError(f"model {path.name} failed: {exc}") from exc
        built.append(name)
    return built


def build(data_dir: Path | None = None, db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """Build the full warehouse and return an open connection."""
    con = duckdb.connect(db_path)
    _register_raw(con, data_dir or DATA_DIR)
    params = {
        "season": current_season(),
        "fuel_correction": FUEL_CORRECTION_S_PER_LAP,
        "max_race_points": MAX_RACE_POINTS,
        "max_sprint_points": MAX_SPRINT_POINTS,
    }
    _run_sql_dir(con, SQL_DIR / "staging", params)
    _run_sql_dir(con, SQL_DIR / "marts", params)
    return con


def run_tests(con: duckdb.DuckDBPyConnection) -> list[tuple[str, int]]:
    """Each test is a query returning failing rows; zero rows means it passes."""
    failures = []
    for path in sorted((SQL_DIR / "tests").glob("*.sql")):
        sql = (path.read_text().replace("{{season}}", str(current_season()))
               .replace("{{min_grid}}", os.getenv("PITWALL_MIN_GRID", "18")))
        rows = con.execute(sql).fetchall()
        status = "PASS" if not rows else f"FAIL ({len(rows)} rows)"
        print(f"  {status:<16} {path.stem}")
        if rows:
            print(f"      e.g. {rows[:3]}")
            failures.append((path.stem, len(rows)))
    return failures


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="run data-quality tests after building")
    parser.add_argument("--db", default=":memory:", help="persist to a .duckdb file instead of memory")
    args = parser.parse_args()

    con = build(db_path=args.db)
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'stg_%' OR table_name LIKE 'mart_%' "
        "ORDER BY 1").fetchall()]
    for t in tables:
        print(f"  {t:<32} {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:>8,} rows")
    if args.test:
        print("\nData-quality tests:")
        failures = run_tests(con)
        if failures:
            sys.exit(1)


if __name__ == "__main__":
    main()
