#!/usr/bin/env python3
"""
Match FBref player names to FIFA Fantasy player IDs.
Run LOCALLY after fetch_fbref.py.

Input:  data/fbref_stats.json
        data/cache/fifa_fantasy_players_raw.json  (or uses demo names as fallback)
Output: data/fbref_player_map.json  {fifa_player_id: fbref_stats_dict}
Log:    data/fbref_unmatched.txt
"""
import json
import os
import sys
import unicodedata

FBREF_STATS_FILE = "data/fbref_stats.json"
FBREF_MAP_FILE   = "data/fbref_player_map.json"
UNMATCHED_FILE   = "data/fbref_unmatched.txt"
FIFA_CACHE_FILE  = "data/cache/fifa_fantasy_players_raw.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_name(name: str) -> str:
    name = name.lower().replace("ı", "i")
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()


def _tokens(norm: str) -> frozenset[str]:
    return frozenset(w for w in norm.split() if len(w) > 1)


# ── FIFA player list extraction ───────────────────────────────────────────────

POSITION_MAP = {
    1: "GK", 2: "DEF", 3: "MID", 4: "FWD",
    "Goalkeeper": "GK", "Defender": "DEF",
    "Midfielder": "MID", "Forward": "FWD", "Attacker": "FWD",
}

FIFA_TEAM_ID_TO_CODE: dict[int, str] = {
    1: "ALG",  2: "ARG",  3: "AUS",  4: "AUT",  5: "BEL",  6: "BIH",
    7: "BRA",  8: "CPV",  9: "CAN", 10: "COL", 11: "COD", 12: "CIV",
   13: "CRO", 14: "CUW", 15: "CZE", 16: "ECU", 17: "EGY", 18: "ENG",
   19: "FRA", 20: "GER", 21: "GHA", 22: "HAI", 23: "IRN", 24: "IRQ",
   25: "JPN", 26: "JOR", 27: "KOR", 28: "MEX", 29: "MAR", 30: "NED",
   31: "NZL", 32: "NOR", 33: "PAN", 34: "PAR", 35: "POR", 36: "QAT",
   37: "KSA", 38: "SCO", 39: "SEN", 40: "RSA", 41: "ESP", 42: "SWE",
   43: "SUI", 44: "TUN", 45: "TUR", 46: "URU", 47: "USA", 48: "UZB",
}


def _parse_fifa_cache(data) -> list[dict]:
    """Extract [{id, name, club}] from FIFA Fantasy raw cache."""
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = data.get("players") or data.get("data") or data.get("response") or []
    else:
        return []

    players = []
    for raw in raw_list:
        if raw.get("status") == "transferred":
            continue
        pid = str(raw.get("id") or raw.get("playerId") or "")
        if not pid:
            continue

        known = raw.get("knownName")
        if known:
            name = known
        else:
            first = raw.get("firstName") or raw.get("name") or ""
            last  = raw.get("lastName") or ""
            name  = f"{first} {last}".strip()
        if not name:
            continue

        club = raw.get("clubName") or raw.get("club") or ""
        players.append({"id": pid, "name": name, "club": club})
    return players


def _demo_players() -> list[dict]:
    """Fallback: demo player names with placeholder IDs when FIFA cache absent."""
    names = [
        ("1",  "Thibaut Courtois",    "Real Madrid"),
        ("2",  "Alisson Becker",      "Liverpool"),
        ("3",  "Emiliano Martinez",   "Aston Villa"),
        ("10", "Virgil van Dijk",     "Liverpool"),
        ("11", "Achraf Hakimi",       "PSG"),
        ("12", "Alejandro Grimaldo",  "Bayer Leverkusen"),
        ("13", "Theo Hernandez",      "AC Milan"),
        ("14", "Ruben Dias",          "Man City"),
        ("30", "Jude Bellingham",     "Real Madrid"),
        ("31", "Florian Wirtz",       "Bayer Leverkusen"),
        ("32", "Pedri",               "Barcelona"),
        ("33", "Phil Foden",          "Man City"),
        ("34", "Declan Rice",         "Arsenal"),
        ("35", "Nico Williams",       "Athletic Bilbao"),
        ("50", "Kylian Mbappe",       "Real Madrid"),
        ("51", "Erling Haaland",      "Man City"),
        ("52", "Harry Kane",          "Bayern Munich"),
        ("53", "Lamine Yamal",        "Barcelona"),
        ("54", "Vinicius Jr",         "Real Madrid"),
        ("55", "Bukayo Saka",         "Arsenal"),
    ]
    return [{"id": pid, "name": name, "club": club} for pid, name, club in names]


