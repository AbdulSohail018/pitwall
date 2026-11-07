import plotly.graph_objects as go
import streamlit as st

from lib import INK, PURPLE, TYRES, colour_for, q, setup_page, short_team, show

setup_page("Teams")

st.markdown('<div class="pw-headline">Who has the fastest car?</div>', unsafe_allow_html=True)
st.markdown('<div class="pw-sub">Race pace strips out grid position and luck: it is each team\'s median clean lap, '
            'compared with the fastest team that day.</div>', unsafe_allow_html=True)

tp = q("SELECT * FROM mart_team_pace WHERE season = {{season}}")
if tp.empty:
    st.info("Team pace appears once lap data is loaded for the first race.")
    st.stop()

season_avg = tp.groupby("team_name").pace_delta_pct.mean().sort_values()
rounds = tp[["round", "location"]].drop_duplicates().sort_values("round")
grid = tp.pivot_table(index="team_name", columns="round", values="pace_delta_pct").reindex(season_avg.index)

text = grid.map(lambda v: "" if v != v else ("●" if v == 0 else f"{v:.1f}"))
fig = go.Figure(go.Heatmap(
    z=grid.values, x=[f"R{r}" for r in grid.columns], y=[short_team(t) for t in grid.index],
    colorscale=[[0, PURPLE], [0.18, "#C9B3FB"], [0.45, "#F4F1FB"], [1, "#FFFFFF"]],
    zmin=0, zmax=max(2.5, float(grid.max().max() or 0)), xgap=2, ygap=2,
    text=text.values, texttemplate="%{text}", textfont=dict(size=11, color=INK),
    customdata=[[rounds.set_index("round").location.get(c, "") for c in grid.columns]] * len(grid),
    hovertemplate="<b>%{y}</b> at %{customdata}<br>%{z:.2f}% off the fastest<extra></extra>",
    colorbar=dict(title=dict(text="% off<br>fastest", font=dict(size=11)), thickness=10),
))
fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(side="top"), plot_bgcolor="#FFFFFF")
show(fig, 70 + 38 * len(grid))
st.markdown('<p class="note">● marks the fastest team in that race. Teams are sorted by their season average.</p>',
            unsafe_allow_html=True)

left, right = st.columns(2, gap="large")

# ---- Tyre degradation ----------------------------------------------------------------------
with left:
    st.markdown("## How fast tyres fade")
    deg = q("SELECT * FROM mart_tyre_deg WHERE season = {{season}} AND r2 > 0.2 AND deg_s_per_lap BETWEEN -0.1 AND 0.5")
    if deg.empty:
        st.info("Not enough long stints to measure degradation yet.")
    else:
        fig = go.Figure()
        for compound in ["SOFT", "MEDIUM", "HARD"]:
            d = deg[deg.compound == compound]
            if d.empty:
                continue
            fig.add_trace(go.Box(
                y=d.deg_s_per_lap, name=compound.title(), boxpoints="all", jitter=0.45, pointpos=0,
                marker=dict(color=TYRES[compound], size=5, line=dict(color=INK, width=0.6)),
                line=dict(color=INK, width=1.2), fillcolor="rgba(255,255,255,0)",
                customdata=d[["driver_code", "location"]].values,
                hovertemplate="%{customdata[0]} at %{customdata[1]}<br>%{y:.3f}s per lap<extra></extra>",
            ))
        fig.update_layout(showlegend=False, yaxis_title="Seconds lost per lap of tyre age")
        show(fig, 420)
        med = deg.groupby("compound").deg_s_per_lap.median()
        parts = [f"{c.title()} {med[c]:.3f}s" for c in ["SOFT", "MEDIUM", "HARD"] if c in med]
        st.markdown(f'<p class="note">Median loss per lap: {", ".join(parts)}. Each dot is one stint of 8+ clean '
                    'laps, fuel-corrected.</p>', unsafe_allow_html=True)

# ---- Pit crews -------------------------------------------------------------------------------------
with right:
    st.markdown("## Pit crews")
    pit = q("SELECT * FROM mart_pit_crew")
    if pit.empty:
        st.info("No pit stops recorded yet.")
    else:
        use_stationary = pit.median_stationary_s.notna().sum() >= 5
        col, label = (("median_stationary_s", "Median time stationary (s)") if use_stationary
                      else ("median_lane_s", "Median pit-lane time (s)"))
        p = pit.dropna(subset=[col]).sort_values(col, ascending=False)
        best = p[col].min()
        fig = go.Figure(go.Bar(
            y=p.team, x=p[col], orientation="h",
            marker_color=[PURPLE if v == best else colour_for(t) for v, t in zip(p[col], p.team, strict=False)],
            marker_line=dict(color=INK, width=0.4), text=[f"{v:.2f}s" for v in p[col]], textposition="outside",
            hovertemplate="%{y}: %{x:.3f}s<extra></extra>",
        ))
        lo = float(p[col].min())
        fig.update_layout(xaxis=dict(title=label, range=[lo * 0.92, float(p[col].max()) * 1.04]), showlegend=False,
                          bargap=0.3)
        show(fig, 420)
        what = ("the car is stationary" if use_stationary else "the car is in the pit lane, entry to exit")
        st.markdown(f'<p class="note">Time {what}. Purple is the quickest crew.</p>', unsafe_allow_html=True)

