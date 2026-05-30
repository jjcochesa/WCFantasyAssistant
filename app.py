"""FIFA World Cup Fantasy 2026 Assistant — Streamlit App"""
import os
import datetime
import streamlit as st
import pandas as pd

import data_engine as _de
from data_engine import load_data, fetch_live_player_data, _norm_name, _match_key
from scoring_rules import (
    SQUAD_SLOTS, BUDGET_GROUP, BUDGET_KNOCKOUT,
    MAX_PER_COUNTRY_GROUP, SCOUT_OWNERSHIP_THRESHOLD, SCOUT_POINTS_THRESHOLD
)
from data.team_stats import TEAM_NAMES, FDR, CS_PCT, PROJ_GOALS, FIXTURES, get_team_fdr_total

st.set_page_config(
    page_title="WC Fantasy 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Token: secrets first, sidebar as one-time override ───────────────────────
# Set FIFA_SESSION_TOKEN once in Streamlit Cloud → App settings → Secrets.
# Format:  FIFA_SESSION_TOKEN = "Bearer eyJ..."
# The sidebar input only shows when no secret is configured.
_SECRET_TOKEN: str = ""
try:
    _SECRET_TOKEN = st.secrets.get("FIFA_SESSION_TOKEN", "")
except Exception:
    pass  # No secrets file in local dev — that's fine


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚽ WC Fantasy 2026")
    st.caption("Official FIFA World Cup Fantasy assistant")

    # Player list always loads from the maintained wc_squads.json (instant).
    # Live prices + ownership are overlaid from the FIFA Fantasy API separately.
    # The advanced expander exists only for debugging / local JSON import.
    with st.expander("Data source (advanced)", expanded=False):
        data_mode = st.radio("Load from", [
            "WC Squads (offline, all players)",
            "Local JSON export",
            "Demo data (40 players)",
        ], index=0)

    players_file = None
    _sidebar_token = ""

    if data_mode == "Local JSON export":
        players_file = st.text_input("JSON file path", "data/players_export.json")

    # Token only needed if FIFA API starts requiring auth
    if not _SECRET_TOKEN:
        with st.expander("Session token (optional)", expanded=False):
            _sidebar_token = st.text_input(
                "Bearer token", type="password", key="wc_token",
                help="Paste from play.fifa.com DevTools → Authorization header. "
                     "Or set FIFA_SESSION_TOKEN in Streamlit secrets to never paste again.",
            )

    # Resolved token: secret beats sidebar input
    session_token = _SECRET_TOKEN or _sidebar_token or None

    st.divider()
    st.caption("Weights: 65% NT / 35% club (flipped if <5 NT apps)")
    st.divider()
    budget = st.number_input("Your budget ($m)", 50.0, 120.0, BUDGET_GROUP, 0.5)
    country_cap = st.slider("Max players per country", 1, 5, MAX_PER_COUNTRY_GROUP)

    load_btn = st.button("Load / Refresh Data", type="primary", use_container_width=True)

    # Live data status — filled in after the refresh below
    live_status_placeholder = st.empty()


# ── Cached loaders ────────────────────────────────────────────────────────────

# Heavy load: stats + projections. Long TTL — stats don't change between loads.
@st.cache_data(ttl=21600, show_spinner="Scoring players...")
def _load(mode: str, token: str, pfile: str, iw: float) -> pd.DataFrame:
    import config as cfg_mod
    cfg_mod.NATIONAL_TEAM_WEIGHT = iw
    cfg_mod.CLUB_FORM_WEIGHT = round(1.0 - iw, 2)
    return load_data(
        session_token=token or None,
        players_file=pfile or None,
        use_demo=(mode == "Demo data (40 players)"),
        use_squads=(mode != "Demo data (40 players)" and mode != "Local JSON export"),
    )


# Live prices + ownership: short TTL, runs on every page render.
# Keyed on token hash so rotating the token immediately gets fresh data.
@st.cache_data(ttl=600, show_spinner=False)
def _get_live_data(token: str) -> dict:
    return fetch_live_player_data(token or None)


def _apply_live_data(df: pd.DataFrame, live: dict) -> pd.DataFrame:
    """
    Overlay real prices AND ownership % from the FIFA Fantasy API.
    Recomputes scout flag and value ratio with the updated numbers.
    """
    if not live:
        return df
    df = df.copy()

    def _get(row, field: str, fallback):
        nm = str(row.get("name", ""))
        entry = (live.get(str(row.get("id", "")))
                 or live.get(_norm_name(nm))
                 or live.get(_match_key(nm)))
        if entry and isinstance(entry, dict):
            v = entry.get(field)
            if v is not None and float(v) > 0:
                return float(v)
        return fallback

    df["own_%"] = df.apply(lambda r: _get(r, "own_pct", r["own_%"]), axis=1)
    df["price"] = df.apply(lambda r: _get(r, "price",   r["price"]),  axis=1)

    # Recompute value and scout with real prices/ownership
    df["value"] = (df["xPts_GS"] / df["price"].replace(0, float("nan"))).round(3)
    df["scout"] = (df["own_%"] < SCOUT_OWNERSHIP_THRESHOLD) & (df["xPts/game"] > SCOUT_POINTS_THRESHOLD)
    return df


# ── Load data ─────────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None
if "live_refreshed_at" not in st.session_state:
    st.session_state.live_refreshed_at = None

if load_btn:
    _load.clear()
    _get_live_data.clear()

if load_btn or st.session_state.df is None:
    try:
        st.session_state.df = _load(data_mode, session_token or "", players_file or "", 0.65)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

# Always refresh live prices + ownership on every page render (cached 10 min)
if st.session_state.df is not None and data_mode != "Demo data (40 players)":
    live_data = _get_live_data(session_token or "")
    if live_data:
        st.session_state.df = _apply_live_data(st.session_state.df, live_data)
        st.session_state.live_refreshed_at = datetime.datetime.now()

df = st.session_state.df
if df is None or df.empty:
    st.info("👈 Click **Load / Refresh Data** to get started.")
    st.stop()

# Sidebar live data status badge
with live_status_placeholder:
    if st.session_state.live_refreshed_at:
        mins_ago = int((datetime.datetime.now() - st.session_state.live_refreshed_at).total_seconds() / 60)
        st.success(f"Live prices & ownership: {mins_ago}m ago")
    else:
        st.warning("Prices & ownership: using estimates (no API)")

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
    grad_cols = [c for c in ["xPts_GS", "xPts/game"] if c in sub.columns]
    blue_cols = [c for c in ["value"] if c in sub.columns]
    s = sub.style
    if grad_cols:
        s = s.background_gradient(subset=grad_cols, cmap="Greens")
    if blue_cols:
        s = s.background_gradient(subset=blue_cols, cmap="Blues")
    fmt_map = {
        "price": "${:.1f}m", "own_%": "{:.1f}%",
        "xPts/game": "{:.2f}", "xPts_GS": "{:.2f}", "value": "{:.3f}",
        "avg_cs%": "{:.1f}%", "avg_proj_goals": "{:.2f}",
        "GD1 xG": "{:.2f}", "GD2 xG": "{:.2f}",
        "goals/90": "{:.3f}", "assists/90": "{:.3f}",
        "xg90_club": "{:.3f}", "xg90_nt": "{:.3f}",
    }
    return s.format({k: v for k, v in fmt_map.items() if k in sub.columns}, na_rep="—")


# ── Greedy squad builder (must be defined before tabs) ───────────────────────
def _greedy_squad(df, budget, sort_col, country_cap):
    """
    Budget-aware greedy squad builder.
    Before selecting each player, reserves the minimum cost needed to fill
    all remaining position slots — guarantees all 15 slots are filled.
    """
    POS_ORDER = ["GK", "DEF", "MID", "FWD"]

    # Pre-compute cheapest possible cost to fill each position with n players
    min_pos_cost = {}
    for pos in POS_ORDER:
        cheapest = df[df["pos"] == pos].sort_values("price")["price"].tolist()
        n = SQUAD_SLOTS[pos]
        min_pos_cost[pos] = cheapest[:n] if len(cheapest) >= n else cheapest

    selected = []
    selected_ids = set()
    country_counts = {}
    rem = budget

    for i, pos in enumerate(POS_ORDER):
        n = SQUAD_SLOTS[pos]

        # Minimum budget needed for ALL positions that come after this one
        future_reserve = sum(
            sum(min_pos_cost[fp]) for fp in POS_ORDER[i + 1:]
        )

        cands = df[
            (df["pos"] == pos) & (~df["id"].isin(selected_ids))
        ].sort_values(sort_col, ascending=False)

        added = 0
        for _, r in cands.iterrows():
            if added >= n:
                break

            # Minimum cost to fill remaining slots in THIS position after this pick
            slots_left_here = n - added - 1
            if slots_left_here > 0:
                pool = df[
                    (df["pos"] == pos) & (~df["id"].isin(selected_ids | {r["id"]}))
                ].sort_values("price")["price"].tolist()
                pos_reserve = sum(pool[:slots_left_here]) if len(pool) >= slots_left_here else float("inf")
            else:
                pos_reserve = 0

            if r["price"] + pos_reserve + future_reserve > rem:
                continue
            if country_counts.get(r["team_code"], 0) >= country_cap:
                continue

            selected.append(r)
            selected_ids.add(r["id"])
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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏅 Rankings",
    "⚽ Club Form",
    "🌍 International Form",
    "🏗️ Squad Builder",
    "🔍 Scouts & Value",
    "📊 Fixtures & FDR",
])