# ── Matching ──────────────────────────────────────────────────────────────────

def _best_candidate(candidates: list[dict], club: str) -> dict:
    """If multiple FBref records share a norm-name, prefer the one whose squad
    matches the FIFA club field."""
    if len(candidates) == 1:
        return candidates[0]
    norm_club = _norm_name(club)
    for c in candidates:
        if norm_club and _norm_name(c.get("squad", "")) == norm_club:
            return c
    # Fall back to the one with most minutes
    return max(candidates, key=lambda c: c.get("min", 0))


def _fbref_stats(p: dict) -> dict:
    """Extract only the fields we expose to data_engine.py."""
    return {
        "name":         p["name"],
        "norm_name":    p["norm_name"],
        "squad":        p.get("squad", ""),
        "pos":          p.get("pos", ""),
        "league":       p.get("league", ""),
        "mp":           p.get("mp", 0),
        "starts":       p.get("starts", 0),
        "xg90":         p.get("xg90",  0.0),
        "xa90":         p.get("xa90",  0.0),
        "goals90":      p.get("goals90", 0.0),
        "sot90":        p.get("sot90",  0.0),
        "starter_rate": p.get("starter_rate", 1.0),
    }


def match_players() -> None:
    # ── Load FBref stats ──────────────────────────────────────────────────────
    if not os.path.exists(FBREF_STATS_FILE):
        print(f"[ERROR] {FBREF_STATS_FILE} not found. Run fetch_fbref.py first.")
        sys.exit(1)
    with open(FBREF_STATS_FILE) as f:
        fbref_players: list[dict] = json.load(f)
    print(f"FBref stats: {len(fbref_players)} players loaded")

    # Build norm_name -> list[dict] index
    by_norm: dict[str, list[dict]] = {}
    for p in fbref_players:
        by_norm.setdefault(p["norm_name"], []).append(p)

    # Build token-set index for fuzzy matching
    token_index: list[tuple[frozenset, str, list[dict]]] = [
        (_tokens(norm), norm, plist)
        for norm, plist in by_norm.items()
    ]

    # ── Load FIFA Fantasy players ────────────────────────────────────────────
    if os.path.exists(FIFA_CACHE_FILE):
        with open(FIFA_CACHE_FILE) as f:
            raw = json.load(f)
        fifa_players = _parse_fifa_cache(raw)
        print(f"FIFA Fantasy cache: {len(fifa_players)} players")
    else:
        print(f"[WARN] {FIFA_CACHE_FILE} not found. Using demo player list.")
        fifa_players = _demo_players()

    # ── Match ─────────────────────────────────────────────────────────────────
    result: dict[str, dict] = {}
    unmatched: list[str] = []

    for fp in fifa_players:
        fid   = fp["id"]
        fname = fp["name"]
        fclub = fp.get("club", "")
        fnorm = _norm_name(fname)

        # 1. Exact norm-name match
        if fnorm in by_norm:
            best = _best_candidate(by_norm[fnorm], fclub)
            result[fid] = _fbref_stats(best)
            continue

        # 2. Fuzzy: all FIFA tokens present in FBref norm-name (or vice-versa)
        ftok = _tokens(fnorm)
        matched: dict | None = None
        if len(ftok) >= 2:
            for btok, bnorm, blist in token_index:
                if ftok <= btok or btok <= ftok:
                    matched = _best_candidate(blist, fclub)
                    break

        # 3. Last-name-only match (single token, e.g. "Neymar")
        if matched is None and len(ftok) == 1:
            tok = next(iter(ftok))
            for btok, bnorm, blist in token_index:
                if tok in btok:
                    matched = _best_candidate(blist, fclub)
                    break

        if matched:
            result[fid] = _fbref_stats(matched)
        else:
            unmatched.append(f"{fid}\t{fname}")

    total = len(fifa_players)
    matched_n = len(result)
    print(f"Matched : {matched_n}/{total} ({100*matched_n//total if total else 0}%)")
    print(f"Unmatched: {len(unmatched)}")

    # ── Write outputs ─────────────────────────────────────────────────────────
    os.makedirs("data", exist_ok=True)
    with open(FBREF_MAP_FILE, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Saved: {FBREF_MAP_FILE}")

    with open(UNMATCHED_FILE, "w") as f:
        f.write("# FIFA_ID\tPlayer Name\n")
        f.write("\n".join(unmatched))
    print(f"Unmatched log: {UNMATCHED_FILE}")


if __name__ == "__main__":
    match_players()
