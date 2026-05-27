"""FIFA World Cup Fantasy 2026 Assistant — Streamlit App"""
import os
import streamlit as st
import pandas as pd

from data_engine import load_data
from scoring_rules import (
    SQUAD_SLOTS, BUDGET_GROUP, BUDGET_KNOCKOUT,
    MAX_PER_COUNTRY_GROUP, SCOUT_OWNERSHIP_THRESHOLD
)
from data.team_stats import TEAM_NAMES, FDR, CS_PCT, PROJ_GOALS, FIXTURES, get_team_fdr_total

st.set_page_config(
    page_title="WC Fantasy 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚽ WC Fantasy 2026")
    st.caption("Official FIFA World Cup Fantasy assistant")

    st.subheader("Data Source")
    data_mode = st.radio("Load from", [
        "Demo data (offline)",
        "FIFA Fantasy API (live)",
        "Local JSON export",
    ])

    session_token = None
    players_file = None

    if data_mode == "FIFA Fantasy API (live)":
        st.info(
            "**How to get your session token:**\n"
            "1. Log into play.fifa.com/fantasy\n"
            "2. Open DevTools → Network tab\n"
            "3. Filter by 'fantasy' → copy the `Authorization` header value\n"
            "4. Paste it below (starts with 'Bearer ...')"
        )
        session_token = st.text_input("Session token", type="password")
        api_key = st.text_input("API-Football key (optional, for live stats)", type="password")
        if api_key:
            os.environ["API_FOOTBALL_KEY"] = api_key
    elif data_mode == "Local JSON export":
        players_file = st.text_input("JSON file path", "data/players_export.json")

    st.divider()
    st.subheader("Projection weights")
    intl_w = st.slider("International weight", 0.0, 1.0, 0.6, 0.05,
                       help="Share of projection from national team stats")
    club_w = round(1.0 - intl_w, 2)
    st.caption(f"Club form weight: {club_w}")

    st.divider()
    budget = st.number_input("Your budget ($m)", 50.0, 120.0, BUDGET_GROUP, 0.5)
    country_cap = st.slider("Max players per country", 1, 5, MAX_PER_COUNTRY_GROUP)

    load_btn = st.button("Load / Refresh Data", type="primary", use_container_width=True)


# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner="Fetching and scoring players...")
def _load(mode: str, token: str, pfile: str, iw: float) -> pd.DataFrame:
    import config as cfg_mod
    cfg_mod.NATIONAL_TEAM_WEIGHT = iw
    cfg_mod.CLUB_FORM_WEIGHT = round(1.0 - iw, 2)
    return load_data(
        session_token=token or None,
        players_file=pfile or None,
        use_demo=(mode == "Demo data (offline)"),
    )


if "df" not in st.session_state:
    st.session_state.df = None

if load_btn or st.session_state.df is None:
    try:
        st.session_state.df = _load(data_mode, session_token or "", players_file or "", intl_w)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

df = st.session_state.df
if df is None or df.empty:
    st.info("👈 Click **Load / Refresh Data** to get started.")
    st.stop()

# ── KPI strip ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Players", len(df))
k2.metric("Countries", df["country"].nunique())
k3.metric("Scout candidates", int(df["scout"].sum()))
best = df.iloc[0]
k4.metric("Top xPts/game", f"{best['xPts/game']:.2f}  —  {best['name']}")
k5.metric("Best value", f"{df.sort_values('value', ascending=False).iloc[0]['name']}")

st.divider()

# ── Helper for display ────────────────────────────────────────────────────────
SORT_LABELS = {
    "xPts group stage total": "xPts_GS",
    "xPts per game": "xPts/game",
    "Value (xPts/$m)": "value",
    "Ownership %": "own_%",
    "Price": "price",
}

def fmt(sub: pd.DataFrame):
    return (
        sub.style
        .background_gradient(subset=["xPts_GS", "xPts/game"], cmap="Greens")
        .background_gradient(subset=["value"], cmap="Blues")
        .format({
            "price": "${:.1f}m",
            "own_%": "{:.1f}%",
            "xPts/game": "{:.2f}",
            "xPts_GS": "{:.2f}",
            "value": "{:.3f}",
            "avg_cs%": "{:.1f}%",
            "avg_proj_goals": "{:.2f}",
        }, na_rep="—")
    )


# ── Greedy squad builder (must be defined before tabs) ───────────────────────
def _greedy_squad(df, budget, sort_col, country_cap):
    selected, country_counts, rem = [], {}, budget
    for pos, n in SQUAD_SLOTS.items():
        cands = df[df["pos"] == pos].sort_values(sort_col, ascending=False)
        added = 0
        for _, r in cands.iterrows():
            if added >= n:
                break
            if r["price"] > rem:
                continue
            if country_counts.get(r["team_code"], 0) >= country_cap:
                continue
            selected.append(r)
            rem -= r["price"]
            country_counts[r["team_code"]] = country_counts.get(r["team_code"], 0) + 1
            added += 1
    if not selected:
        return None
    result = pd.DataFrame(selected)
    pos_order = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
    result["_o"] = result["pos"].map(pos_order)
    return result.sort_values(["_o", sort_col], ascending=[True, False]).drop(columns=["_o"]).reset_index(drop=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🏅 Player Rankings",
    "🏗️ Squad Builder",
    "🔍 Scouts & Value",
    "📊 Fixtures & FDR",
])

