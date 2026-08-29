"""UCL Fantasy Assistant — Streamlit App"""
import os
import datetime
import streamlit as st
import pandas as pd

import data_engine as _de
from data_engine import load_data, fetch_live_player_data, _norm_name, _match_key
from scoring_rules import (
    SQUAD_SLOTS, BUDGET_GROUP, BUDGET_KNOCKOUT,
    MAX_PER_COUNTRY_GROUP, MAX_PER_COUNTRY_KNOCKOUT,
    SCOUT_OWNERSHIP_THRESHOLD, SCOUT_POINTS_THRESHOLD
)
from data.team_stats import (
    TEAM_NAMES, FDR, CS_PCT, PROJ_GOALS, FIXTURES, CURRENT_ROUND, CURRENT_ROUND_DATE,
    get_team_fdr, get_next_opponent, get_team_xg, get_team_cs,
    get_qual_probs, has_round_data as _ts_has_round_data,
)

st.set_page_config(
    page_title="UCL Fantasy Assistant",
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
    st.title("⚽ UCL Fantasy Assistant")
    st.caption("Official UEFA Champions League Fantasy assistant")

    # Player list always loads from the maintained wc_squads.json (instant).
    # Live prices + ownership are overlaid from the FIFA Fantasy API separately.
    # The advanced expander exists only for debugging / local JSON import.
    with st.expander("Data source (advanced)", expanded=False):
        data_mode = st.radio("Load from", [
            "UCL pool (official UEFA feed)",
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
    st.caption("Per-90 rates: last season, all competitions + UCL record")
    st.divider()
    budget = st.number_input("Your budget (€m)", 50.0, 120.0, BUDGET_GROUP, 0.5)
    country_cap = st.slider("Max players per club", 1, 11, MAX_PER_COUNTRY_GROUP)

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
# Prices and ownership come from the UEFA feed with the pool itself, so the old
# FIFA live overlay is skipped — it would only risk overwriting good values.
if False and st.session_state.df is not None and data_mode != "Demo data (40 players)":
    live_data = _get_live_data(session_token or "")
    if live_data:
        st.session_state.df = _apply_live_data(st.session_state.df, live_data)
        st.session_state.live_refreshed_at = datetime.datetime.now()

df = st.session_state.df
if df is None or df.empty:
    st.info("👈 Click **Load / Refresh Data** to get started.")
    st.stop()

# Awaiting-draw banner: team data for the upcoming round isn't loaded yet.
if not _ts_has_round_data():
    st.warning(
        f"**Awaiting {CURRENT_ROUND} team data.** The league-phase draw / fixture "
        "board hasn't been wired into `data/team_stats.py` yet, so projections "
        "read zero. The player pool and prices still load normally."
    )

# Sidebar live data status badge
with live_status_placeholder:
    if st.session_state.live_refreshed_at:
        mins_ago = int((datetime.datetime.now() - st.session_state.live_refreshed_at).total_seconds() / 60)
        st.success(f"Live prices & ownership: {mins_ago}m ago")
    else:
        st.caption("Prices from the UEFA fantasy feed")

# ── KPI strip (rendered after the rankings table — see tab1 below) ────────────

st.divider()

# ── Helper for display ────────────────────────────────────────────────────────
SORT_LABELS = {
    "Projected points (this round)": "xPts_GS",
    "xPts per game": "xPts/game",
    "Value (xPts/€m)": "value",
    "Tournament xPts (all remaining rounds)": "tournament_xpts",
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
        "team_cs_pct": "{:.0%}", "team_xg": "{:.2f}", "proj_xg": "{:.2f}",
        "goals/90": "{:.3f}", "assists/90": "{:.3f}",
        "xg90_club": "{:.3f}", "xg90_nt": "{:.3f}",
    }
    return s.format({k: v for k, v in fmt_map.items() if k in sub.columns}, na_rep="—")


# ── Scout bonus (display-only, +2 if own%<4.5 AND projected pts≥4) ────────────
def _with_scout_bonus(view: pd.DataFrame) -> pd.DataFrame:
    v = view.copy()
    low_own = v["own_%"] < 4.5
    v["scout_bonus"] = ((low_own) & (v["xPts_GS"] >= 4.0)).astype(int) * 2
    v["adj_total"]   = v["xPts_GS"] + v["scout_bonus"]
    return v


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
    "🌐 UCL Stats",
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
    st.subheader(f"Player Rankings — Next Round ({CURRENT_ROUND})")

    f1, f2, f3 = st.columns([3, 1, 1])
    with f1:
        pos_filter = st.radio("Position", ["All", "GK", "DEF", "MID", "FWD"], horizontal=True, key="t1_pos")
    with f2:
        nation_filter = st.selectbox("Nation", ["All"] + sorted(df["country"].unique().tolist()), key="t1_nation")
    with f3:
        alive_only = st.checkbox("Still in tournament", value=True, key="t1_alive",
                                 help="Hide players whose team has been knocked out "
                                      "(no upcoming fixture this round).")

    view = df.copy()
    if alive_only and "in_round" in view.columns:
        view = view[view["in_round"]]
    if pos_filter != "All":
        view = view[view["pos"] == pos_filter]
    if nation_filter != "All":
        view = view[view["country"] == nation_filter]
    # Rank over a MATCHDAY WINDOW, not a single round — the opening squad has to
    # cover MD1-MD3, so that total is the number that matters when picking it.
    _mds = sorted(int(c.replace("xPts_md", "")) for c in df.columns
                  if c.startswith("xPts_md"))
    t1_horizon = []
    if _mds:
        _lo, _hi = min(_mds), max(_mds)
        if _lo == _hi:
            t1_horizon = [_lo]
        else:
            _f, _l = st.slider("Matchdays to total", _lo, _hi,
                               (_lo, min(_lo + 2, _hi)), key="t1_horizon")
            t1_horizon = list(range(_f, _l + 1))
    _hcols = [f"xPts_md{m}" for m in t1_horizon if f"xPts_md{m}" in view.columns]

    if _hcols:
        view = view.copy()
        view["md_total"] = view[_hcols].sum(axis=1).round(2)
        view["md_value"] = (view["md_total"] / view["price"].replace(0, float("nan"))).round(2)
        view = view.sort_values("md_total", ascending=False).reset_index(drop=True)
        _span = f"MD{t1_horizon[0]}–MD{t1_horizon[-1]}"
    else:
        view = view.sort_values("xPts_GS", ascending=False).reset_index(drop=True)
        _span = CURRENT_ROUND
    view.index += 1

    st.markdown(
        "<div style='font-size:12px;color:#aaa;padding:2px 0 6px'>"
        "🪪 Identity &nbsp;│&nbsp; 🗓️ Opponent + difficulty per matchday &nbsp;│&nbsp; "
        f"<span style='color:#4ade80'>🎯 Points per matchday, totalled over {_span}</span>"
        " &nbsp;│&nbsp; 📊 CS% / xG &nbsp;│&nbsp; 🏆 Qualification odds"
        "</div>",
        unsafe_allow_html=True,
    )

    COL_MAP = {
        "name":             "Name",
        "team_code":        "Club",
        "pos":              "Pos",
        "price":            "Price",
        "opp":              "Opp",
        # Points per matchday across the chosen window, then the total. There is
        # no separate "adjusted" figure: the old +2 scout bonus keyed off
        # ownership, which isn't part of how we pick here.
        **{f"xPts_md{m}": f"MD{m}" for m in t1_horizon},
        "md_total":         f"Total {_span}",
        "md_value":         "Pts/€m",
        "tournament_xpts":  "Tourn xPts",
        "top8_pct":         "Top8%",
        "po_pct":           "PO%",
        "r16_pct":          "R16%",
        "qf_pct":           "QF%",
        "sf_pct":           "SF%",
        "f_pct":            "Final%",
        "exp_games":        "Exp Games",
        "team_cs_pct":      "CS%",
        "team_xg":          "Team xG",
        "proj_min":         "Proj Min",
        "set_pieces":       "Set Pcs",
    }

    display_cols = [c for c in COL_MAP if c in view.columns]
    # Keep Name as a column (not the index): duplicate player names — e.g. two
    # "Emiliano Martínez" — make the index non-unique, which breaks
    # Styler.background_gradient (it uses .apply, which requires a unique index).
    disp = view[display_cols].rename(columns=COL_MAP).reset_index(drop=True)

    # Hide reach-% columns for rounds everyone shown has already reached (all 100%)
    # — e.g. R16%/QF% once the field is down to the quarter-finalists. Round-agnostic:
    # if eliminated players are shown (they read 0%), the column stays informative.
    for _qc in ["Top8%", "PO%", "R16%", "QF%", "SF%"]:
        if _qc in disp.columns and len(disp) and (disp[_qc] >= 0.999).all():
            disp = disp.drop(columns=_qc)

    md_cols  = [f"MD{m}" for m in t1_horizon if f"MD{m}" in disp.columns]
    tot_col  = [c for c in [f"Total {_span}"] if c in disp.columns]
    pts_cols = md_cols + tot_col
    pct_cols = [c for c in ["CS%"] if c in disp.columns]
    xg_cols  = [c for c in ["Team xG"] if c in disp.columns]

    qual_pct_cols = [c for c in ["Top8%", "PO%", "R16%", "QF%", "SF%", "Final%"]
                     if c in disp.columns]
    qual_xpts_cols = [c for c in ["Tourn xPts"] if c in disp.columns]

    fmt_map = {"Price": "€{:.1f}m", "Proj Min": "{:.0f}'", "Exp Games": "{:.2f}",
               "Pts/€m": "{:.2f}"}
    fmt_map.update({c: "{:.2f}" for c in xg_cols})
    fmt_map.update({c: "{:.0%}" for c in pct_cols})
    fmt_map.update({c: "{:.1f}" for c in pts_cols})
    fmt_map.update({c: "{:.0%}" for c in qual_pct_cols})
    fmt_map.update({c: "{:.2f}" for c in qual_xpts_cols})
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
            for c in ["Cl KP/90", "NT KP/90", "WC KP/90"]:
                if c in idx and isinstance(row[c], (int, float)) and row[c] >= 3.0:
                    _hi(c, BONUS_KP)
            for c in ["Cl Tkl/90", "NT Tkl/90", "WC Tkl/90"]:
                if c in idx and isinstance(row[c], (int, float)) and row[c] >= 3.0:
                    _hi(c, BONUS_TKL)
        elif pos == "FWD":
            for c in ["Cl SOT/90", "NT SOT/90", "WC SOT/90"]:
                if c in idx and isinstance(row[c], (int, float)) and row[c] >= 2.0:
                    _hi(c, BONUS_SOT)
        elif pos == "GK":
            pass  # save_rate not exposed as per-90 in rankings table

        return styles

    def _opp_fdr_style(row):
        styles = [""] * len(row)
        idx = list(row.index)
        nation = row.get("Nation", "")
        fdr_val = get_team_fdr(nation)
        if "Opp" in idx:
            styles[idx.index("Opp")] = _fdr_color(fdr_val)
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
    _active_qual = [c for c in qual_pct_cols if c in disp_idx.columns and disp_idx[c].sum() > 0]
    if _active_qual:
        styler = styler.background_gradient(subset=_active_qual, cmap="YlGn")
    _active_qxpts = [c for c in qual_xpts_cols if c in disp_idx.columns and disp_idx[c].sum() > 0]
    if _active_qxpts:
        styler = styler.background_gradient(subset=_active_qxpts, cmap="Greens")

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
**Source**: API-Football, club + international competitions:
- UEFA Champions League 2026/27 (live from MD1)
- Domestic league form (club per-90 baseline)
- International appearances (Nations League / qualifiers)

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
                        "opp", "proj_xg", "xPts_GS",
                        "xg90_nt", "xa90_nt", "xg90_club", "xa90_club",
                        "intl_games", "club_games", "nt_weight", "value"]
            st.dataframe(
                fmt(_pin_name(cp[_cp_cols], "name")),
                use_container_width=True,
            )


# ── TAB 4: Squad Builder ──────────────────────────────────────────────────────
with tab4:
    st.subheader("Build Your Best Squad")

    st.caption(f"Optimised for the upcoming round ({CURRENT_ROUND}). "
               "Pool = predicted starters on teams still in the tournament.")

    b1, b2 = st.columns(2)
    build_budget  = b1.number_input("Budget (€m)", 50.0, 120.0, budget, 0.5, key="build_b")
    build_cap     = b2.slider("Max per club", 1, 11, country_cap, key="build_cap")

    # Horizon: optimise the squad over a RANGE of matchdays, not just the next
    # one. This is what a Wildcard is for — e.g. MD1-MD3 for the opening squad,
    # then MD4-MD7 after playing the chip.
    _md_cols = sorted(
        int(c.replace("xPts_md", "")) for c in df.columns if c.startswith("xPts_md")
    )
    if _md_cols:
        lo, hi = min(_md_cols), max(_md_cols)
        if lo == hi:
            horizon = [lo]
            st.caption(f"Horizon: MD{lo} (only matchday with data loaded).")
        else:
            first, last = st.slider(
                "Matchdays to optimise for", lo, hi, (lo, min(lo + 2, hi)),
                key="build_horizon",
            )
            horizon = list(range(first, last + 1))
        _hcols = [f"xPts_md{m}" for m in horizon if f"xPts_md{m}" in df.columns]
        st.caption(
            f"Optimising total points across **MD{horizon[0]}–MD{horizon[-1]}** "
            f"({len(_hcols)} matchdays). Wildcard tip: build MD1–MD3 now, then "
            "re-run for MD4–MD7 when you play the chip."
        )
    else:
        horizon, _hcols = [], []
        st.caption("No per-matchday data loaded yet — using the upcoming round only.")

    if st.button("Build Optimal Squad", type="primary"):
        # Only pick from viable players: teams still in the tournament (eliminated
        # teams score 0 and were being grabbed as cheap fillers) and predicted
        # starters (bench players sit at 20' — don't build a squad around them).
        build_df = df.copy()
        if "in_round" in build_df.columns:
            build_df = build_df[build_df["in_round"]]
        if "predicted_starter" in build_df.columns:
            build_df = build_df[build_df["predicted_starter"]]
        # Objective: total points over the chosen horizon, else the next round.
        if _hcols:
            build_df["xPts_H"] = build_df[_hcols].sum(axis=1).round(2)
            obj = "xPts_H"
        else:
            obj = "xPts_GS"
        squad = _greedy_squad(build_df, build_budget, obj, build_cap)
        if squad is None or squad.empty:
            st.error("Could not fill squad within budget. Try increasing budget or the per-club cap.")
        else:
            cost       = squad["price"].sum()
            total_xpts = squad[obj].sum()
            span = (f"MD{horizon[0]}–MD{horizon[-1]}"
                    if obj == "xPts_H" and horizon else CURRENT_ROUND)

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Total cost", f"€{cost:.1f}m")
            sc2.metric("Remaining",  f"€{build_budget - cost:.1f}m")
            sc3.metric(f"{span} xPts", f"{total_xpts:.1f}")

            # Captain doubles a single matchday, so pick on the best SINGLE
            # matchday in the horizon, not the horizon total.
            cap_col = f"xPts_md{horizon[0]}" if (obj == "xPts_H" and horizon
                                                 and f"xPts_md{horizon[0]}" in squad.columns) \
                      else "xPts/game"
            ranked  = squad.sort_values(cap_col, ascending=False)
            captain, vice = ranked.iloc[0], ranked.iloc[1]
            st.success(
                f"⭐ Captain: **{captain['name']}**  |  👑 Vice: **{vice['name']}**  "
                f"_(best single matchday: {cap_col.replace('xPts_md', 'MD')})_"
            )

            sq_cols = ["name", "team_code", "pos", "price", "own_%", "opp"]
            sq_cols += [f"xPts_md{m}" for m in horizon if f"xPts_md{m}" in squad.columns]
            sq_cols += [c for c in (obj, "xPts_GS") if c in squad.columns and c not in sq_cols]
            sq_cols = [c for c in sq_cols if c in squad.columns]
            rename = {"name": "Name", "team_code": "Club", "pos": "Pos",
                      "price": "Price", "own_%": "Own%", "opp": "Opp",
                      "xPts_GS": "Next Rd", "xPts_H": "Total"}
            rename.update({f"xPts_md{m}": f"MD{m}" for m in horizon})
            disp_sq = _pin_name(squad[sq_cols].rename(columns=rename), "Name", "Club")
            numfmt = {"Price": "€{:.1f}m", "Own%": "{:.1f}%"}
            numfmt.update({v: "{:.1f}" for k, v in rename.items()
                           if k.startswith("xPts") and v in disp_sq.columns})
            st.dataframe(
                disp_sq.style.format(
                    {k: v for k, v in numfmt.items() if k in disp_sq.columns}, na_rep="—"
                ),
                use_container_width=True,
            )

            for pos in ["GK", "DEF", "MID", "FWD"]:
                sub = squad[squad["pos"] == pos]
                line = "  |  ".join(
                    f"{r['name']} €{r['price']:.1f}m ({r[obj]:.1f})"
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
                  "opp", "team_cs_pct", "team_xg",
                  "xPts_GS", "scout_bonus", "adj_total", "value"]
        s_cols = [c for c in s_cols if c in scouts.columns]
        s_disp = scouts[s_cols].rename(columns={
            "name": "Name", "team_code": "Nation", "pos": "Pos",
            "price": "Price", "own_%": "Own%",
            "opp": "Opp", "team_cs_pct": "CS%", "team_xg": "Team xG",
            "xPts_GS": "Proj Pts", "scout_bonus": "Scout+", "adj_total": "Adj Pts",
            "value": "Value",
        }).reset_index(drop=True)

        s_fmt = {"Price": "${:.1f}m", "Own%": "{:.1f}%",
                 "CS%": "{:.0%}", "Team xG": "{:.2f}",
                 "Proj Pts": "{:.1f}", "Scout+": "{:.0f}", "Adj Pts": "{:.1f}",
                 "Value": "{:.3f}"}
        s_grad = [c for c in ["Proj Pts", "Adj Pts"] if c in s_disp.columns and s_disp[c].dropna().nunique() >= 2]
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
                  "opp", "xPts_GS"]
        v_cols = [c for c in v_cols if c in val_view.columns]
        v_disp = val_view[v_cols].rename(columns={
            "name": "Name", "team_code": "Nation",
            "price": "Price", "adj_total": "Adj Pts", "adj_value": "Value",
            "opp": "Opp", "xPts_GS": "Proj Pts",
        }).reset_index(drop=True)

        v_fmt = {"Price": "${:.1f}m", "Adj Pts": "{:.1f}", "Value": "{:.3f}",
                 "Proj Pts": "{:.1f}"}
        v_grad = [c for c in ["Adj Pts", "Value"] if c in v_disp.columns and v_disp[c].dropna().nunique() >= 2]
        v_disp_idx = _pin_name(v_disp, "Name", "Nation")
        v_styler = v_disp_idx.style.format({k: v for k, v in v_fmt.items() if k in v_disp_idx.columns}, na_rep="—")
        if v_grad:
            v_styler = v_styler.background_gradient(subset=v_grad, cmap="Blues")
        st.dataframe(v_styler, use_container_width=True, height=480)


# ── TAB 6: Fixtures & FDR ─────────────────────────────────────────────────────
with tab6:
    st.subheader(f"Upcoming Round ({CURRENT_ROUND}) — Fixtures, CS% & Projected Goals")
    st.caption(f"CS% and xG from FPLJoe.com SBOBET/Betfair bookie markets ({CURRENT_ROUND_DATE}). CS% directly drives DEF/GK clean sheet points in model.")

    fdr_rows = []
    for code, name in sorted(TEAM_NAMES.items(), key=lambda x: get_team_fdr(x[0])):
        fdr_rows.append({
            "Country": name,
            "vs":   get_next_opponent(code),
            "FDR":  get_team_fdr(code),
            "CS%":  get_team_cs(code),
            "xG":   get_team_xg(code),
        })

    fdr_df = pd.DataFrame(fdr_rows).sort_values("FDR").set_index("Country")

    styler = fdr_df.style
    try:
        styler = styler.map(_fdr_color, subset=["FDR"])
    except AttributeError:
        styler = styler.applymap(_fdr_color, subset=["FDR"])
    styler = styler.background_gradient(subset=["CS%"], cmap="Greens")
    styler = styler.background_gradient(subset=["xG"], cmap="Oranges")
    styler = styler.format({"CS%": "{:.0%}", "xG": "{:.2f}"}, na_rep="—")

    st.dataframe(styler, use_container_width=True, height=640)


# ── TAB 7: Competition stats ──────────────────────────────────────────────────
with tab7:
    st.subheader("🌐 Real Champions League Stats (accumulated)")
    st.caption(
        "Actual per-90 stats from API-Football, refreshed each matchday "
        "(run `scripts/matchday_refresh.sh` locally). Blended into projections via "
        "empirical-Bayes shrinkage toward each player's pre-competition baseline "
        f"(prior strength {int(__import__('config').WC_FORM_PRIOR_GAMES)} games) — "
        "so one match nudges, while more UCL minutes increasingly take over."
    )

    wc_df = df[df["wc_min"] > 0].copy()
    if wc_df.empty:
        st.info(
            "No WC stats loaded yet. After a round completes, run "
            "`python3 scripts/fetch_wc_stats.py --key YOUR_KEY` on your Mac, then "
            "commit `data/wc_stats.json`."
        )
    else:
        wpos = st.radio("Position", ["All", "GK", "DEF", "MID", "FWD"],
                        horizontal=True, key="t7_pos")
        wc_view = wc_df if wpos == "All" else wc_df[wc_df["pos"] == wpos]
        wc_view = wc_view.sort_values("xPts_GS", ascending=False).reset_index(drop=True)
        wc_view.index += 1

        WC_COLS = {
            "name": "Name", "team_code": "Nation", "pos": "Pos",
            "wc_games": "WC GP", "wc_min": "WC Min",
            "xg90_wc": "WC Gls/90", "xa90_wc": "WC Ast/90", "sot90_wc": "WC SOT/90",
            "kp90_wc": "WC KP/90", "tackles90_wc": "WC Tkl/90",
            "xPts_GS": "Proj Pts",
        }
        wc_disp_cols = [c for c in WC_COLS if c in wc_view.columns]
        wc_disp = _pin_name(wc_view[wc_disp_cols].rename(columns=WC_COLS), "Name", "Nation")
        wc_per90 = ["WC Gls/90", "WC Ast/90", "WC SOT/90", "WC KP/90", "WC Tkl/90"]

        # Hide per-90 for players with < 45 WC minutes
        if "WC Min" in wc_disp.columns:
            _low_wc = wc_disp["WC Min"] < 45
            for _c in [c for c in wc_per90 if c in wc_disp.columns]:
                wc_disp.loc[_low_wc, _c] = float("nan")
        wc_fmt = {"WC Min": "{:.0f}'", "Proj Pts": "{:.1f}"}
        wc_fmt.update({c: "{:.2f}" for c in wc_per90})
        wc_styler = wc_disp.style.format(
            {k: v for k, v in wc_fmt.items() if k in wc_disp.columns}, na_rep="—"
        )
        for c in ["WC Gls/90", "WC Ast/90"]:
            if c in wc_disp.columns:
                wc_styler = wc_styler.background_gradient(subset=[c], cmap="Purples")
        st.dataframe(wc_styler, use_container_width=True, height=620)
        st.caption(f"{len(wc_df)} players with WC minutes logged.")


st.divider()
st.caption("Scoring: Official FIFA WC Fantasy 2026 | Model: xG ratio share (sample-size regressed) × team projection + set-piece duty bonuses (PK/FK/CK) | Weights: 65% NT / 35% club | CS% & xG: FPLJoe.com bookie markets (SBOBET/Betfair)")
