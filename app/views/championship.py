import html

import plotly.graph_objects as go
import streamlit as st
from lib import FADE, INK, MUTED, PURPLE, RULE, SEASON, colour_for, q, setup_page, show, spread_labels

setup_page("Championship")

title = q("SELECT * FROM mart_title_math")
prog = q("SELECT * FROM mart_points_progression WHERE season = {{season}} ORDER BY round")
sched = q("SELECT * FROM stg_schedule WHERE season = {{season}} ORDER BY round")

if title.empty or prog.empty:
    st.markdown('<div class="pw-headline">Waiting for the first race of the season</div>', unsafe_allow_html=True)
    st.info("No results are loaded yet. Run `python -m pitwall.refresh` to pull the latest data.")
    st.stop()

leader = title.iloc[0]
second = title.iloc[1]
alive = title[title.still_in_contention]
after_round = int(leader.after_round)
total_rounds = len(sched)
races_left = int(leader.races_left)
next_race = sched[sched["round"] > after_round].head(1)


def headline() -> str:
    lead = int(second.gap_to_leader)
    name = leader.driver_name.split()[-1]
    if races_left == 0:
        return f"{leader.driver_name} is the {SEASON} world champion"
    if len(alive) == 1:
        return f"{name} has clinched the {SEASON} title"
    rivals = alive.iloc[1:]["driver_name"].str.split().str[-1].tolist()
    who = rivals[0] if len(rivals) == 1 else ", ".join(rivals[:-1]) + " and " + rivals[-1]
    return f"{name} leads by {lead} points. Only {who} can still catch him."


left = f"{races_left} {'race' if races_left == 1 else 'races'}"
sprints = int(leader.sprints_left)
status = f"After round {after_round} of {total_rounds}."
if not next_race.empty:
    nr = next_race.iloc[0]
    status += f" Next: {nr.race_name}, {nr.race_date:%d %B}."
st.markdown(f'<div class="pw-status">{status}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="pw-headline">{html.escape(headline())}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="pw-sub">{left}{f" and {sprints} sprint" + ("s" if sprints != 1 else "") if sprints else ""} remain, '
    f'worth up to {int(leader.max_points_available)} points to any one driver.</div>',
    unsafe_allow_html=True,
)

# ---- Timing tower + points race -------------------------------------------------
tower_col, chart_col = st.columns([0.9, 2.1], gap="large")

with tower_col:
    rows = []
    for i, r in enumerate(title.head(12).itertuples(), 1):
        gap = "Leader" if r.gap_to_leader == 0 else f"+{int(r.gap_to_leader)}"
        rows.append(
            f'<div class="tower-row{"" if r.still_in_contention else " out"}">'
            f'<span class="tower-pos">{i}</span>'
            f'<span class="tower-bar" style="background:{colour_for(r.constructor_name)}"></span>'
            f'<span><span class="tower-code">{html.escape(str(r.driver_code))}</span>'
            f'<span class="tower-team">{html.escape(r.constructor_name)}</span></span>'
            f'<span class="tower-gap{" leader" if r.gap_to_leader == 0 else ""}">{gap}</span></div>'
        )
    st.markdown(
        f'<div class="tower"><div class="tower-head"><span>Drivers</span><span>{int(leader.points)} pts lead</span></div>'
        + "".join(rows) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Greyed drivers can no longer win the title.")

with chart_col:
    focus = set(title.head(5).driver_code)
    fig = go.Figure()
    for code, d in prog.groupby("driver_code"):
        on = code in focus
        team = d.constructor_name.iloc[-1]
        fig.add_trace(go.Scatter(
            x=d["round"], y=d.cumulative_points, mode="lines", name=code,
            line=dict(color=colour_for(team) if on else FADE, width=3.2 if on else 1.2, shape="spline", smoothing=0.4),
            opacity=1 if on else 0.6, showlegend=False,
            hovertemplate=f"<b>{code}</b> after %{{customdata}}<br>%{{y:.0f}} pts<extra></extra>",
            customdata=d.race_name,
        ))
    ends = prog[prog.driver_code.isin(focus)].sort_values("round").groupby("driver_code").tail(1)
    span = float(prog.cumulative_points.max() or 1)
    for (_, last), y in zip(ends.iterrows(), spread_labels(ends.cumulative_points.tolist(), span * 0.045),
                            strict=False):
        fig.add_annotation(x=last["round"], y=y, text=f"<b>{last.driver_code}</b>", showarrow=False,
                           xanchor="left", xshift=8, font=dict(color=INK, size=13))
    fig.update_layout(title="Points after each round", xaxis_title="Round", yaxis_title=None,
                      xaxis=dict(range=[0.6, after_round + 1.4], dtick=1), margin=dict(r=40))
    show(fig, 470)

# ---- Title math -------------------------------------------------------------------
st.markdown("## Can they still win it?")
contenders = title.head(8).iloc[::-1]
fig = go.Figure()
fig.add_trace(go.Bar(
    y=contenders.driver_code, x=contenders.gap_to_leader, orientation="h",
    marker_color=[PURPLE if a else FADE for a in contenders.still_in_contention],
    text=[f"{int(g)} behind" if g else "Leader" for g in contenders.gap_to_leader], textposition="outside",
    hovertemplate="%{y}: %{x} points behind<extra></extra>",
))
fig.add_vline(x=float(leader.max_points_available), line=dict(color=INK, dash="dash", width=1.5))
fig.add_annotation(x=float(leader.max_points_available), y=1.02, yref="paper", showarrow=False, xanchor="right",
                   text=f"{int(leader.max_points_available)} points still available", font=dict(color=MUTED, size=12))
fig.update_layout(xaxis_title="Points behind the leader", showlegend=False, bargap=0.35)
show(fig, 340)
st.markdown(
    '<p class="note">A driver is still in contention if winning every remaining race and sprint would lift them to '
    "at least the leader's current total. Purple bars are still in it.</p>",
    unsafe_allow_html=True,
)

# ---- Constructors + scorecard --------------------------------------------------------
c1, c2 = st.columns([1, 1.25], gap="large")
with c1:
    st.markdown("## Constructors")
    cons = q("SELECT * FROM mart_constructor_season WHERE season = {{season}} ORDER BY points")
    fig = go.Figure(go.Bar(
        y=cons.constructor_name, x=cons.points, orientation="h",
        marker_color=[colour_for(c) for c in cons.constructor_id], marker_line=dict(color=RULE, width=0.5),
        text=cons.points.astype(int), textposition="outside",
        hovertemplate="%{y}: %{x:.0f} pts<extra></extra>",
    ))
    fig.update_layout(xaxis_title=None, showlegend=False, bargap=0.3)
    show(fig, 420)

with c2:
    st.markdown("## Driver scorecard")
    card = q("""
        SELECT driver_code AS Driver, constructor_name AS Team, points AS Points, wins AS Wins, podiums AS Podiums,
               poles AS Poles, dnfs AS DNFs, avg_grid AS "Avg grid", avg_finish AS "Avg finish",
               avg_positions_gained AS "Places gained"
        FROM mart_driver_season WHERE season = {{season}} ORDER BY points DESC
    """)
    st.dataframe(
        card, hide_index=True, width="stretch", height=420,
        column_config={
            "Points": st.column_config.ProgressColumn("Points", format="%d", min_value=0,
                                                      max_value=float(card.Points.max() or 1)),
            "Places gained": st.column_config.NumberColumn(format="%+.1f"),
        },
    )
    st.download_button("Download scorecard (CSV)", card.to_csv(index=False), f"pitwall_scorecard_{SEASON}.csv",
                       "text/csv")
