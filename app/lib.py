"""Shared helpers for the PitWall dashboard: data access, theme, colours and chart styling."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pitwall import warehouse  # noqa: E402
from pitwall.config import DATA_DIR, current_season  # noqa: E402

# ---- Palette ------------------------------------------------------------------
INK = "#14202E"
MUTED = "#5E6B7A"
PAPER = "#F2F4F6"
PANEL = "#FFFFFF"
RULE = "#D9DEE4"
PURPLE = "#7B2FF2"   # timing-screen "best"
GREEN = "#0E9F5B"    # timing-screen "improved"
FADE = "#C3CAD3"     # drivers not in focus

TYRES = {"SOFT": "#E2231A", "MEDIUM": "#F5C400", "HARD": "#E9ECEF", "INTERMEDIATE": "#2EA043", "WET": "#1F6FD1"}

FALLBACK_TEAM_COLOURS = {
    "mercedes": "#27F4D2", "ferrari": "#E8002D", "red_bull": "#3671C6", "mclaren": "#FF8000",
    "aston_martin": "#229971", "alpine": "#0093CC", "williams": "#64C4FF", "rb": "#6692FF",
    "sauber": "#52E252", "audi": "#9C9C9C", "haas": "#B6BABD", "cadillac": "#BFA25E",
}


# ---- Data ---------------------------------------------------------------------
@st.cache_resource(ttl=3600, show_spinner="Building the warehouse...")
def connection():
    return warehouse.build()


@st.cache_data(ttl=3600, show_spinner=False)
def q(sql: str) -> pd.DataFrame:
    return connection().execute(sql.replace("{{season}}", str(current_season()))).df()


def meta() -> dict:
    path = DATA_DIR / "meta.json"
    return json.loads(path.read_text()) if path.exists() else {}


SEASON = current_season()


@st.cache_data(ttl=3600, show_spinner=False)
def team_colours() -> dict[str, str]:
    """Map Jolpica constructor names and ids, and OpenF1 team names, to the official team colour from OpenF1."""
    of = q("SELECT team_name, any_value(team_colour) AS c FROM stg_of_drivers WHERE team_name IS NOT NULL GROUP BY 1")
    jc = q("SELECT DISTINCT constructor_id, constructor_name FROM stg_results WHERE season = {{season}}")
    colours: dict[str, str] = {}
    for _, row in of.iterrows():
        colours[row.team_name] = row.c
    for _, row in jc.iterrows():
        key = row.constructor_name.lower().split()[0]
        match = next((c for name, c in colours.items() if key in name.lower()), None)
        colour = match or FALLBACK_TEAM_COLOURS.get(row.constructor_id, MUTED)
        colours[row.constructor_name] = colour
        colours[row.constructor_id] = colour
    return colours


def colour_for(team: str | None) -> str:
    if not team:
        return MUTED
    return team_colours().get(team, FALLBACK_TEAM_COLOURS.get(str(team).lower(), MUTED))


# ---- Theme --------------------------------------------------------------------
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Saira+Semi+Condensed:wght@400;500;600;700;800&family=Saira:wght@400;500;600&display=swap');

:root {{ --ink:{INK}; --muted:{MUTED}; --paper:{PAPER}; --panel:{PANEL}; --rule:{RULE}; --purple:{PURPLE}; --green:{GREEN}; }}

html, body, [class*="css"], .stApp, .stMarkdown, p, li, label, input, button, textarea, select {{
  font-family: 'Saira', system-ui, sans-serif;
  font-variant-numeric: tabular-nums;
}}
.stApp {{
  background-color: var(--paper);
  background-image:
    linear-gradient(rgba(20,32,46,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(20,32,46,.035) 1px, transparent 1px);
  background-size: 24px 24px;
  color: var(--ink);
}}
h1, h2, h3, h4 {{ font-family: 'Saira Semi Condensed', sans-serif !important; color: var(--ink) !important;
  letter-spacing: -0.01em; }}
h2 {{ font-size: 1.55rem !important; font-weight: 700 !important; margin-top: 1.2rem !important; }}
h3 {{ font-size: 1.15rem !important; font-weight: 600 !important; }}
.block-container {{ padding-top: 2.2rem; max-width: 1280px; }}

[data-testid="stSidebar"] {{ background: {INK}; }}
[data-testid="stSidebar"] * {{ color: #E8ECF1 !important; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: rgba(123,47,242,.35); border-radius: 4px; }}

.pw-status {{ color: var(--muted); font-size: .9rem; margin-bottom: .2rem; }}
.pw-headline {{ font-family: 'Saira Semi Condensed', sans-serif; font-weight: 800; color: var(--ink);
  font-size: clamp(1.9rem, 3.6vw, 3.1rem); line-height: 1.04; letter-spacing: -0.02em; max-width: 22ch;
  margin: .1rem 0 .7rem; }}
.pw-sub {{ color: var(--muted); font-size: 1.05rem; max-width: 62ch; margin-bottom: 1.2rem; }}

/* Timing tower */
.tower {{ background: {INK}; border-radius: 6px; padding: .45rem 0; box-shadow: 0 10px 28px rgba(20,32,46,.18); }}
.tower-head {{ color: #9AA7B6; font-size: .78rem; padding: .15rem .9rem .45rem; display: flex; justify-content: space-between; }}
.tower-row {{ display: grid; grid-template-columns: 2.1rem 4px 1fr auto; align-items: center; gap: .55rem;
  padding: .26rem .9rem; color: #F1F4F7; font-family: 'Saira Semi Condensed', sans-serif; }}
.tower-row:nth-child(even) {{ background: rgba(255,255,255,.035); }}
.tower-pos {{ font-weight: 700; text-align: right; color: #C9D2DC; }}
.tower-bar {{ height: 1.15rem; border-radius: 2px; }}
.tower-code {{ font-weight: 700; font-size: 1.05rem; letter-spacing: .02em; }}
.tower-team {{ color: #8F9CAB; font-size: .78rem; font-family: 'Saira', sans-serif; margin-left: .4rem; }}
.tower-gap {{ font-size: .95rem; color: #DDE3EA; }}
.tower-gap.leader {{ color: #C9A7FF; font-weight: 700; }}
.tower-row.out .tower-code, .tower-row.out .tower-gap {{ color: #6F7C8B; }}

/* KPI strip: plain figures on a rule, not boxed cards */
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); border-top: 2px solid var(--ink);
  margin: .4rem 0 1.2rem; }}
.kpi {{ padding: .6rem .9rem .5rem 0; border-right: 1px solid var(--rule); }}
.kpi:last-child {{ border-right: none; }}
.kpi .v {{ font-family: 'Saira Semi Condensed', sans-serif; font-size: 1.55rem; font-weight: 700; line-height: 1.1; }}
.kpi .l {{ color: var(--muted); font-size: .85rem; }}

.note {{ color: var(--muted); font-size: .88rem; max-width: 72ch; }}
.legend-chip {{ display:inline-block; width:.7rem; height:.7rem; border-radius:50%; margin:0 .3rem 0 .8rem;
  vertical-align: middle; border: 1px solid rgba(0,0,0,.25); }}
[data-testid="stMetricValue"] {{ font-family: 'Saira Semi Condensed', sans-serif; }}
:focus-visible {{ outline: 2px solid var(--purple) !important; outline-offset: 2px; }}
</style>
"""