# ── Shared filter helper ──────────────────────────────────────────────────────
def _filter(key_prefix: str) -> pd.DataFrame:
    c1, c2, c3, c4 = st.columns(4)
    pos_f    = c1.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key=f"{key_prefix}_pos")
    max_p    = c2.number_input("Max price ($m)", 4.0, 15.0, 12.0, 0.5, key=f"{key_prefix}_price")
    country  = c3.selectbox("Country", ["All"] + sorted(df["country"].unique()), key=f"{key_prefix}_ctry")
    sort_opt = c4.selectbox("Sort by", list(SORT_LABELS.keys()), key=f"{key_prefix}_sort")
    v = df.copy()
    if pos_f != "All":
        v = v[v["pos"] == pos_f]
    if country != "All":
        v = v[v["country"] == country]
    v = v[v["price"] <= max_p].sort_values(SORT_LABELS[sort_opt], ascending=False).reset_index(drop=True)
    v.index += 1
    return v


# ── TAB 1: Master Table ───────────────────────────────────────────────────────
with tab1:
    st.subheader("Player Rankings — Group Stage (MD1 + MD2)")

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2 = st.columns([3, 1])
    with f1:
        pos_filter = st.radio(
            "Position", ["All", "GK", "DEF", "MID", "FWD"],
            horizontal=True, key="t1_pos",
        )
    with f2:
        nation_filter = st.selectbox(
            "Nation", ["All"] + sorted(df["country"].unique().tolist()),
            key="t1_nation",
        )

    view = df.copy()
    if pos_filter != "All":
        view = view[view["pos"] == pos_filter]
    if nation_filter != "All":
        view = view[view["country"] == nation_filter]
    view = view.sort_values("xPts_GS", ascending=False).reset_index(drop=True)
    view.index += 1

    # ── Column group legend ───────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:12px;color:#aaa;padding:2px 0 6px'>"
        "🪪 <b>Identity</b> &nbsp;│&nbsp; "
        "🗓️ <b>Fixtures</b>: opponents &nbsp;│&nbsp; "
        "<span style='color:#4ade80'>⚽ <b>Club·</b> 2025/26 per-90 (league + cups)</span> &nbsp;│&nbsp; "
        "<span style='color:#60a5fa'>🌍 <b>NT·</b> recent NT form per-90</span> &nbsp;│&nbsp; "
        "📊 <b>MD· CS% / xG</b> from TEAM_PROJECTIONS &nbsp;│&nbsp; "
        "⏱️ <b>Proj Min</b>: predicted XI=70', bench=20' (else from starter rate) &nbsp;│&nbsp; "
        "<span style='color:#fb923c'>🎯 <b>Proj Pts</b></span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Build display dataframe with renamed columns ──────────────────────────
    COL_MAP = {
        # Identity
        "name":           "Name",
        "country":        "Nation",
        "pos":            "Pos",
        "club":           "Club",
        "price":          "Price",
        "own_%":          "Own%",
        "proj_min":       "Proj Min",
        # Fixtures
        "md1_opp":        "MD1 Opp",
        "md2_opp":        "MD2 Opp",
        # Club season stats
        "xg90_club":      "Cl Gls/90",
        "xa90_club":      "Cl Ast/90",
        "sot90_club":     "Cl SOT/90",
        "kp90_club":      "Cl KP/90",
        "tackles90_club": "Cl Tkl/90",
        # NT stats
        "xg90_nt":        "NT Gls/90",
        "xa90_nt":        "NT Ast/90",
        "sot90_nt":       "NT SOT/90",
        "kp90_nt":        "NT KP/90",
        "tackles90_nt":   "NT Tkl/90",
        # Fixture data
        "cs_md1_pct":     "MD1 CS%",
        "cs_md2_pct":     "MD2 CS%",
        "goals_md1":      "MD1 xG",
        "goals_md2":      "MD2 xG",
        # Output
        "md1_pts":        "MD1 Pts",
        "md2_pts":        "MD2 Pts",
        "xPts_GS":        "Total Pts",
    }

    display_cols = [c for c in COL_MAP if c in view.columns]
    disp = view[display_cols].rename(columns=COL_MAP)

    # Set Name as index so it stays frozen when scrolling right
    disp = disp.set_index("Name")

    per90_club = ["Cl Gls/90", "Cl Ast/90", "Cl SOT/90", "Cl KP/90", "Cl Tkl/90"]
    per90_nt   = ["NT Gls/90", "NT Ast/90", "NT SOT/90", "NT KP/90", "NT Tkl/90"]
    pts_cols   = ["MD1 Pts", "MD2 Pts", "Total Pts"]
    pct_cols   = [c for c in ["MD1 CS%", "MD2 CS%"] if c in disp.columns]
    xg_cols    = [c for c in ["MD1 xG", "MD2 xG"] if c in disp.columns]

    fmt_map = {"Price": "${:.1f}m", "Own%": "{:.1f}%", "Proj Min": "{:.0f}'"}
    fmt_map.update({c: "{:.2f}" for c in per90_club + per90_nt})
    fmt_map.update({c: "{:.2f}" for c in xg_cols})
    fmt_map.update({c: "{:.0%}" for c in pct_cols})
    fmt_map.update({c: "{:.1f}" for c in pts_cols})

    grad_pts  = [c for c in ["Total Pts", "MD1 Pts", "MD2 Pts"] if c in disp.columns and disp[c].notna().any()]
    grad_club = [c for c in per90_club if c in disp.columns and disp[c].notna().any()]
    grad_nt   = [c for c in per90_nt   if c in disp.columns and disp[c].notna().any()]

    styler = disp.style.format(
        {k: v for k, v in fmt_map.items() if k in disp.columns}, na_rep="—"
    )
    if grad_pts:
        styler = styler.background_gradient(subset=grad_pts,  cmap="YlOrRd")
    if grad_club:
        styler = styler.background_gradient(subset=grad_club, cmap="Greens")
    if grad_nt:
        styler = styler.background_gradient(subset=grad_nt,   cmap="Blues")

    try:
        st.dataframe(styler, use_container_width=True, height=620)
    except Exception:
        st.dataframe(disp, use_container_width=True, height=620)


