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

# ── KPI strip (rendered after the rankings table — see tab1 below) ────────────

st.divider()

# ── Helper for display ────────────────────────────────────────────────────────
SORT_LABELS = {
    "xPts group stage total": "xPts_GS",
    "xPts per game": "xPts/game",
    "Value (xPts/$m)": "value",
    "Ownership %": "own_%",
    "Price": "price",
}

def _fdr_color(val) -> str:
    """Continuous FDR coloring: 1.0 (easiest, dark green) → 5.0 (hardest, dark red)."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    v = max(1.0, min(5.0, v))
    stops = [
        (0x1a, 0x7a, 0x1a),  # 1: dark green
        (0x5c, 0xb8, 0x5c),  # 2: lime green
        (0xf0, 0xad, 0x4e),  # 3: orange
        (0xd9, 0x53, 0x4f),  # 4: red
        (0x8b, 0x00, 0x00),  # 5: dark red
    ]
    lo = min(int(v - 1), 3)
    hi = lo + 1
    t = v - 1.0 - lo
    r = int(stops[lo][0] + t * (stops[hi][0] - stops[lo][0]))
    g = int(stops[lo][1] + t * (stops[hi][1] - stops[lo][1]))
    b = int(stops[lo][2] + t * (stops[hi][2] - stops[lo][2]))
    fg = "white" if (0.299 * r + 0.587 * g + 0.114 * b) < 160 else "black"
    return f"background-color: rgb({r},{g},{b}); color: {fg}"


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


# ── Scout bonus (display-only, +2 per MD where own%<4.5 AND md_pts≥4) ────────
def _with_scout_bonus(view: pd.DataFrame) -> pd.DataFrame:
    v = view.copy()
    low_own = v["own_%"] < 4.5
    v["sb_md1"]      = ((low_own) & (v["md1_pts"] >= 4.0)).astype(int) * 2
    v["sb_md2"]      = ((low_own) & (v["md2_pts"] >= 4.0)).astype(int) * 2
    v["scout_bonus"] = v["sb_md1"] + v["sb_md2"]
    v["adj_md1"]     = v["md1_pts"]  + v["sb_md1"]
    v["adj_md2"]     = v["md2_pts"]  + v["sb_md2"]
    v["adj_total"]   = v["xPts_GS"] + v["scout_bonus"]
    return v.drop(columns=["sb_md1", "sb_md2"])


# ── Greedy squad builder (must be defined before tabs) ───────────────────────
def _greedy_squad(df, budget, sort_col, country_cap, max_gk_per_country=1):
    """
    Global greedy squad builder — sorts ALL players by sort_col together,
    picks across positions simultaneously. Budget reservation prevents
    running out of money for unfilled slots in any position.

    GKs are capped at max_gk_per_country (default 1) so the two keepers come
    from different nations — this lets you bench one and start the other based
    on which nation has the kinder fixture each matchday.
    """
    pos_filled = {p: 0 for p in SQUAD_SLOTS}
    selected = []
    selected_ids: set = set()
    country_counts: dict = {}
    gk_countries: set = set()
    rem = budget

    def _min_reserve(excl_ids, filled, gk_used):
        total = 0.0
        for p, slots in SQUAD_SLOTS.items():
            still_need = slots - filled[p]
            if still_need <= 0:
                continue
            pool = df[(df["pos"] == p) & (~df["id"].isin(excl_ids))].sort_values("price")
            if p == "GK":
                # cheapest GKs from distinct, not-yet-used nations
                seen = set(gk_used)
                prices = []
                for _, row in pool.iterrows():
                    if row["team_code"] in seen:
                        continue
                    seen.add(row["team_code"])
                    prices.append(row["price"])
                    if len(prices) == still_need:
                        break
            else:
                prices = pool["price"].tolist()[:still_need]
            if len(prices) < still_need:
                return float("inf")
            total += sum(prices)
        return total

    for _, r in df.sort_values(sort_col, ascending=False).iterrows():
        if sum(pos_filled.values()) == sum(SQUAD_SLOTS.values()):
            break
        pos = r["pos"]
        if pos_filled[pos] >= SQUAD_SLOTS[pos]:
            continue
        if r["id"] in selected_ids:
            continue
        if country_counts.get(r["team_code"], 0) >= country_cap:
            continue
        if pos == "GK" and r["team_code"] in gk_countries:
            continue
        tentative_ids = selected_ids | {r["id"]}
        tentative_filled = {**pos_filled, pos: pos_filled[pos] + 1}
        tentative_gk = gk_countries | ({r["team_code"]} if pos == "GK" else set())
        reserve = _min_reserve(tentative_ids, tentative_filled, tentative_gk)
        if r["price"] + reserve > rem:
            continue
        selected.append(r)
        selected_ids.add(r["id"])
        rem -= r["price"]
        country_counts[r["team_code"]] = country_counts.get(r["team_code"], 0) + 1
        if pos == "GK":
            gk_countries.add(r["team_code"])
        pos_filled[pos] += 1

    if not selected:
        return None
    result = pd.DataFrame(selected)
    pos_order = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
    result["_o"] = result["pos"].map(pos_order)
    return result.sort_values(["_o", sort_col], ascending=[True, False]).drop(columns=["_o"]).reset_index(drop=True)


def _dual_squad(df, budget, country_cap):
    """Build best xPts_GS squad, then make 2 transfers to maximise MD2, return (md1, md2)."""
    md1 = _greedy_squad(df, budget, "xPts_GS", country_cap)
    if md1 is None or md1.empty:
        return None, None

    worst2 = md1.nsmallest(2, "md2_pts")
    keep13 = md1[~md1["id"].isin(worst2["id"])].copy()
    freed  = worst2["price"].sum()
    keep_country = keep13["team_code"].value_counts().to_dict()
    used_ids = set(keep13["id"])

    transfers, remaining = [], freed
    for _, sold in worst2.sort_values("md2_pts").iterrows():
        n_left  = 2 - len(transfers) - 1
        min_res = n_left * 4.0
        cur_cnt = {**keep_country}
        for p in transfers:
            cur_cnt[p["team_code"]] = cur_cnt.get(p["team_code"], 0) + 1

        pool = df[
            (df["pos"] == sold["pos"]) &
            (~df["id"].isin(used_ids)) &
            (df["price"] <= remaining - min_res) &
            (df["team_code"].apply(lambda tc: cur_cnt.get(tc, 0) < country_cap))
        ]
        if sold["pos"] == "GK":
            # don't end up with both keepers from the same nation
            gk_nat = set(keep13[keep13["pos"] == "GK"]["team_code"])
            gk_nat |= {t["team_code"] for t in transfers if t["pos"] == "GK"}
            pool = pool[~pool["team_code"].isin(gk_nat)]
        pool = pool.sort_values("md2_pts", ascending=False)

        picked = pool.iloc[0] if not pool.empty else sold
        transfers.append(picked)
        used_ids.add(picked["id"])
        remaining -= picked["price"]

    md2 = pd.concat([keep13, pd.DataFrame(transfers)]).reset_index(drop=True)
    pos_order = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}
    md2["_o"] = md2["pos"].map(pos_order)
    md2 = md2.sort_values(["_o", "md2_pts"], ascending=[True, False]).drop(columns=["_o"]).reset_index(drop=True)
    return md1, md2


def _pin_name(df: pd.DataFrame, name_col: str, team_col: str = None) -> pd.DataFrame:
    """Set name_col as the index (pinned in Streamlit), deduplicating with (TEAM) suffix."""
    out = df.copy()
    if out[name_col].duplicated().any():
        seen: set = set()
        names = []
        for _, r in out.iterrows():
            n = r[name_col]
            if n in seen and team_col and team_col in out.columns:
                names.append(f"{n} ({r[team_col]})")
            else:
                names.append(n)
                seen.add(n)
        out[name_col] = names
    return out.set_index(name_col)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏅 Rankings",
    "⚽ Club Form",
    "🌍 International Form",
    "🏗️ Squad Builder",
    "🔍 Scouts & Value",
    "📊 Fixtures & FDR",
    "🎯 Draft",
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

    f1, f2 = st.columns([3, 1])
    with f1:
        pos_filter = st.radio("Position", ["All", "GK", "DEF", "MID", "FWD"], horizontal=True, key="t1_pos")
    with f2:
        nation_filter = st.selectbox("Nation", ["All"] + sorted(df["country"].unique().tolist()), key="t1_nation")

    view = df.copy()
    if pos_filter != "All":
        view = view[view["pos"] == pos_filter]
    if nation_filter != "All":
        view = view[view["country"] == nation_filter]
    view = _with_scout_bonus(view.sort_values("xPts_GS", ascending=False).reset_index(drop=True))
    view.index += 1

    st.markdown(
        "<div style='font-size:12px;color:#aaa;padding:2px 0 6px'>"
        "🪪 Identity &nbsp;│&nbsp; 🗓️ Opponents (3-letter) &nbsp;│&nbsp; "
        "<span style='color:#4ade80'>🎯 Proj Pts → Adj Pts (+2 scout bonus if &lt;4.5% owned &amp; ≥4 pts)</span> &nbsp;│&nbsp; "
        "📊 CS% / xG &nbsp;│&nbsp; "
        "<span style='color:#4ade80'>⚽ Club·</span> <span style='color:#60a5fa'>🌍 NT· per-90</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    COL_MAP = {
        "name":           "Name",
        "team_code":      "Nation",
        "pos":            "Pos",
        "price":          "Price",
        "md1_opp":        "MD1 Opp",
        "md2_opp":        "MD2 Opp",
        "own_%":          "Own%",
        "md1_pts":        "MD1 Pts",
        "md2_pts":        "MD2 Pts",
        "xPts_GS":        "Total Pts",
        "adj_total":      "Adj Pts",
        "cs_md1_pct":     "MD1 CS%",
        "cs_md2_pct":     "MD2 CS%",
        "goals_md1":      "MD1 xG",
        "goals_md2":      "MD2 xG",
        "xg90_club":      "Cl Gls/90",
        "xa90_club":      "Cl Ast/90",
        "sot90_club":     "Cl SOT/90",
        "kp90_club":      "Cl KP/90",
        "tackles90_club": "Cl Tkl/90",
        "xg90_nt":        "NT Gls/90",
        "xa90_nt":        "NT Ast/90",
        "sot90_nt":       "NT SOT/90",
        "kp90_nt":        "NT KP/90",
        "tackles90_nt":   "NT Tkl/90",
        "proj_min":       "Proj Min",
        "set_pieces":     "Set Pcs",
    }

    display_cols = [c for c in COL_MAP if c in view.columns]
    # Keep Name as a column (not the index): duplicate player names — e.g. two
    # "Emiliano Martínez" — make the index non-unique, which breaks
    # Styler.background_gradient (it uses .apply, which requires a unique index).
    disp = view[display_cols].rename(columns=COL_MAP).reset_index(drop=True)

    per90_club = ["Cl Gls/90", "Cl Ast/90", "Cl SOT/90", "Cl KP/90", "Cl Tkl/90"]
    per90_nt   = ["NT Gls/90", "NT Ast/90", "NT SOT/90", "NT KP/90", "NT Tkl/90"]
    pts_cols   = ["MD1 Pts", "MD2 Pts", "Total Pts", "Adj Pts"]
    pct_cols   = [c for c in ["MD1 CS%", "MD2 CS%"] if c in disp.columns]
    xg_cols    = [c for c in ["MD1 xG", "MD2 xG"] if c in disp.columns]

    fmt_map = {"Price": "${:.1f}m", "Own%": "{:.1f}%", "Proj Min": "{:.0f}'"}
    fmt_map.update({c: "{:.2f}" for c in per90_club + per90_nt})
    fmt_map.update({c: "{:.2f}" for c in xg_cols})
    fmt_map.update({c: "{:.0%}" for c in pct_cols})
    fmt_map.update({c: "{:.1f}" for c in pts_cols})

    # Threshold-based bonus highlighting — blue palette, three distinct shades.
    #   MID  KP/90 ≥ 3.0  → blue-700   (chances created bonus)
    #   MID  Tkl/90 ≥ 3.0 → sky-700    (tackles bonus)
    #   FWD  SOT/90 ≥ 2.0 → indigo-700 (shots on target bonus)
    BONUS_KP  = "background-color: #1d4ed8; color: #dbeafe"   # MID KP  (blue)
    BONUS_TKL = "background-color: #0369a1; color: #bae6fd"   # MID Tkl (sky)
    BONUS_SOT = "background-color: #4338ca; color: #e0e7ff"   # FWD SOT (indigo)

    def _bonus_style(row):
        styles = [""] * len(row)
        idx = list(row.index)
        pos = row.get("Pos", "")

        def _hi(col, style):
            if col in idx:
                styles[idx.index(col)] = style

        if pos == "MID":
            for c in ["Cl KP/90", "NT KP/90"]:
                if c in idx and isinstance(row[c], (int, float)) and row[c] >= 3.0:
                    _hi(c, BONUS_KP)
            for c in ["Cl Tkl/90", "NT Tkl/90"]:
                if c in idx and isinstance(row[c], (int, float)) and row[c] >= 3.0:
                    _hi(c, BONUS_TKL)
        elif pos == "FWD":
            for c in ["Cl SOT/90", "NT SOT/90"]:
                if c in idx and isinstance(row[c], (int, float)) and row[c] >= 2.0:
                    _hi(c, BONUS_SOT)
        elif pos == "GK":
            pass  # save_rate not exposed as per-90 in rankings table

        return styles

    def _opp_fdr_style(row):
        styles = [""] * len(row)
        idx = list(row.index)
        nation = row.get("Nation", "")
        fdr_vals = FDR.get(nation, [3, 3, 3])
        for col, fdr_val in [("MD1 Opp", fdr_vals[0]), ("MD2 Opp", fdr_vals[1])]:
            if col in idx:
                styles[idx.index(col)] = _fdr_color(fdr_val)
        return styles

    # Name as index → Streamlit pins the index column, making Name sticky.
    # _pin_name deduplicates (required: pandas Styler.apply needs unique index).
    disp_idx = _pin_name(disp, "Name", "Nation")
    styler = (
        disp_idx.style
        .format({k: v for k, v in fmt_map.items() if k in disp_idx.columns}, na_rep="—")
        .apply(_bonus_style, axis=1)
        .apply(_opp_fdr_style, axis=1)
    )
    if pct_cols:
        for c in pct_cols:
            styler = styler.background_gradient(subset=[c], cmap="Greens")
    if xg_cols:
        for c in xg_cols:
            styler = styler.background_gradient(subset=[c], cmap="Oranges")

    st.dataframe(styler, use_container_width=True, height=620)

    st.divider()
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Players", len(df))
    k2.metric("Countries", df["country"].nunique())
    k3.metric("Scout candidates", int(df["scout"].sum()))
    best = df.iloc[0]
    k4.metric("Top xPts/game", f"{best['xPts/game']:.2f}  —  {best['name']}")
    k5.metric("Best value", f"{df.sort_values('value', ascending=False).iloc[0]['name']}")


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
        _pin_name(view2[club_cols], "name", "country").style
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
        _pin_name(view3[nt_cols], "name", "country").style
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
            _cp_cols = ["name", "pos", "club", "price", "own_%",
                        "GD1 xG", "GD2 xG", "xPts_GS",
                        "xg90_nt", "xa90_nt", "xg90_club", "xa90_club",
                        "intl_games", "club_games", "nt_weight", "value"]
            st.dataframe(
                fmt(_pin_name(cp[_cp_cols], "name")),
                use_container_width=True,
            )


# ── TAB 4: Squad Builder ──────────────────────────────────────────────────────
with tab4:
    st.subheader("Build Your Best Squad")

    b1, b2, b3, b4 = st.columns(4)
    build_budget  = b1.number_input("Budget ($m)", 50.0, 120.0, budget, 0.5, key="build_b")
    build_cap     = b2.slider("Max per country", 1, 5, country_cap, key="build_cap")
    use_transfers = b3.toggle("2 transfers MD1→MD2", value=False, key="build_transfers")
    exclude_mex   = b4.toggle("Exclude MEX", value=True, key="build_excl_mex")

    if st.button("Build Optimal Squad", type="primary"):
        build_df = df[df["team_code"] != "MEX"].copy() if exclude_mex else df.copy()
        if use_transfers:
            md1_squad, md2_squad = _dual_squad(build_df, build_budget, build_cap)
            if md1_squad is None:
                st.error("Could not build squad within budget. Try increasing budget or country cap.")
            else:
                md1_pts_total = md1_squad["md1_pts"].sum()
                md2_pts_total = md2_squad["md2_pts"].sum()
                combined      = md1_pts_total + md2_pts_total
                cost          = md1_squad["price"].sum()

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("Cost (MD1 squad)", f"${cost:.1f}m")
                sc2.metric("MD1 xPts", f"{md1_pts_total:.1f}")
                sc3.metric("MD2 xPts", f"{md2_pts_total:.1f}")
                sc4.metric("Combined xPts", f"{combined:.1f}")

                # Show transfers
                sold_ids = set(md1_squad["id"]) - set(md2_squad["id"])
                bought_ids = set(md2_squad["id"]) - set(md1_squad["id"])
                if sold_ids:
                    out_names = md1_squad[md1_squad["id"].isin(sold_ids)]["name"].tolist()
                    in_names  = md2_squad[md2_squad["id"].isin(bought_ids)]["name"].tolist()
                    st.info(f"**2 transfers:** OUT {', '.join(out_names)}  →  IN {', '.join(in_names)}")

                sq_cols = ["name", "team_code", "pos", "price", "md1_pts", "md2_pts", "xPts_GS"]
                sq_cols = [c for c in sq_cols if c in md1_squad.columns]

                st.markdown("**MD1 Squad (15 players)**")
                st.dataframe(
                    _pin_name(md1_squad[sq_cols].rename(columns={
                        "name": "Name", "team_code": "Nation", "pos": "Pos",
                        "price": "Price", "md1_pts": "MD1 Pts",
                        "md2_pts": "MD2 Pts", "xPts_GS": "Total Pts"
                    }), "Name", "Nation").style.format({"Price": "${:.1f}m", "MD1 Pts": "{:.1f}",
                                     "MD2 Pts": "{:.1f}", "Total Pts": "{:.1f}"}, na_rep="—"),
                    use_container_width=True,
                )
                st.markdown("**MD2 Squad (after 2 transfers)**")
                sq2_cols = [c for c in sq_cols if c in md2_squad.columns]
                st.dataframe(
                    _pin_name(md2_squad[sq2_cols].rename(columns={
                        "name": "Name", "team_code": "Nation", "pos": "Pos",
                        "price": "Price", "md1_pts": "MD1 Pts",
                        "md2_pts": "MD2 Pts", "xPts_GS": "Total Pts"
                    }), "Name", "Nation").style.format({"Price": "${:.1f}m", "MD1 Pts": "{:.1f}",
                                     "MD2 Pts": "{:.1f}", "Total Pts": "{:.1f}"}, na_rep="—"),
                    use_container_width=True,
                )
        else:
            squad = _greedy_squad(build_df, build_budget, "xPts_GS", build_cap)
            if squad is None or squad.empty:
                st.error("Could not fill squad within budget. Try increasing budget or country cap.")
            else:
                cost          = squad["price"].sum()
                md1_total     = squad["md1_pts"].sum()
                md2_total     = squad["md2_pts"].sum()
                total_xpts    = squad["xPts_GS"].sum()

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("Total cost",   f"${cost:.1f}m")
                sc2.metric("Remaining",    f"${build_budget - cost:.1f}m")
                sc3.metric("MD1 xPts",     f"{md1_total:.1f}")
                sc4.metric("MD2 xPts",     f"{md2_total:.1f}")

                captain = squad.sort_values("xPts/game", ascending=False).iloc[0]
                vice    = squad.sort_values("xPts/game", ascending=False).iloc[1]
                st.success(f"⭐ Captain: **{captain['name']}**  |  👑 Vice: **{vice['name']}**")

                sq_cols = ["name", "team_code", "pos", "price", "own_%", "md1_pts", "md2_pts", "xPts_GS"]
                sq_cols = [c for c in sq_cols if c in squad.columns]
                st.dataframe(
                    _pin_name(squad[sq_cols].rename(columns={
                        "name": "Name", "team_code": "Nation", "pos": "Pos",
                        "price": "Price", "own_%": "Own%",
                        "md1_pts": "MD1 Pts", "md2_pts": "MD2 Pts", "xPts_GS": "Total Pts",
                    }), "Name", "Nation").style.format({
                        "Price": "${:.1f}m", "Own%": "{:.1f}%",
                        "MD1 Pts": "{:.1f}", "MD2 Pts": "{:.1f}", "Total Pts": "{:.1f}",
                    }, na_rep="—"),
                    use_container_width=True,
                )

                for pos in ["GK", "DEF", "MID", "FWD"]:
                    sub = squad[squad["pos"] == pos]
                    line = "  |  ".join(
                        f"{r['name']} ${r['price']:.1f}m (MD1 {r['md1_pts']:.1f} / MD2 {r['md2_pts']:.1f})"
                        for _, r in sub.iterrows()
                    )
                    st.markdown(f"**{pos}:** {line}")


# ── TAB 5: Scouts & Value ─────────────────────────────────────────────────────
with tab5:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader(f"🔍 Scout Picks  (<{SCOUT_OWNERSHIP_THRESHOLD}% owned, ≥{SCOUT_POINTS_THRESHOLD} pts/game)")
        scouts = _with_scout_bonus(df[df["scout"]].sort_values("xPts/game", ascending=False).copy())
        pos_s = st.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="scout_pos")
        if pos_s != "All":
            scouts = scouts[scouts["pos"] == pos_s]
        scouts = scouts.reset_index(drop=True)
        scouts.index = range(1, len(scouts) + 1)

        s_cols = ["name", "team_code", "pos", "price", "own_%",
                  "md1_opp", "md2_opp",
                  "cs_md1_pct", "cs_md2_pct", "goals_md1", "goals_md2",
                  "md1_pts", "md2_pts", "xPts_GS", "scout_bonus", "adj_total", "value"]
        s_cols = [c for c in s_cols if c in scouts.columns]
        s_disp = scouts[s_cols].rename(columns={
            "name": "Name", "team_code": "Nation", "pos": "Pos",
            "price": "Price", "own_%": "Own%",
            "md1_opp": "MD1 Opp", "md2_opp": "MD2 Opp",
            "cs_md1_pct": "MD1 CS%", "cs_md2_pct": "MD2 CS%",
            "goals_md1": "MD1 xG", "goals_md2": "MD2 xG",
            "md1_pts": "MD1 Pts", "md2_pts": "MD2 Pts",
            "xPts_GS": "Total Pts", "scout_bonus": "Scout+", "adj_total": "Adj Pts",
            "value": "Value",
        }).reset_index(drop=True)

        s_fmt = {"Price": "${:.1f}m", "Own%": "{:.1f}%",
                 "MD1 CS%": "{:.0%}", "MD2 CS%": "{:.0%}",
                 "MD1 xG": "{:.2f}", "MD2 xG": "{:.2f}",
                 "MD1 Pts": "{:.1f}", "MD2 Pts": "{:.1f}",
                 "Total Pts": "{:.1f}", "Scout+": "{:.0f}", "Adj Pts": "{:.1f}",
                 "Value": "{:.3f}"}
        s_grad = [c for c in ["MD1 Pts", "MD2 Pts", "Adj Pts"] if c in s_disp.columns and s_disp[c].dropna().nunique() >= 2]
        s_disp_idx = _pin_name(s_disp, "Name", "Nation")
        s_styler = s_disp_idx.style.format({k: v for k, v in s_fmt.items() if k in s_disp_idx.columns}, na_rep="—")
        if s_grad:
            s_styler = s_styler.background_gradient(subset=s_grad, cmap="Greens")
        st.dataframe(s_styler, use_container_width=True, height=480)

    with c2:
        st.subheader("💰 Best Value (Adj Pts / $m)")
        pos_v  = st.selectbox("Position", ["All", "GK", "DEF", "MID", "FWD"], key="val_pos")
        max_pv = st.number_input("Max price", 4.0, 15.0, 12.0, 0.5, key="val_price")
        val_view = _with_scout_bonus(df[df["price"] <= max_pv].copy())
        if pos_v != "All":
            val_view = val_view[val_view["pos"] == pos_v]
        val_view["adj_value"] = (val_view["adj_total"] / val_view["price"].replace(0, float("nan"))).round(3)
        val_view = val_view.sort_values("adj_value", ascending=False).head(20).reset_index(drop=True)
        val_view.index += 1

        v_cols = ["name", "team_code", "price", "adj_total", "adj_value",
                  "md1_opp", "md2_opp", "md1_pts", "md2_pts"]
        v_cols = [c for c in v_cols if c in val_view.columns]
        v_disp = val_view[v_cols].rename(columns={
            "name": "Name", "team_code": "Nation",
            "price": "Price", "adj_total": "Adj Pts", "adj_value": "Value",
            "md1_opp": "MD1 Opp", "md2_opp": "MD2 Opp",
            "md1_pts": "MD1 Pts", "md2_pts": "MD2 Pts",
        }).reset_index(drop=True)

        v_fmt = {"Price": "${:.1f}m", "Adj Pts": "{:.1f}", "Value": "{:.3f}",
                 "MD1 Pts": "{:.1f}", "MD2 Pts": "{:.1f}"}
        v_grad = [c for c in ["Adj Pts", "Value"] if c in v_disp.columns and v_disp[c].dropna().nunique() >= 2]
        v_disp_idx = _pin_name(v_disp, "Name", "Nation")
        v_styler = v_disp_idx.style.format({k: v for k, v in v_fmt.items() if k in v_disp_idx.columns}, na_rep="—")
        if v_grad:
            v_styler = v_styler.background_gradient(subset=v_grad, cmap="Blues")
        st.dataframe(v_styler, use_container_width=True, height=480)


# ── TAB 6: Fixtures & FDR ─────────────────────────────────────────────────────
with tab6:
    st.subheader("Group Stage Fixtures — CS% & Projected Goals")
    st.caption("CS% and xG from FPLJoe.com SBOBET/Betfair bookie markets (02.06.26). CS% directly drives DEF/GK clean sheet points in model.")

    md_show = st.radio("Show matchdays", [1, 2, 3], index=2, horizontal=True, key="t6_mds",
                       format_func=lambda x: f"MD1 only" if x == 1 else f"MD1–MD{x}")

    fdr_rows = []
    for code, name in sorted(TEAM_NAMES.items(), key=lambda x: get_team_fdr_total(x[0])):
        fdr_vals  = FDR.get(code, [3, 3, 3])
        cs_vals   = CS_PCT.get(code, [0.3, 0.3, 0.3])
        g_vals    = PROJ_GOALS.get(code, [1.0, 1.0, 1.0])
        fixtures  = FIXTURES.get(code, ["?", "?", "?"])
        row = {"Country": name}
        for i in range(md_show):
            row[f"MD{i+1} vs"] = fixtures[i] if len(fixtures) > i else "?"
            row[f"FDR{i+1}"]   = fdr_vals[i]
            row[f"CS%{i+1}"]   = cs_vals[i]
            row[f"xG{i+1}"]    = g_vals[i]
        row["Total FDR"] = sum(fdr_vals[:md_show])
        row["Avg CS%"]   = sum(cs_vals[:md_show]) / md_show
        row["Avg xG"]    = sum(g_vals[:md_show])  / md_show
        fdr_rows.append(row)

    fdr_df = pd.DataFrame(fdr_rows).sort_values("Total FDR").set_index("Country")

    cs_cols6  = [c for c in [f"CS%{i}" for i in range(1, md_show+1)]  if c in fdr_df.columns]
    xg_cols6  = [c for c in [f"xG{i}"  for i in range(1, md_show+1)]  if c in fdr_df.columns]
    fdr_cols6 = [c for c in [f"FDR{i}" for i in range(1, md_show+1)]  if c in fdr_df.columns]

    styler = fdr_df.style
    try:
        styler = styler.map(_fdr_color, subset=fdr_cols6)
    except AttributeError:
        styler = styler.applymap(_fdr_color, subset=fdr_cols6)
    for c in cs_cols6:
        styler = styler.background_gradient(subset=[c], cmap="Greens")
    for c in xg_cols6:
        styler = styler.background_gradient(subset=[c], cmap="Oranges")

    fmt6 = {}
    fmt6.update({c: "{:.0%}" for c in cs_cols6})
    fmt6.update({c: "{:.2f}" for c in xg_cols6})
    if "Avg CS%" in fdr_df.columns:
        fmt6["Avg CS%"] = "{:.0%}"
    if "Avg xG" in fdr_df.columns:
        fmt6["Avg xG"] = "{:.2f}"
        styler = styler.background_gradient(subset=["Avg xG"], cmap="Oranges")
    if "Avg CS%" in fdr_df.columns:
        styler = styler.background_gradient(subset=["Avg CS%"], cmap="Greens")
    styler = styler.format(fmt6, na_rep="—")

    st.dataframe(styler, use_container_width=True, height=640)


# ── TAB 7: Draft ──────────────────────────────────────────────────────────────
with tab7:
    from data.predicted_lineups import PREDICTED_XI
    st.subheader("Draft Mode — Top 200 Players")
    st.caption("Only nations with a predicted XI are included — teams without one are unlikely to advance past the group stage.")

    draft_nations = set(PREDICTED_XI.keys())

    d_pos = st.radio("Position", ["All", "GK", "DEF", "MID", "FWD"], horizontal=True, key="t7_pos")

    draft_all = df[df["country"].isin(draft_nations)].copy()

    # Derive MD3 pts and opponent from the total
    draft_all["md3_pts"] = draft_all["xPts_GS"] - draft_all["md1_pts"] - draft_all["md2_pts"]
    draft_all["md3_opp"] = draft_all["team_code"].map(
        lambda c: FIXTURES.get(c, ["?", "?", "?"])[2] if len(FIXTURES.get(c, [])) > 2 else "?"
    )

    if d_pos != "All":
        draft_view = draft_all[draft_all["pos"] == d_pos]
    else:
        draft_view = draft_all

    draft_top = (
        draft_view
        .sort_values("xPts_GS", ascending=False)
        .head(200)
        .reset_index(drop=True)
    )
    draft_top.index += 1

    DRAFT_COLS = {
        "name":     "Name",
        "team_code": "Nation",
        "pos":      "Pos",
        "md1_opp":  "MD1 vs",
        "md2_opp":  "MD2 vs",
        "md3_opp":  "MD3 vs",
        "md1_pts":  "MD1 Pts",
        "md2_pts":  "MD2 Pts",
        "md3_pts":  "MD3 Pts",
        "xPts_GS":  "Total Pts",
    }
    disp_cols = [c for c in DRAFT_COLS if c in draft_top.columns]
    draft_disp = draft_top[disp_cols].rename(columns=DRAFT_COLS)

    st.dataframe(
        draft_disp.style.format(
            {"MD1 Pts": "{:.1f}", "MD2 Pts": "{:.1f}", "MD3 Pts": "{:.1f}", "Total Pts": "{:.1f}"},
            na_rep="—"
        ),
        use_container_width=True,
        height=680,
    )

    # Download: full list (all nations with XI, position-filtered, no 200 cap)
    download_all = (
        draft_view
        .sort_values("xPts_GS", ascending=False)
        .reset_index(drop=True)
    )
    download_all.index += 1
    download_disp = download_all[[c for c in DRAFT_COLS if c in download_all.columns]].rename(columns=DRAFT_COLS)
    st.download_button(
        "⬇️ Download full list (CSV)",
        download_disp.to_csv(index_label="Rank"),
        file_name="wc2026_draft.csv",
        mime="text/csv",
    )


st.divider()
st.caption("Scoring: Official FIFA WC Fantasy 2026 | Model: xG ratio share (sample-size regressed) × team projection + set-piece duty bonuses (PK/FK/CK) | Weights: 65% NT / 35% club | CS% & xG: FPLJoe.com bookie markets (SBOBET/Betfair)")
