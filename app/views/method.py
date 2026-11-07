import io
from contextlib import redirect_stdout

import streamlit as st

from lib import SEASON, connection, meta, q, setup_page
from pitwall import warehouse

setup_page("Method")

st.markdown('<div class="pw-headline">How PitWall works</div>', unsafe_allow_html=True)
st.markdown('<div class="pw-sub">Every morning a scheduled job pulls fresh data from two public F1 APIs, rebuilds '
            'a DuckDB warehouse from SQL models, and refuses to publish if any data-quality test fails.</div>',
            unsafe_allow_html=True)

st.graphviz_chart("""
digraph {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="#FFFFFF", color="#C3CAD3", fontname="Saira", fontsize=11];
  edge [color="#5E6B7A"];
  jol [label="Jolpica-F1 API\\nresults, qualifying,\\nsprints, pit stops"];
  of  [label="OpenF1 API\\nlaps, tyres, pit,\\nweather, positions"];
  raw [label="Parquet snapshots\\n(committed daily)"];
  stg [label="Staging models\\nclean, typed, joined"];
  mart [label="Marts\\nstandings, pace,\\ntyres, DNA, eras"];
  test [label="Data tests\\n(block the publish)", fillcolor="#F1EAFE", color="#7B2FF2"];
  app [label="PitWall dashboard", fillcolor="#14202E", fontcolor="#FFFFFF", color="#14202E"];
  jol -> raw; of -> raw; raw -> stg -> mart -> app; mart -> test;
}
""")

m = meta()
counts = q("""
    SELECT 'Grands Prix (all seasons)' AS "Dataset", count(DISTINCT (season, round)) AS "Rows" FROM stg_results
    UNION ALL SELECT 'Race results', count(*) FROM stg_results
    UNION ALL SELECT 'Qualifying results', count(*) FROM stg_qualifying
    UNION ALL SELECT 'Laps timed (this season)', count(*) FROM stg_of_laps
    UNION ALL SELECT 'Tyre stints', count(*) FROM raw_of_stints
    UNION ALL SELECT 'Pit stops', count(*) FROM stg_pitstops
""")
left, right = st.columns(2, gap="large")
with left:
    st.markdown("## What's loaded")
    st.dataframe(counts, hide_index=True, width="stretch",
                 column_config={"Rows": st.column_config.NumberColumn(format="%d")})
    if m:
        st.caption(f"Last refresh {m.get('refreshed_at', '?')} UTC for the {m.get('season', SEASON)} season.")

with right:
    st.markdown("## Data-quality tests")
    buf = io.StringIO()
    with redirect_stdout(buf):
        failures = warehouse.run_tests(connection())
    lines = [ln.strip() for ln in buf.getvalue().splitlines() if ln.strip().startswith(("PASS", "FAIL"))]
    passed = sum(ln.startswith("PASS") for ln in lines)
    if failures:
        st.error(f"{len(failures)} of {len(lines)} tests are failing.")
    else:
        st.success(f"All {passed} tests pass on the data you're looking at.")
    for ln in lines:
        status, name = ln.split(maxsplit=1) if ln.startswith("PASS") else (ln[:4], ln.split()[-1])
        st.markdown(f"{'✓' if status == 'PASS' else '✗'} `{name.split()[-1]}`")

st.markdown("## Definitions")
st.markdown("""
- **Clean lap**: not lap 1, not a pit in- or out-lap, and no slower than 107% of the session's quick laps
  (5th percentile). This removes safety-car laps, traffic and incidents.
- **Race pace**: a driver's median clean lap, shown as the percentage slower than the fastest driver in that race.
  Team pace uses the team's quicker car.
- **Fuel correction**: cars get lighter as fuel burns. Lap times are adjusted by 0.035 s for every lap of fuel
  still on board, so tyre wear isn't hidden by the falling fuel load.
- **Tyre degradation**: the slope of fuel-corrected lap time against tyre age, per stint of 8+ clean laps,
  keeping fits with R² above 0.2.
- **Title contention**: a driver is still in it if winning every remaining race (25) and sprint (8) would bring
  them level with the leader's current total.
- **Driver DNA**: percentile ranks against every driver with 3+ starts this season.
""")
st.caption("Data: OpenF1 (openf1.org) and Jolpica-F1 (jolpi.ca), used under their public terms. "
           "PitWall is an unofficial project and is not associated with Formula 1 companies.")
