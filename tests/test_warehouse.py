"""Every SQL model builds and every data-quality test passes on a known-good synthetic season."""
import io
from contextlib import redirect_stdout

import duckdb

from pitwall import warehouse
from tests.conftest import ROUNDS, SEASON


def build(dataset):
    root, _ = dataset
    return warehouse.build(root)


def test_all_data_tests_pass(dataset):
    con = build(dataset)
    with redirect_stdout(io.StringIO()):
        failures = warehouse.run_tests(con)
    assert failures == []


def test_points_include_sprints(dataset):
    con = build(dataset)
    _, totals = dataset
    got = dict(con.execute(f"SELECT driver_id, points FROM mart_driver_season WHERE season = {SEASON}").fetchall())
    assert got == totals


def test_title_math(dataset):
    con = build(dataset)
    rows = con.execute("SELECT races_left, sprints_left, max_points_available, gap_to_leader FROM mart_title_math"
                       ).fetchall()
    assert rows[0] == (1, 1, 33, 0)
    assert all(r[3] >= 0 for r in rows)


def test_session_round_mapping_and_clean_laps(dataset):
    con = build(dataset)
    mapping = con.execute("SELECT round, location FROM stg_of_sessions WHERE session_name = 'Race' ORDER BY round"
                          ).fetchall()
    assert [m[0] for m in mapping] == [1, 2, 3, 4]
    # lap 1, the pit in-lap (15) and the out-lap (16) are never clean
    dirty = con.execute("SELECT count(*) FROM stg_of_laps WHERE is_clean AND lap_number IN (1, 15, 16)").fetchone()[0]
    assert dirty == 0
    assert con.execute("SELECT count(*) FROM stg_of_laps WHERE is_clean").fetchone()[0] > 400


def test_tyre_degradation_recovers_true_slope(dataset):
    """The synthetic data has 0.05 s/lap wear after fuel correction; the model should find it."""
    con = build(dataset)
    med = con.execute("SELECT median(deg_s_per_lap) FROM mart_tyre_deg").fetchone()[0]
    assert abs(med - 0.05) < 0.02


def test_reconciliation_test_catches_bad_points(dataset):
    root, _ = dataset
    con = warehouse.build(root)
    con.execute("UPDATE mart_points_progression SET cumulative_points = cumulative_points + 1")
    sql = (warehouse.SQL_DIR / "tests" / "points_reconcile_official.sql").read_text().replace("{{season}}", str(SEASON))
    assert len(con.execute(sql).fetchall()) > 0


def test_empty_warehouse_builds(tmp_path, monkeypatch):
    monkeypatch.setenv("PITWALL_SEASON", str(SEASON))
    con = warehouse.build(tmp_path)
    assert con.execute("SELECT count(*) FROM mart_title_math").fetchone()[0] == 0
    assert isinstance(con, duckdb.DuckDBPyConnection)
    assert len(ROUNDS) == 3
