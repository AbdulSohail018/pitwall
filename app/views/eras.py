import plotly.graph_objects as go
import streamlit as st

from lib import INK, PURPLE, colour_for, q, setup_page, show

setup_page("Eras")

era = q("SELECT * FROM mart_era ORDER BY season")
if era.empty:
    st.info("Historical seasons haven't been loaded yet.")
    st.stop()

first, last = int(era.season.min()), int(era.season.max())
peak = era.loc[era.top_team_win_share_pct.idxmax()]
st.markdown(f'<div class="pw-headline">Eras of dominance, {first} to {last}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="pw-sub">The most one-sided season was {int(peak.season)}, when {peak.top_team} won '
    f'{int(peak.top_team_wins)} of {int(peak.races)} races ({peak.top_team_win_share_pct:.0f}%).</div>',
    unsafe_allow_html=True,
)

fig = go.Figure()
fig.add_trace(go.Bar(
    x=era.season, y=era.top_team_win_share_pct,
    marker_color=[colour_for(t) for t in era.top_team], marker_line=dict(color=INK, width=0.5),
    customdata=era[["top_team", "top_team_wins", "races", "champion"]].values,
    text=era.top_team, textposition="inside", insidetextanchor="end", textangle=-90,
    textfont=dict(color=INK, size=11),
    hovertemplate="<b>%{x}</b>: %{customdata[0]} won %{customdata[1]} of %{customdata[2]}<br>"
                  "Champion: %{customdata[3]}<extra></extra>",
    name="Top team's share of wins",
))
fig.add_trace(go.Scatter(
    x=era.season, y=era.winners, yaxis="y2", mode="lines+markers", name="Different race winners",
    line=dict(color=PURPLE, width=2.5), marker=dict(size=7, color=PURPLE),
    hovertemplate="%{x}: %{y} different winners<extra></extra>",
))
fig.update_layout(
    yaxis=dict(title="Top team's share of wins (%)", range=[0, 105]),
    yaxis2=dict(title="Different winners", overlaying="y", side="right", range=[0, 12.5], dtick=2,
                showgrid=False),
    xaxis=dict(dtick=1), legend=dict(y=-0.14), bargap=0.25,
)
show(fig, 480)

left, right = st.columns([1.3, 1], gap="large")
with left:
    st.markdown("## Wins by team")
    wins = q("""
        SELECT season, constructor_name, wins FROM mart_constructor_season WHERE wins > 0 ORDER BY season
    """)
    totals = wins.groupby("constructor_name").wins.sum().sort_values(ascending=False)
    fig = go.Figure()
    for team in totals.index:
        d = wins[wins.constructor_name == team]
        fig.add_trace(go.Bar(x=d.season, y=d.wins, name=team, marker_color=colour_for(team),
                             marker_line=dict(color=INK, width=0.4),
                             hovertemplate=f"{team}: %{{y}} wins in %{{x}}<extra></extra>"))
    fig.update_layout(barmode="stack", xaxis=dict(dtick=1), yaxis_title="Race wins", bargap=0.2)
    show(fig, 440)

with right:
    st.markdown("## Champions")
    table = era[["season", "champion", "champion_points", "title_margin", "top_team"]].rename(columns={
        "season": "Season", "champion": "Driver champion", "champion_points": "Points",
        "title_margin": "Winning margin", "top_team": "Top team"}).sort_values("Season", ascending=False)
    st.dataframe(table, hide_index=True, width="stretch", height=440,
                 column_config={"Season": st.column_config.NumberColumn(format="%d"),
                                "Points": st.column_config.NumberColumn(format="%d"),
                                "Winning margin": st.column_config.NumberColumn(format="%d")})
    closest = era.loc[era.title_margin.idxmin()]
    st.markdown(f'<p class="note">Closest title: {int(closest.season)}, won by {closest.champion} by '
                f'{int(closest.title_margin)} points. The current season is shown as it stands.</p>',
                unsafe_allow_html=True)

