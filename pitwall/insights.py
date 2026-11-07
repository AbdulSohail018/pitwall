"""Write INSIGHTS.md: plain-English findings computed from the warehouse.  python -m pitwall.insights"""
from __future__ import annotations

from datetime import datetime, timezone

from pitwall.config import ROOT, current_season
from pitwall.warehouse import build


def _fmt_list(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def generate() -> str:
    con = build()
    season = current_season()
    df = lambda sql: con.execute(sql.replace("{{season}}", str(season))).df()  # noqa: E731
    lines = [f"# PitWall insights: {season} season", "",
             f"_Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from live OpenF1 and Jolpica data. "
             "Regenerated automatically after every daily refresh._", ""]

    title = df("SELECT * FROM mart_title_math")
    if not title.empty:
        lead, second = title.iloc[0], title.iloc[1]
        alive = title[title.still_in_contention].driver_name.tolist()
        lines += ["## The title fight", "",
                  f"- After round {int(lead.after_round)}, **{lead.driver_name}** ({lead.constructor_name}) leads "
                  f"with {int(lead.points)} points, {int(second.gap_to_leader)} ahead of {second.driver_name}.",
                  f"- {int(lead.races_left)} races and {int(lead.sprints_left)} sprints remain, worth up to "
                  f"{int(lead.max_points_available)} points.",
                  f"- Still mathematically in contention: {_fmt_list(alive)}.", ""]

    ds = df("SELECT * FROM mart_driver_season WHERE season = {{season}} ORDER BY points DESC")
    if not ds.empty:
        top_wins = ds.sort_values("wins", ascending=False).iloc[0]
        gainer = ds[ds.starts >= 5].sort_values("avg_positions_gained", ascending=False).iloc[0]
        reliable = ds[ds.starts >= 5].sort_values(["dnfs", "points"], ascending=[True, False]).iloc[0]
        winners = int((ds.wins > 0).sum())
        lines += ["## Drivers", "",
                  f"- {winners} different drivers have won a race; {top_wins.driver_name} has the most wins "
                  f"({int(top_wins.wins)}).",
                  f"- Best racecraft: {gainer.driver_name} gains {gainer.avg_positions_gained:+.1f} places per race "
                  "from the grid on average.",
                  f"- Most reliable front-runner: {reliable.driver_name}, with {int(reliable.dnfs)} DNFs in "
                  f"{int(reliable.starts)} starts.", ""]

    h2h = df("SELECT * FROM mart_teammate_h2h")
    if not h2h.empty:
        h2h["margin"] = (h2h.a_quali - h2h.b_quali).abs()
        most = h2h.sort_values("margin", ascending=False).iloc[0]
        close = h2h.sort_values("margin").iloc[0]
        lead_d, trail_d = ((most.driver_a, most.driver_b) if most.a_quali > most.b_quali
                           else (most.driver_b, most.driver_a))
        lines += ["## Teammates", "",
                  f"- Most one-sided qualifying battle: {lead_d} over {trail_d} at {most.constructor_name}, "
                  f"{int(max(most.a_quali, most.b_quali))}–{int(min(most.a_quali, most.b_quali))}.",
                  f"- Closest: {close.driver_a} v {close.driver_b} at {close.constructor_name}, "
                  f"{int(close.a_quali)}–{int(close.b_quali)}.", ""]

    tp = df("SELECT team_name, avg(pace_delta_pct) AS pace, count(*) AS races, "
            "count(*) FILTER (WHERE pace_delta_pct = 0) AS fastest FROM mart_team_pace "
            "WHERE season = {{season}} GROUP BY 1 ORDER BY pace")
    if not tp.empty:
        best, second = tp.iloc[0], tp.iloc[1] if len(tp) > 1 else tp.iloc[0]
        lines += ["## Car performance", "",
                  f"- Fastest car on race pace: **{best.team_name}**, quickest team in {int(best.fastest)} of "
                  f"{int(best.races)} races and {second.pace - best.pace:.2f}% clear of {second.team_name} on average.",
                  ""]

    deg = df("SELECT compound, median(deg_s_per_lap) AS m, count(*) AS n FROM mart_tyre_deg "
             "WHERE season = {{season}} AND r2 > 0.2 AND deg_s_per_lap BETWEEN -0.1 AND 0.5 GROUP BY 1")
    if not deg.empty:
        parts = [f"{r.compound.title()} {r.m:.3f}s/lap ({int(r.n)} stints)" for r in deg.itertuples()]
        lines += ["## Tyres", "", f"- Median fuel-corrected degradation: {_fmt_list(parts)}.", ""]

    pit = df("SELECT * FROM mart_pit_crew ORDER BY median_lane_s")
    if not pit.empty:
        p = pit.iloc[0]
        lines += ["## Pit stops", "",
                  f"- Quickest crew by median pit-lane time: {p.team} ({p.median_lane_s:.2f}s over "
                  f"{int(p.stops)} stops).", ""]

    era = df("SELECT * FROM mart_era ORDER BY top_team_win_share_pct DESC")
    if not era.empty:
        e = era.iloc[0]
        lines += ["## History", "",
                  f"- Most dominant season since {int(era.season.min())}: {int(e.season)}, when {e.top_team} won "
                  f"{int(e.top_team_wins)} of {int(e.races)} races ({e.top_team_win_share_pct:.0f}%).", ""]
    return "\n".join(lines)


def main() -> None:
    text = generate()
    (ROOT / "INSIGHTS.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
