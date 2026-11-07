import plotly.graph_objects as go
import streamlit as st

from lib import INK, MUTED, PURPLE, colour_for, q, setup_page, show

setup_page("Drivers")

dna = q("SELECT * FROM mart_driver_dna ORDER BY scoring DESC")
if dna.empty:
    st.info("Driver profiles appear after the third race of the season.")
    st.stop()

st.markdown('<div class="pw-headline">Driver DNA</div>', unsafe_allow_html=True)
st.markdown('<div class="pw-sub">Six measures of a season, each scored against the rest of the grid. '
            '100 means best on the grid, 0 means worst.</div>', unsafe_allow_html=True)

AXES = ["qualifying", "race_pace", "consistency", "racecraft", "reliability", "scoring"]
NAMES = ["Qualifying", "Race pace", "Consistency", "Racecraft", "Reliability", "Scoring"]
codes = dna.driver_code.tolist()
c1, c2 = st.columns(2)
a = c1.selectbox("Driver", codes, index=0)
b = c2.selectbox("Compare with", codes, index=1 if len(codes) > 1 else 0)

def rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    if len(h) != 6:
        return f"rgba(94,107,122,{alpha})"
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


fig = go.Figure()
for code, is_main in ((b, False), (a, True)):
    r = dna[dna.driver_code == code].iloc[0]
    colour = colour_for(r.constructor_name)
    values = [r[x] for x in AXES]
    fig.add_trace(go.Scatterpolar(
        r=values + values[:1], theta=NAMES + NAMES[:1], name=f"{code}, {r.constructor_name}",
        line=dict(color=colour if is_main else INK, width=3 if is_main else 2, dash="solid" if is_main else "dot"),
        fill="toself", fillcolor=rgba(colour, 0.28) if is_main else "rgba(0,0,0,0)",
        hovertemplate="%{theta}: %{r:.0f}<extra>" + code + "</extra>",
    ))
fig.update_layout(
    polar=dict(bgcolor="#FFFFFF", radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100], gridcolor="#E3E7EC",
                                                 tickfont=dict(color=MUTED, size=10)),
               angularaxis=dict(gridcolor="#E3E7EC", tickfont=dict(size=13, color=INK))),
    legend=dict(y=-0.08), margin=dict(l=70, r=70, t=30, b=30),
)
left, right = st.columns([1.25, 1], gap="large")
with left:
    show(fig, 480)
with right:
    ra, rb = dna[dna.driver_code == a].iloc[0], dna[dna.driver_code == b].iloc[0]
    rows = [
        ("Average qualifying position", f"{ra.avg_quali_position:.1f}", f"{rb.avg_quali_position:.1f}", "low"),
        ("Race pace off the fastest", f"{ra.pace_delta_pct:.2f}%", f"{rb.pace_delta_pct:.2f}%", "low"),
        ("Lap time spread within a stint", f"{ra.lap_sd_s:.3f}s", f"{rb.lap_sd_s:.3f}s", "low"),
        ("Places gained per race", f"{ra.avg_positions_gained:+.1f}", f"{rb.avg_positions_gained:+.1f}", "high"),
        ("Races finished", f"{ra.finish_rate:.0%}", f"{rb.finish_rate:.0%}", "high"),
        ("Points per start", f"{ra.points_per_start:.1f}", f"{rb.points_per_start:.1f}", "high"),
    ]
    raw = [(ra.avg_quali_position, rb.avg_quali_position), (ra.pace_delta_pct, rb.pace_delta_pct),
           (ra.lap_sd_s, rb.lap_sd_s), (ra.avg_positions_gained, rb.avg_positions_gained),
           (ra.finish_rate, rb.finish_rate), (ra.points_per_start, rb.points_per_start)]
    body = ""
    for (label, va, vb, better), (xa, xb) in zip(rows, raw, strict=False):
        win_a = xa == xa and xb == xb and ((xa < xb) if better == "low" else (xa > xb))
        win_b = xa == xa and xb == xb and ((xb < xa) if better == "low" else (xb > xa))
        style_a = f"color:{PURPLE};font-weight:700" if win_a else ""
        style_b = f"color:{PURPLE};font-weight:700" if win_b else ""
        body += (f'<tr><td style="padding:.45rem .2rem;color:{MUTED}">{label}</td>'
                 f'<td style="text-align:right;{style_a}">{va}</td><td style="text-align:right;{style_b}">{vb}</td></tr>')
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:.98rem;margin-top:1.2rem">'
        f'<tr style="border-bottom:2px solid {INK}"><th></th><th style="text-align:right">{a}</th>'
        f'<th style="text-align:right">{b}</th></tr>{body}</table>'
        f'<p class="note" style="margin-top:.8rem">Purple marks the better of the two.</p>',
        unsafe_allow_html=True,
    )

# ---- Teammate battles ------------------------------------------------------------------------------
st.markdown("## Teammate battles")
st.markdown('<p class="note">Your teammate has the same car, so this is the fairest comparison in the sport. '
            'Bars show how many qualifying sessions each driver won.</p>', unsafe_allow_html=True)
h2h = q("SELECT * FROM mart_teammate_h2h")
if h2h.empty:
    st.info("Teammate comparisons appear after a few races.")
else:
    fig = go.Figure()
    labels = [f"{r.driver_a} v {r.driver_b}" for r in h2h.itertuples()]
    colours = [colour_for(r.constructor_name) for r in h2h.itertuples()]
    fig.add_trace(go.Bar(y=labels, x=-h2h.a_quali, orientation="h", marker_color=colours, name="Driver A",
                         text=h2h.driver_a + " " + h2h.a_quali.astype(int).astype(str), textposition="inside",
                         insidetextanchor="start", hovertemplate="%{text} quali wins<extra></extra>"))
    fig.add_trace(go.Bar(y=labels, x=h2h.b_quali, orientation="h", marker_color=[rgba(c, 0.4) for c in colours],
                         name="Driver B",
                         text=h2h.b_quali.astype(int).astype(str) + " " + h2h.driver_b, textposition="inside",
                         insidetextanchor="end", hovertemplate="%{text} quali wins<extra></extra>"))
    fig.update_layout(barmode="relative", showlegend=False, bargap=0.35,
                      xaxis=dict(showticklabels=False, title=None, zeroline=True, zerolinecolor=INK),
                      yaxis=dict(autorange="reversed"), uniformtext=dict(minsize=11, mode="show"),
                      font=dict(color=INK))
    fig.update_traces(textfont=dict(color=INK, family="Saira Semi Condensed, Saira, sans-serif", size=13))
    show(fig, 60 + 40 * len(h2h))

    table = h2h.rename(columns={
        "constructor_name": "Team", "driver_a": "Driver A", "driver_b": "Driver B", "a_quali": "Quali A",
        "b_quali": "Quali B", "a_race": "Race A", "b_race": "Race B", "a_points": "Points A", "b_points": "Points B",
        "a_median_quali_gap_pct": "Quali gap A to B (%)",
    })[["Team", "Driver A", "Driver B", "Quali A", "Quali B", "Race A", "Race B", "Points A", "Points B",
        "Quali gap A to B (%)"]]
    st.dataframe(table, hide_index=True, width="stretch",
                 column_config={"Quali gap A to B (%)": st.column_config.NumberColumn(format="%+.3f")})
    st.markdown('<p class="note">Quali gap is the median lap-time difference in the last session both drivers '
                'reached. Negative means driver A was quicker.</p>', unsafe_allow_html=True)