# ── TAB 2: Club Form ──────────────────────────────────────────────────────────
with tab2:
    st.subheader("Club Form — 2025/26 Season Stats")
    st.caption("Per-90 stats from API-Football club season (league + continental + domestic cups aggregated). Used at 35% weight in model (65% if <5 NT apps).")
    view2 = _filter("cl")
    club_cols = ["name", "country", "club", "pos", "price",
                 "club_games", "club_minutes",
                 "xg90_club", "xa90_club", "sot90_club", "kp90_club", "tackles90_club",
                 "club_goals", "club_assists", "club_sot", "club_chances", "club_tackles",
                 "starter_rate"]
    st.dataframe(
        view2[club_cols].style
            .background_gradient(subset=["xg90_club", "xa90_club"], cmap="Greens")
            .format({
                "price": "${:.1f}m", "starter_rate": "{:.0%}",
                "club_games": "{:.0f}", "club_minutes": "{:.0f}",
                "club_goals": "{:.0f}", "club_assists": "{:.0f}",
                "club_sot": "{:.0f}", "club_chances": "{:.0f}", "club_tackles": "{:.0f}",
                "xg90_club": "{:.2f}", "xa90_club": "{:.2f}",
                "sot90_club": "{:.2f}", "kp90_club": "{:.2f}", "tackles90_club": "{:.2f}",
            }, na_rep="—"),
        use_container_width=True, height=580,
    )
    with st.expander("ℹ️ About Club Form data"):
        st.markdown("""
**Source**: 2025/26 club season stats from `data/stats.json` (run `fetch_player_stats.py` locally to refresh).

**What each column means**:
- `xg90_club` = goals/90 from club (proxy for xG/90 until FBRef scraper is added)
- `xa90_club` = assists/90 from club
- `sot90_club` = shots on target/90 (FWD relevance)
- `kp90_club` = key passes/90 (MID relevance)
- `tackles90_club` = tackles/90 (MID relevance)
        """)


