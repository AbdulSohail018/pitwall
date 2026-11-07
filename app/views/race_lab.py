import plotly.graph_objects as go
import streamlit as st

from lib import FADE, INK, MUTED, PURPLE, TYRES, kpis, q, setup_page, show

setup_page("Race Lab")

races = q("""
    SELECT DISTINCT s.round, s.location, sc.race_name, sc.race_date
    FROM stg_of_sessions s JOIN stg_schedule sc USING (season, round)
    WHERE s.season = {{season}} AND s.session_name = 'Race'
      AND s.session_key IN (SELECT session_key FROM raw_of_laps)
    ORDER BY s.round DESC
""")
if races.empty:
    st.markdown('<div class="pw-headline">No lap data yet</div>', unsafe_allow_html=True)
    st.info("Lap timing appears here a couple of hours after each race finishes.")
    st.stop()

labels = {r.round: f"Round {r.round}: {r.race_name}" for r in races.itertuples()}
rnd = st.selectbox("Race", list(labels), format_func=labels.get)
race = races[races["round"] == rnd].iloc[0]

res = q(f"SELECT * FROM stg_results WHERE season = {{{{season}}}} AND round = {rnd} ORDER BY position")
quali = q(f"SELECT * FROM stg_qualifying WHERE season = {{{{season}}}} AND round = {rnd} AND quali_position = 1")
cond = q(f"SELECT * FROM mart_race_conditions WHERE season = {{{{season}}}} AND round = {rnd} AND session_name = 'Race'")
laps = q(f"SELECT * FROM mart_race_laps WHERE season = {{{{season}}}} AND round = {rnd} AND session_name = 'Race'")
stints = q(f"SELECT * FROM mart_stints WHERE season = {{{{season}}}} AND round = {rnd} AND session_name = 'Race'")
pos = q(f"SELECT * FROM mart_positions WHERE season = {{{{season}}}} AND round = {rnd} AND session_name = 'Race'")
pace = q(f"SELECT * FROM mart_race_pace WHERE season = {{{{season}}}} AND round = {rnd} ORDER BY pace_rank")

winner = res.iloc[0] if not res.empty else None
st.markdown(f'<div class="pw-status">{race.race_date:%A %d %B %Y}</div>', unsafe_allow_html=True)
if winner is not None:
    gained = (winner.grid - 1) if winner.grid else 0
    from_txt = "from pole" if winner.grid == 1 else f"from P{int(winner.grid)}" if winner.grid else "from the pit lane"
    st.markdown(f'<div class="pw-headline">{winner.driver_name} wins in {race.location} {from_txt}</div>',
                unsafe_allow_html=True)

c = cond.iloc[0] if not cond.empty else None
fl = res[res.fastest_lap]
kpis([
    ("Pole", quali.iloc[0].driver_code if not quali.empty else "–"),
    ("Fastest lap", fl.iloc[0].driver_code if not fl.empty else "–"),
    ("Safety cars", f"{int(c.safety_cars)} SC, {int(c.virtual_safety_cars)} VSC" if c is not None else "–"),
    ("Track temp", f"{c.track_c:.0f}°C" if c is not None and c.track_c == c.track_c else "–"),
    ("Rain", ("Yes" if c.rain else "No") if c is not None else "–"),
    ("Finishers", f"{int(res.finished_running.sum())} of {len(res)}" if not res.empty else "–"),
])

order = res.driver_code.tolist()
top = order[:5]
focus = st.multiselect("Highlight drivers", order, default=top, max_selections=8)

# ---- Position chart -----------------------------------------------------------------------
st.markdown("## How the race unfolded")
if pos.empty:
    st.info("Position data isn't available for this race.")