# ── TAB 1: Player Rankings ────────────────────────────────────────────────────
with tab1:
    st.subheader("All Players — Ranked by Projected Group Stage Points")

    r1, r2, r3, r4 = st.columns(4)
    pos_f = r1.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="r_pos")
    max_p = r2.number_input("Max price ($m)", 4.0, 15.0, 12.0, 0.5, key="r_price")
    sort_l = r3.selectbox("Sort by", list(SORT_LABELS.keys()), key="r_sort")
    country_f = r4.selectbox("Country", ["All"] + sorted(df["country"].unique()), key="r_country")

    view = df.copy()
    if pos_f != "All":
        view = view[view["pos"] == pos_f]
    if country_f != "All":
        view = view[view["country"] == country_f]
    view = view[view["price"] <= max_p]
    view = view.sort_values(SORT_LABELS[sort_l], ascending=False).reset_index(drop=True)
    view.index += 1

    cols_main = ["name", "pos", "country", "club", "price", "own_%",
                 "xPts_GS", "xPts/game", "value", "team_fdr", "avg_cs%", "avg_proj_goals", "scout"]
    st.dataframe(fmt(view[cols_main]), use_container_width=True, height=560)

    with st.expander("📋 Full stats breakdown"):
        st.caption("International stats (last 2 years)")
        intl_cols = ["name", "pos", "country", "intl_games", "intl_goals", "intl_assists",
                     "intl_cs", "intl_sot", "intl_chances", "intl_tackles", "intl_saves",
                     "raw_intl_ppg", "participation_mult"]
        st.dataframe(view[intl_cols], use_container_width=True)
        st.caption("Club stats (current season)")
        club_cols = ["name", "pos", "club", "club_games", "club_goals", "club_assists",
                     "club_cs", "club_sot", "club_chances", "club_tackles", "club_saves",
                     "raw_club_ppg"]
        st.dataframe(view[club_cols], use_container_width=True)


# ── TAB 2: Squad Builder ──────────────────────────────────────────────────────
with tab2:
    st.subheader("Build Your Best Squad")

    b1, b2 = st.columns(2)
    build_budget = b1.number_input("Budget ($m)", 50.0, 120.0, budget, 0.5, key="build_b")
    build_sort = b2.selectbox("Optimise by", list(SORT_LABELS.keys()), key="build_sort")
    build_cap = st.slider("Max per country", 1, 5, country_cap, key="build_cap")

    if st.button("Build Optimal Squad", type="primary"):
        squad = _greedy_squad(df, build_budget, SORT_LABELS[build_sort], build_cap)
        if squad is None or squad.empty:
            st.error("Could not fill squad within budget. Try increasing budget or country cap.")
        else:
            cost = squad["price"].sum()
            total_xpts = squad["xPts_GS"].sum()
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Total cost", f"${cost:.1f}m")
            sc2.metric("Remaining", f"${build_budget - cost:.1f}m")
            sc3.metric("Total xPts (GS)", f"{total_xpts:.1f}")

            captain = squad.sort_values("xPts/game", ascending=False).iloc[0]
            vice = squad.sort_values("xPts/game", ascending=False).iloc[1]
            st.success(f"⭐ Captain: **{captain['name']}** ({captain['xPts/game']:.2f} → ×2 = {captain['xPts/game']*2:.2f} xPts/game)  |  👑 Vice: **{vice['name']}**")

            squad_cols = ["name", "pos", "country", "club", "price", "own_%",
                          "xPts_GS", "xPts/game", "value", "team_fdr", "scout"]
            st.dataframe(
                squad[squad_cols].style
                    .background_gradient(subset=["xPts_GS"], cmap="Greens")
                    .format({"price": "${:.1f}m", "own_%": "{:.1f}%",
                             "xPts_GS": "{:.2f}", "xPts/game": "{:.2f}", "value": "{:.3f}"}),
                use_container_width=True,
            )

            for pos in ["GK", "DEF", "MID", "FWD"]:
                sub = squad[squad["pos"] == pos]
                line = "  |  ".join(
                    f"{r['name']} ${r['price']:.1f}m ({r['xPts_GS']:.1f} xPts)"
                    for _, r in sub.iterrows()
                )
                st.markdown(f"**{pos}:** {line}")