# ── TAB 3: International Form ─────────────────────────────────────────────────
with tab3:
    st.subheader("International Form — Last 20 NT Matches")
    st.caption("Per-90 stats from API-Football international competitions (WC qualifiers, Nations League, friendlies). Used at 65% weight in model.")
    view3 = _filter("nt")
    nt_cols = ["name", "country", "club", "pos", "price",
               "intl_games", "intl_minutes",
               "xg90_nt", "xa90_nt", "sot90_nt", "kp90_nt", "tackles90_nt",
               "intl_goals", "intl_assists", "intl_sot", "intl_chances", "intl_tackles",
               "nt_weight"]
    st.dataframe(
        view3[nt_cols].style
            .background_gradient(subset=["xg90_nt", "xa90_nt"], cmap="Blues")
            .format({
                "price": "${:.1f}m",
                "intl_games": "{:.0f}", "intl_minutes": "{:.0f}",
                "intl_goals": "{:.0f}", "intl_assists": "{:.0f}",
                "intl_sot": "{:.0f}", "intl_chances": "{:.0f}", "intl_tackles": "{:.0f}",
                "xg90_nt": "{:.2f}", "xa90_nt": "{:.2f}",
                "sot90_nt": "{:.2f}", "kp90_nt": "{:.2f}", "tackles90_nt": "{:.2f}",
            }, na_rep="—"),
        use_container_width=True, height=580,
    )
    with st.expander("ℹ️ About International Form data"):
        st.markdown("""
**Source**: API-Football, international competitions:
- WC 2026 (live from June 11)
- UEFA Nations League 2024/25
- WC Qualifying (all confederations, 2024–2025)

**NT weight**: `65% NT` = 5+ international appearances → NT data is trusted.
`35% NT` = fewer than 5 apps → club form is the primary signal.

**Clean sheets** are particularly important for **GK** and **DEF** —
CS probability from FPLJoe bookie markets overrides historical CS rate in the model.
        """)

    st.subheader("Country Deep Dive")
    sel_country = st.selectbox("Select country", sorted(TEAM_NAMES.values()), key="nt_country_drill")
    sel_code = next((c for c, n in TEAM_NAMES.items() if n == sel_country), None)
    if sel_code:
        cp = df[df["team_code"] == sel_code].sort_values("xPts_GS", ascending=False)
        cp.index = range(1, len(cp) + 1)
        if cp.empty:
            st.info("No players loaded for this country.")
        else:
            st.dataframe(
                fmt(cp[["name", "pos", "club", "price", "own_%",
                         "GD1 xG", "GD2 xG", "xPts_GS",
                         "xg90_nt", "xa90_nt", "xg90_club", "xa90_club",
                         "intl_games", "club_games", "nt_weight", "value"]]),
                use_container_width=True,
            )