else:
    fig = go.Figure()
    for code, d in pos.sort_values("lap").groupby("driver_code"):
        on = code in focus
        fig.add_trace(go.Scatter(
            x=d.lap, y=d.position, mode="lines", name=code, showlegend=False,
            line=dict(color=d.team_colour.iloc[0] if on else FADE, width=3 if on else 1.1, shape="hv"),
            opacity=1 if on else 0.35, hovertemplate=f"<b>{code}</b> lap %{{x}}: P%{{y}}<extra></extra>",
        ))
        if on:
            last = d.iloc[-1]
            fig.add_annotation(x=last.lap, y=last.position, text=f"<b>{code}</b>", showarrow=False, xanchor="left",
                               xshift=6, font=dict(size=12, color=INK))
    fig.update_yaxes(range=[float(pos.position.max()) + 0.5, 0.5], dtick=1, title="Position")
    fig.update_xaxes(title="Lap")
    show(fig, 520)

# ---- Tyre strategy -------------------------------------------------------------------------
st.markdown("## Tyre strategy")
if stints.empty:
    st.info("Tyre data isn't available for this race.")
else:
    fig = go.Figure()
    ordered = [d for d in order if d in set(stints.driver_code)] or sorted(stints.driver_code.unique())
    shown = set()
    for s in stints.itertuples():
        compound = s.compound if s.compound in TYRES else "UNKNOWN"
        fig.add_trace(go.Bar(
            y=[s.driver_code], x=[s.stint_laps], base=[s.lap_start - 1], orientation="h",
            marker=dict(color=TYRES.get(compound, MUTED), line=dict(color=INK, width=0.6)),
            name=compound.title(), legendgroup=compound, showlegend=compound not in shown,
            hovertemplate=(f"<b>{s.driver_code}</b> {compound.title()}<br>Laps {s.lap_start}–{s.lap_end}"
                           f" ({s.stint_laps} laps, {s.tyre_age_at_start} old at fit)<extra></extra>"),
        ))
        shown.add(compound)
    fig.update_layout(barmode="overlay", bargap=0.28, legend=dict(y=1.06, orientation="h"))
    fig.update_yaxes(categoryorder="array", categoryarray=ordered[::-1], title=None)
    fig.update_xaxes(title="Lap")
    show(fig, max(420, 24 * len(ordered)))
    st.markdown('<p class="note">Drivers are listed in finishing order.</p>', unsafe_allow_html=True)

# ---- Lap times + pace ----------------------------------------------------------------------
left, right = st.columns([1.6, 1], gap="large")
with left:
    st.markdown("## Lap times")
    clean = laps[laps.is_clean & laps.driver_code.isin(focus)]
    if clean.empty:
        st.info("Pick drivers above to compare their lap times.")
    else:
        fig = go.Figure()
        for code, d in clean.sort_values("lap_number").groupby("driver_code"):
            fig.add_trace(go.Scatter(
                x=d.lap_number, y=d.lap_duration, mode="markers", name=code,
                marker=dict(color=d.team_colour.iloc[0], size=6, line=dict(color=INK, width=0.4)),
                customdata=d[["compound", "tyre_age"]].values,
                hovertemplate=f"<b>{code}</b> lap %{{x}}: %{{y:.3f}}s<br>%{{customdata[0]}}, "
                              f"%{{customdata[1]}} laps old<extra></extra>",
            ))
        fig.update_xaxes(title="Lap")
        fig.update_yaxes(title="Lap time (s)")
        show(fig, 440)
        st.markdown('<p class="note">Clean laps only: no first lap, pit laps, or laps slower than 107% of the '
                    'quick laps (safety cars, traffic, incidents).</p>', unsafe_allow_html=True)

with right:
    st.markdown("## Race pace")
    if pace.empty:
        st.info("Not enough clean laps to rank pace.")
    else:
        p = pace.head(12).iloc[::-1]
        fig = go.Figure(go.Bar(
            y=p.driver_code, x=p.pace_delta_pct, orientation="h",
            marker_color=[PURPLE if r == 1 else c for r, c in zip(p.pace_rank, p.team_colour, strict=False)],
            text=[("Fastest" if r == 1 else f"+{d:.2f}%") for r, d in zip(p.pace_rank, p.pace_delta_pct, strict=False)],
            textposition="outside", hovertemplate="%{y}: median clean lap %{customdata:.3f}s<extra></extra>",
            customdata=p.median_lap_s,
        ))
        fig.update_layout(xaxis_title="Slower than the fastest (%)", showlegend=False, bargap=0.3)
        show(fig, 440)
