"""
FIFA World Cup Fantasy 2026 Assistant
Streamlit app for player rankings, squad building, and differential scouting.
"""

import streamlit as st
import pandas as pd
import os

from src.data_loader import load_and_enrich
from src.analysis.ranker import (
    filter_by_position, filter_by_country, filter_by_club,
    filter_by_budget, top_differentials, best_value,
    get_country_summary, get_club_summary,
)
from src.analysis.team_builder import build_best_squad, suggest_captain

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WC Fantasy 2026 Assistant",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a472a 0%, #2d6a4f 100%);
        border-radius: 10px;
        padding: 12px 16px;
        color: white;
        text-align: center;
    }
    .differential-badge {
        background-color: #e63946;
        color: white;
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 0.75em;
        font-weight: bold;
    }
    .stDataFrame { font-size: 0.85em; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/a/a9/FIFA_World_Cup_2026_emblem.svg/200px-FIFA_World_Cup_2026_emblem.svg.png",
             width=120)
    st.title("WC Fantasy 2026")

    st.subheader("Data Source")
    data_mode = st.radio(
        "Load players from",
        ["Demo Data (no API key)", "API-Football + FIFA Fantasy", "Local JSON file"],
        help="Demo mode uses realistic hardcoded player data. API mode fetches live data.",
    )

    fifa_token = None
    players_file = None

    if data_mode == "API-Football + FIFA Fantasy":
        st.info("Set your API_FOOTBALL_KEY in .env and optionally paste your FIFA Fantasy session token.")
        fifa_token = st.text_input(
            "FIFA Fantasy session token (optional)",
            type="password",
            help="Open play.fifa.com → DevTools → Network → any /json/fantasy/ request → copy Authorization header value",
        )
    elif data_mode == "Local JSON file":
        players_file = st.text_input("Path to players JSON file", value="data/players.json")

    if st.button("Load / Refresh Data", type="primary"):
        with st.spinner("Fetching and scoring players..."):
            try:
                st.session_state.df = load_and_enrich(
                    fifa_session_token=fifa_token or None,
                    players_file=players_file,
                    use_demo_data=(data_mode == "Demo Data (no API key)"),
                )
                st.success(f"Loaded {len(st.session_state.df)} players.")
            except Exception as e:
                st.error(f"Error loading data: {e}")

    st.divider()
    st.subheader("Scoring Weights")
    nat_weight = st.slider("National team weight", 0.0, 1.0, 0.6, 0.05)
    club_weight = round(1.0 - nat_weight, 2)
    st.caption(f"Club form weight: {club_weight}")

    # Allow override without restart
    import config
    config.NATIONAL_TEAM_WEIGHT = nat_weight
    config.CLUB_FORM_WEIGHT = club_weight

    st.divider()
    budget = st.number_input("Budget ($m)", min_value=50.0, max_value=120.0, value=100.0, step=0.5)
    country_cap = st.slider("Max players per country", 1, 5, 3)


# ── Main content ──────────────────────────────────────────────────────────────
st.title("⚽ FIFA World Cup Fantasy 2026 Assistant")

if st.session_state.df is None:
    st.info("👈 Select a data source and click **Load / Refresh Data** to get started.")
    st.markdown("""
    ### What this assistant does
    - **Fetches** player prices and ownership % from the official FIFA Fantasy game
    - **Pulls** match statistics (goals, assists, shots on target, tackles, chances created, clean sheets) from API-Football
    - **Scores** every player using the official WC Fantasy 2026 points system
    - **Ranks** players by expected points per match, value per dollar, and differential potential
    - **Separates** stats by national team and club so you can see both contexts
    - **Builds** an optimal squad within your budget

    ### Scoring system used
    | Action | GK | DEF | MID | FWD |
    |---|---|---|---|---|
    | Goal | 6 | 6 | 5 | 4 |
    | Assist | 3 | 3 | 3 | 3 |
    | Clean sheet (60+ min) | 5 | 5 | — | — |
    | Saves (per 3) | +1 | — | — | — |
    | Tackles (per 3) | — | — | +1 | — |
    | Chances created (per 2) | — | — | +1 | — |
    | Shots on target (per 2) | — | — | — | +1 |
    | Goal outside box | +1 | +1 | +1 | +1 |
    | Yellow card | -1 | -1 | -1 | -1 |
    | Red card | -3 | -3 | -3 | -3 |
    | **Low ownership bonus** (<5%, >4pts) | **+2** | **+2** | **+2** | **+2** |
    """)
    st.stop()

df = st.session_state.df.copy()