# ── TAB 4: Squad Builder ──────────────────────────────────────────────────────
with tab4:
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
                          "GD1 xG", "GD2 xG", "xPts_GS", "value"]
            st.dataframe(fmt(squad[squad_cols]), use_container_width=True)

            for pos in ["GK", "DEF", "MID", "FWD"]:
                sub = squad[squad["pos"] == pos]
                line = "  |  ".join(
                    f"{r['name']} ${r['price']:.1f}m ({r['xPts_GS']:.1f} xPts)"
                    for _, r in sub.iterrows()
                )
                st.markdown(f"**{pos}:** {line}")


# ── TAB 5: Scouts & Value ─────────────────────────────────────────────────────
with tab5:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader(f"🔍 Scout Picks  (<{int(SCOUT_OWNERSHIP_THRESHOLD)}% owned)")
        scouts = df[df["scout"]].sort_values("xPts/game", ascending=False)
        pos_s = st.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="scout_pos")
        if pos_s != "All":
            scouts = scouts[scouts["pos"] == pos_s]
        scouts.index = range(1, len(scouts) + 1)
        st.dataframe(
            scouts[["name", "pos", "country", "club", "price", "own_%",
                     "GD1 xG", "GD2 xG", "xPts_GS", "value"]].style
                .background_gradient(subset=["xPts_GS"], cmap="Reds")
                .format({"price": "${:.1f}m", "own_%": "{:.1f}%",
                         "GD1 xG": "{:.3f}", "GD2 xG": "{:.3f}",
                         "xPts_GS": "{:.2f}", "value": "{:.3f}"}),
            use_container_width=True, height=420,
        )

    with c2:
        st.subheader("💰 Best Value (xPts GS / $m)")
        pos_v = st.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="val_pos")
        max_pv = st.number_input("Max price", 4.0, 15.0, 12.0, 0.5, key="val_price")
        val_view = df[df["price"] <= max_pv].copy()
        if pos_v != "All":
            val_view = val_view[val_view["pos"] == pos_v]
        val_view = val_view.sort_values("value", ascending=False).head(20).reset_index(drop=True)
        val_view.index += 1
        st.dataframe(
            val_view[["name", "pos", "country", "club", "price", "own_%",
                       "GD1 xG", "GD2 xG", "xPts_GS", "value"]].style
                .background_gradient(subset=["value"], cmap="Blues")
                .format({"price": "${:.1f}m", "own_%": "{:.1f}%",
                         "GD1 xG": "{:.3f}", "GD2 xG": "{:.3f}",
                         "xPts_GS": "{:.2f}", "value": "{:.3f}"}),
            use_container_width=True, height=420,
        )