def setup_page(title: str) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    m = meta()
    with st.sidebar:
        st.markdown("### PitWall")
        st.caption(f"{SEASON} Formula 1 season")
        if m.get("refreshed_at"):
            st.caption(f"Data refreshed {m['refreshed_at'].replace('T', ' ')[:16]} UTC")
        st.caption("Sources: OpenF1 and Jolpica-F1. Unofficial; not affiliated with Formula 1.")


def kpis(items: list[tuple[str, str]]) -> None:
    cells = "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{label}</div></div>' for label, v in items)
    st.markdown(f'<div class="kpis">{cells}</div>', unsafe_allow_html=True)


def empty_state(message: str) -> None:
    st.info(message)


# ---- Plotly template ------------------------------------------------------------
pio.templates["pitwall"] = go.layout.Template(layout=go.Layout(
    font=dict(family="Saira, system-ui, sans-serif", color=INK, size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=PANEL,
    xaxis=dict(gridcolor="#EDF0F3", linecolor=RULE, zeroline=False, ticks="outside", tickcolor=RULE),
    yaxis=dict(gridcolor="#EDF0F3", linecolor=RULE, zeroline=False),
    margin=dict(l=10, r=10, t=36, b=10),
    hoverlabel=dict(font=dict(family="Saira Semi Condensed, sans-serif", size=13), bgcolor=INK, bordercolor=INK,
                    font_color="#fff"),
    legend=dict(orientation="h", y=-0.15, x=0, font=dict(size=12)),
    title=dict(font=dict(family="Saira Semi Condensed, sans-serif", size=16, color=INK), x=0, xanchor="left"),
    colorway=[PURPLE, GREEN, "#1F6FD1", "#E2231A", "#F59E0B", "#0EA5B7"],
))
pio.templates.default = "pitwall"


def show(fig: go.Figure, height: int = 420) -> None:
    fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})


def spread_labels(values: list[float], min_gap: float) -> list[float]:
    """Nudge end-of-line label positions apart so close finishers don't overlap. Keeps the original order."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = list(values)
    for prev, cur in zip(order, order[1:], strict=False):
        if out[cur] - out[prev] < min_gap:
            out[cur] = out[prev] + min_gap
    return out