# Re-score with updated weights if changed
if nat_weight != 0.6:
    from src.scoring.calculator import score_player
    from src.api.models import Player
    # Re-rank in place
    df = load_and_enrich(use_demo_data=True) if st.session_state.df is not None else df

# ── KPI strip ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Players", len(df))
col2.metric("Countries", df["country"].nunique())
col3.metric("Differentials (<5%)", int(df["is_differential"].sum()))
col4.metric("Avg xPts/match", f"{df['combined_xPts'].mean():.2f}")
col5.metric("Top xPts/match", f"{df['combined_xPts'].max():.2f} — {df.iloc[0]['name']}")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 All Players", "🎯 Best XI Builder", "🔍 Differentials", "🌍 By Country", "🏟️ By Club"
])


# ── Tab 1: All Players ─────────────────────────────────────────────────────────
with tab1:
    st.subheader("All Players — Ranked by Combined xPts/match")

    c1, c2, c3 = st.columns(3)
    pos_filter = c1.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"])
    max_price = c2.number_input("Max price ($m)", 4.0, 15.0, 12.0, 0.5)
    sort_col = c3.selectbox("Sort by", ["combined_xPts", "value", "differential_score", "ownership_%", "price"])

    view = df.copy()
    if pos_filter != "All":
        view = filter_by_position(view, pos_filter)
    view = filter_by_budget(view, max_price)
    view = view.sort_values(sort_col, ascending=False).reset_index(drop=True)
    view.index += 1

    display_cols = [
        "name", "position", "country", "club", "price", "ownership_%",
        "combined_xPts", "national_xPts", "club_xPts", "value", "is_differential"
    ]
    st.dataframe(
        view[display_cols].style
            .background_gradient(subset=["combined_xPts"], cmap="Greens")
            .background_gradient(subset=["value"], cmap="Blues")
            .format({"price": "${:.1f}m", "combined_xPts": "{:.2f}",
                     "national_xPts": "{:.2f}", "club_xPts": "{:.2f}",
                     "value": "{:.3f}", "ownership_%": "{:.1f}%"}),
        use_container_width=True,
        height=600,
    )


# ── Tab 2: Best XI Builder ─────────────────────────────────────────────────────
with tab2:
    st.subheader("Optimal Squad Builder")

    c1, c2 = st.columns(2)
    build_budget = c1.number_input("Budget ($m)", 50.0, 120.0, budget, 0.5, key="build_budget")
    build_sort = c2.selectbox("Optimise by", ["combined_xPts", "value", "differential_score"])
    build_cap = st.slider("Max players per country", 1, 5, country_cap, key="build_cap")

    if st.button("Build Best Squad", type="primary"):
        squad = build_best_squad(df, budget=build_budget, sort_by=build_sort, country_cap=build_cap)

        if squad.empty:
            st.error("Could not build a squad with these constraints. Try increasing budget or cap.")
        else:
            total_cost = squad["price"].sum()
            total_xpts = squad["combined_xPts"].sum()

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Total Cost", f"${total_cost:.1f}m")
            sc2.metric("Remaining Budget", f"${build_budget - total_cost:.1f}m")
            sc3.metric("Total xPts/round", f"{total_xpts:.1f}")

            # Captain recommendation
            captain = suggest_captain(squad)
            st.success(f"⭐ Suggested Captain: **{captain['name']}** ({captain['country']}) — {captain['combined_xPts']:.2f} xPts (×2 = {captain['combined_xPts']*2:.2f})")

            squad_display_cols = ["name", "position", "country", "club", "price", "ownership_%",
                                   "combined_xPts", "national_xPts", "club_xPts", "value", "is_differential"]
            st.dataframe(
                squad[squad_display_cols].style
                    .background_gradient(subset=["combined_xPts"], cmap="Greens")
                    .format({"price": "${:.1f}m", "combined_xPts": "{:.2f}",
                             "national_xPts": "{:.2f}", "club_xPts": "{:.2f}",
                             "value": "{:.3f}", "ownership_%": "{:.1f}%"}),
                use_container_width=True,
            )

            # Formation breakdown
            st.subheader("Squad Breakdown")
            for pos in ["GK", "DEF", "MID", "FWD"]:
                pos_df = squad[squad["position"] == pos]
                names = " | ".join(f"{r['name']} (${r['price']:.1f}m, {r['combined_xPts']:.2f}xPts)"
                                   for _, r in pos_df.iterrows())
                st.markdown(f"**{pos}:** {names}")