# ── TAB 6: Fixtures & FDR ─────────────────────────────────────────────────────
with tab6:
    st.subheader("Group Stage Fixtures — CS% & Projected Goals")
    st.caption("CS% and xG from FPLJoe.com SBOBET/Betfair bookie markets (27.05.26). CS% directly drives DEF/GK clean sheet points in model.")

    fdr_rows = []
    for code, name in sorted(TEAM_NAMES.items(), key=lambda x: get_team_fdr_total(x[0])):
        fdr_vals  = FDR.get(code, [3, 3, 3])
        cs_vals   = CS_PCT.get(code, [0.3, 0.3, 0.3])
        g_vals    = PROJ_GOALS.get(code, [1.0, 1.0, 1.0])
        fixtures  = FIXTURES.get(code, ["?", "?", "?"])
        fdr_rows.append({
            "Country": name,
            "MD1 vs":  TEAM_NAMES.get(fixtures[0], "?") if fixtures else "?",
            "FDR1": fdr_vals[0],
            "CS%1": f"{int(cs_vals[0]*100)}%",
            "xG1":  g_vals[0],
            "MD2 vs":  TEAM_NAMES.get(fixtures[1], "?") if len(fixtures) > 1 else "?",
            "FDR2": fdr_vals[1],
            "CS%2": f"{int(cs_vals[1]*100)}%",
            "xG2":  g_vals[1],
            "MD3 vs":  TEAM_NAMES.get(fixtures[2], "?") if len(fixtures) > 2 else "?",
            "FDR3": fdr_vals[2],
            "CS%3": f"{int(cs_vals[2]*100)}%",
            "xG3":  g_vals[2],
            "Total FDR": sum(fdr_vals),
            "Avg CS%": f"{int(sum(cs_vals)/3*100)}%",
        })

    fdr_df = pd.DataFrame(fdr_rows).sort_values("Total FDR")

    def color_fdr(val):
        return {
            1: "background-color:#1a7a1a;color:white",
            2: "background-color:#5cb85c;color:white",
            3: "background-color:#f0ad4e;color:black",
            4: "background-color:#d9534f;color:white",
            5: "background-color:#8b0000;color:white",
        }.get(val, "")

    styler = fdr_df.style
    try:
        styler = styler.map(color_fdr, subset=["FDR1", "FDR2", "FDR3"])
    except AttributeError:
        styler = styler.applymap(color_fdr, subset=["FDR1", "FDR2", "FDR3"])
    st.dataframe(styler, use_container_width=True, height=640)

st.divider()
st.caption("Scoring: Official FIFA WC Fantasy 2026 | Model: xG ratio share × team projection | Weights: 65% NT / 35% club | CS% & xG: FPLJoe.com bookie markets (SBOBET/Betfair)")