# ── TAB 3: Scouts & Value ────────────────────────────────────────────────────
with tab3:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader(f"🔍 Scout Candidates (<{int(SCOUT_OWNERSHIP_THRESHOLD)}% owned, >4 xPts/game)")
        scouts = df[df["scout"]].sort_values("xPts/game", ascending=False)
        pos_s = st.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="scout_pos")
        if pos_s != "All":
            scouts = scouts[scouts["pos"] == pos_s]
        scouts.index = range(1, len(scouts) + 1)
        st.dataframe(
            scouts[["name", "pos", "country", "club", "price", "own_%",
                     "xPts_GS", "xPts/game", "value"]].style
                .background_gradient(subset=["xPts/game"], cmap="Reds")
                .format({"price": "${:.1f}m", "own_%": "{:.1f}%",
                         "xPts/game": "{:.2f}", "xPts_GS": "{:.2f}", "value": "{:.3f}"}),
            use_container_width=True, height=400,
        )

    with c2:
        st.subheader("💰 Best Value by Position (xPts GS / $m)")
        pos_v = st.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="val_pos")
        max_pv = st.number_input("Max price", 4.0, 15.0, 12.0, 0.5, key="val_price")
        val_view = df[df["price"] <= max_pv].copy()
        if pos_v != "All":
            val_view = val_view[val_view["pos"] == pos_v]
        val_view = val_view.sort_values("value", ascending=False).head(20).reset_index(drop=True)
        val_view.index += 1
        st.dataframe(
            val_view[["name", "pos", "country", "club", "price", "own_%",
                       "xPts_GS", "xPts/game", "value"]].style
                .background_gradient(subset=["value"], cmap="Blues")
                .format({"price": "${:.1f}m", "own_%": "{:.1f}%",
                         "xPts/game": "{:.2f}", "xPts_GS": "{:.2f}", "value": "{:.3f}"}),
            use_container_width=True, height=400,
        )


# ── TAB 4: Fixtures & FDR ────────────────────────────────────────────────────
with tab4:
    st.subheader("Group Stage Fixtures, FDR & Projections")
    st.caption("FDR: 1 = easiest, 5 = hardest | CS% = clean sheet probability | Proj.G = projected goals | Source: FPLJoe.com / @FPL_Marcello")

    fdr_rows = []
    for code, name in sorted(TEAM_NAMES.items(), key=lambda x: get_team_fdr_total(x[0])):
        fdr_vals = FDR.get(code, [3, 3, 3])
        cs_vals = CS_PCT.get(code, [0.3, 0.3, 0.3])
        g_vals = PROJ_GOALS.get(code, [1.0, 1.0, 1.0])
        fixtures = FIXTURES.get(code, ["?", "?", "?"])
        fdr_rows.append({
            "Country": name,
            "Code": code,
            "MD1 vs": TEAM_NAMES.get(fixtures[0], fixtures[0]) if len(fixtures) > 0 else "?",
            "FDR1": fdr_vals[0],
            "CS%1": f"{int(cs_vals[0]*100)}%",
            "xG1": g_vals[0],
            "MD2 vs": TEAM_NAMES.get(fixtures[1], fixtures[1]) if len(fixtures) > 1 else "?",
            "FDR2": fdr_vals[1],
            "CS%2": f"{int(cs_vals[1]*100)}%",
            "xG2": g_vals[1],
            "MD3 vs": TEAM_NAMES.get(fixtures[2], fixtures[2]) if len(fixtures) > 2 else "?",
            "FDR3": fdr_vals[2],
            "CS%3": f"{int(cs_vals[2]*100)}%",
            "xG3": g_vals[2],
            "Total FDR": sum(fdr_vals),
            "Avg CS%": f"{int(sum(cs_vals)/3*100)}%",
        })

    fdr_df = pd.DataFrame(fdr_rows).sort_values("Total FDR")

    def color_fdr(val):
        colors = {1: "background-color:#1a7a1a;color:white",
                  2: "background-color:#5cb85c;color:white",
                  3: "background-color:#f0ad4e;color:black",
                  4: "background-color:#d9534f;color:white",
                  5: "background-color:#8b0000;color:white"}
        return colors.get(val, "")

    st.dataframe(
        fdr_df.style.applymap(color_fdr, subset=["FDR1", "FDR2", "FDR3"]),
        use_container_width=True, height=600,
    )

    st.subheader("Drill into a Country")
    sel_country = st.selectbox("Select country", sorted(TEAM_NAMES.values()))
    sel_code = next((c for c, n in TEAM_NAMES.items() if n == sel_country), None)
    if sel_code:
        country_players = df[df["team_code"] == sel_code].sort_values("xPts_GS", ascending=False)
        if country_players.empty:
            st.info("No players loaded for this country in current dataset.")
        else:
            country_players.index = range(1, len(country_players) + 1)
            st.dataframe(
                country_players[["name", "pos", "club", "price", "own_%",
                                  "xPts_GS", "xPts/game", "value", "scout",
                                  "intl_games", "intl_goals", "intl_assists",
                                  "club_games", "club_goals", "club_assists"]].style
                    .background_gradient(subset=["xPts_GS"], cmap="Greens")
                    .format({"price": "${:.1f}m", "own_%": "{:.1f}%",
                             "xPts_GS": "{:.2f}", "xPts/game": "{:.2f}", "value": "{:.3f}"}),
                use_container_width=True,
            )

st.divider()
st.caption("Scoring: Official FIFA WC Fantasy 2026 rules | Stats: 60% international (last 2yr) + 40% club form | Bayesian shrinkage K=max(3, 40/√games) | Participation floor 0.75 for <8 intl appearances | FDR & projections: FPLJoe.com / @FPL_Marcello")