# ── Tab 3: Differentials ──────────────────────────────────────────────────────
with tab3:
    st.subheader("Differential Picks — <5% Ownership with High Upside")
    st.caption("These players score **+2 bonus pts** whenever they earn >4 pts, since they're in fewer than 5% of teams.")

    c1, c2 = st.columns(2)
    diff_pos = c1.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="diff_pos")
    diff_n = c2.slider("Show top N", 5, 30, 10)

    diff_view = df[df["is_differential"]].copy()
    if diff_pos != "All":
        diff_view = filter_by_position(diff_view, diff_pos)
    diff_view = diff_view.sort_values("differential_score", ascending=False).head(diff_n).reset_index(drop=True)
    diff_view.index += 1

    st.dataframe(
        diff_view[["name", "position", "country", "club", "price", "ownership_%",
                    "combined_xPts", "differential_score", "national_xPts", "club_xPts"]].style
            .background_gradient(subset=["differential_score"], cmap="Reds")
            .format({"price": "${:.1f}m", "combined_xPts": "{:.2f}",
                     "differential_score": "{:.2f}", "national_xPts": "{:.2f}",
                     "club_xPts": "{:.2f}", "ownership_%": "{:.1f}%"}),
        use_container_width=True,
    )

    st.subheader("Best Value Picks (xPts per $m)")
    val_pos = st.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="val_pos")
    val_view = best_value(df, position=val_pos if val_pos != "All" else None, n=15)
    st.dataframe(
        val_view[["name", "position", "country", "club", "price", "ownership_%",
                   "combined_xPts", "value"]].style
            .background_gradient(subset=["value"], cmap="Blues")
            .format({"price": "${:.1f}m", "combined_xPts": "{:.2f}",
                     "value": "{:.3f}", "ownership_%": "{:.1f}%"}),
        use_container_width=True,
    )


# ── Tab 4: By Country ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("Performance by National Team")

    country_summary = get_country_summary(df)
    st.dataframe(
        country_summary.style
            .background_gradient(subset=["avg_xPts"], cmap="Greens")
            .format({"avg_xPts": "{:.2f}", "total_xPts": "{:.2f}",
                     "avg_price": "${:.1f}m", "avg_ownership": "{:.1f}%"}),
        use_container_width=True,
    )

    st.subheader("Drill into a Country")
    selected_country = st.selectbox("Select country", sorted(df["country"].unique()))
    country_df = filter_by_country(df, selected_country).sort_values("combined_xPts", ascending=False)
    country_df.index = range(1, len(country_df) + 1)

    nat_cols = ["name", "position", "club", "price", "ownership_%",
                "combined_xPts", "nat_goals", "nat_assists", "nat_cs",
                "nat_sot", "nat_chances", "nat_tackles", "nat_saves", "nat_yc", "nat_matches"]
    available = [c for c in nat_cols if c in country_df.columns]
    st.dataframe(
        country_df[available].style
            .background_gradient(subset=["combined_xPts"], cmap="Greens")
            .format({"price": "${:.1f}m", "combined_xPts": "{:.2f}", "ownership_%": "{:.1f}%"}),
        use_container_width=True,
    )


# ── Tab 5: By Club ────────────────────────────────────────────────────────────
with tab5:
    st.subheader("Performance by Club")

    club_summary = get_club_summary(df)
    st.dataframe(
        club_summary.style
            .background_gradient(subset=["avg_xPts"], cmap="Purples")
            .format({"avg_xPts": "{:.2f}", "total_xPts": "{:.2f}", "avg_price": "${:.1f}m"}),
        use_container_width=True,
    )

    st.subheader("Drill into a Club")
    clubs = sorted([c for c in df["club"].unique() if c])
    selected_club = st.selectbox("Select club", clubs)
    club_df = filter_by_club(df, selected_club).sort_values("combined_xPts", ascending=False)
    club_df.index = range(1, len(club_df) + 1)

    club_cols = ["name", "position", "country", "price", "ownership_%",
                 "combined_xPts", "club_goals", "club_assists", "club_cs",
                 "club_sot", "club_chances", "club_tackles", "club_saves", "club_yc", "club_matches"]
    available = [c for c in club_cols if c in club_df.columns]
    st.dataframe(
        club_df[available].style
            .background_gradient(subset=["combined_xPts"], cmap="Purples")
            .format({"price": "${:.1f}m", "combined_xPts": "{:.2f}", "ownership_%": "{:.1f}%"}),
        use_container_width=True,
    )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Data: FIFA World Cup Fantasy 2026 (play.fifa.com) + API-Football (api-sports.io) · Stats weighted 60% national team / 40% club form · Low-ownership bonus (+2) applied for <5% owned players scoring >4 pts")
