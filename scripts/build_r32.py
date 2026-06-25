#!/usr/bin/env python3
"""
Build the Round-of-32 data pack automatically from API-Football odds + national-team
Elo, then Monte-Carlo simulate the locked bracket to produce advancement probabilities.

Replaces the manual FPLJoe screenshot for the knockout rounds. Produces, for all 32
teams still alive:
    FIXTURES     — R32 opponent (3-letter)
    PROJ_GOALS   — projected goals (Poisson lambda from O/U 2.5 + 1X2 odds)
    CS_PCT       — clean-sheet % (e^-opp_lambda)
    FDR          — 1..5 banded by opponent threat = avg(opp_xG, opp_CS%)
    QUAL_PROBS   — {r32, r16, qf, sf, f} from a 50k Monte-Carlo of the bracket

Method (this is "our own FiveThirtyEight"):
  * R32 round (known matchups, real bookmaker odds):
      de-vig 1X2 + O/U 2.5  ->  solve two independent Poisson lambdas per match
      advance_prob = P(win) + 0.5*P(draw)        (draw -> penalty coin-flip)
  * R16 and beyond (opponents unknown until earlier rounds resolve, so NO odds exist):
      use national-team Elo. advance_prob = 1 / (1 + 10^(-elo_diff/400))
  * Monte-Carlo the binary bracket tree N times, tally how often each team reaches
    each round.  reach(R32)=1.0 for everyone in the bracket; reach(Final)=plays final.

Run LOCALLY from your Mac (API key is IP-restricted), Sunday once the bracket is set:
    cd ~/WCFantasyAssistant
    git pull origin claude/vibrant-davinci-JojAL
    pip install datafc requests          # one-time
    python3 scripts/build_r32.py --key YOUR_KEY

It writes data/r32_output.json (and prints paste-ready Python dicts). Send me that
JSON (or paste the dicts) and we cross-check against your FPLJoe + bracket screenshots
before committing the values into data/team_stats.py.

Self-test the math with no network / no key:
    python3 scripts/build_r32.py --self-test
"""
import argparse
import json
import math
import os
import sys
import time
import unicodedata
from datetime import datetime, timezone

# requests is only needed for the live (--key) path; --self-test must run without it.
try:
    import requests
except Exception:
    requests = None

BASE = "https://v3.football.api-sports.io"
DELAY = 2.2
WC_LEAGUE_ID = 1
WC_SEASON = 2026

# API-Football bet-type IDs (stable): 1 = Match Winner (1X2), 5 = Goals Over/Under.
BET_MATCH_WINNER = 1
BET_OVER_UNDER = 5
OU_LINE = "2.5"

ELO_HOME_ADV = 0.0   # WC is neutral venue (host bump handled per-team below if wanted)
ELO_HOST_BONUS = {"USA": 50.0, "MEX": 50.0, "CAN": 50.0}  # modest home-soil edge

OUTPUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "r32_output.json"))
CACHE_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "r32_fetch_cache.json"))

# API-Football team name -> our 3-letter code. Extend if a name doesn't map.
_NAME_TO_CODE = {
    "Mexico": "MEX", "South Korea": "KOR", "Korea Republic": "KOR", "Czechia": "CZE",
    "Czech Republic": "CZE", "South Africa": "RSA", "Switzerland": "SUI", "Canada": "CAN",
    "Qatar": "QAT", "Bosnia & Herzegovina": "BIH", "Bosnia and Herzegovina": "BIH",
    "Brazil": "BRA", "Morocco": "MAR", "Scotland": "SCO", "Haiti": "HAI", "USA": "USA",
    "United States": "USA", "Turkey": "TUR", "Türkiye": "TUR", "Australia": "AUS",
    "Paraguay": "PAR", "Germany": "GER", "Ecuador": "ECU", "Ivory Coast": "CIV",
    "Cote d'Ivoire": "CIV", "Curacao": "CUW", "Curaçao": "CUW", "Netherlands": "NED",
    "Japan": "JPN", "Sweden": "SWE", "Tunisia": "TUN", "Belgium": "BEL", "Iran": "IRN",
    "Egypt": "EGY", "New Zealand": "NZL", "Spain": "ESP", "Uruguay": "URU",
    "Saudi Arabia": "KSA", "Cape Verde": "CPV", "Cape Verde Islands": "CPV",
    "France": "FRA", "Senegal": "SEN", "Norway": "NOR", "Iraq": "IRQ", "Argentina": "ARG",
    "Austria": "AUT", "Algeria": "ALG", "Jordan": "JOR", "Portugal": "POR",
    "Colombia": "COL", "DR Congo": "COD", "Congo DR": "COD", "Uzbekistan": "UZB",
    "England": "ENG", "Croatia": "CRO", "Ghana": "GHA", "Panama": "PAN",
}

# Our 3-letter code -> eloratings.net page slug (for the World.tsv fallback / datafc).
_CODE_TO_ELO_SLUG = {
    "MEX": "Mexico", "KOR": "South_Korea", "CZE": "Czech_Republic", "RSA": "South_Africa",
    "SUI": "Switzerland", "CAN": "Canada", "QAT": "Qatar", "BIH": "Bosnia_and_Herzegovina",
    "BRA": "Brazil", "MAR": "Morocco", "SCO": "Scotland", "HAI": "Haiti", "USA": "United_States",
    "TUR": "Turkey", "AUS": "Australia", "PAR": "Paraguay", "GER": "Germany", "ECU": "Ecuador",
    "CIV": "Ivory_Coast", "CUW": "Curacao", "NED": "Netherlands", "JPN": "Japan",
    "SWE": "Sweden", "TUN": "Tunisia", "BEL": "Belgium", "IRN": "Iran", "EGY": "Egypt",
    "NZL": "New_Zealand", "ESP": "Spain", "URU": "Uruguay", "KSA": "Saudi_Arabia",
    "CPV": "Cape_Verde", "FRA": "France", "SEN": "Senegal", "NOR": "Norway", "IRQ": "Iraq",
    "ARG": "Argentina", "AUT": "Austria", "ALG": "Algeria", "JOR": "Jordan", "POR": "Portugal",
    "COL": "Colombia", "COD": "Congo_DR", "UZB": "Uzbekistan", "ENG": "England",
    "CRO": "Croatia", "GHA": "Ghana", "PAN": "Panama",
}


# ── Poisson helpers ────────────────────────────────────────────────────────────

def _pois_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _p_over_25(mu: float) -> float:
    """P(total goals >= 3) for total ~ Poisson(mu)  (sum of two independent Poissons)."""
    p_le2 = sum(_pois_pmf(k, mu) for k in range(3))
    return 1.0 - p_le2


def _solve_mu_from_over(p_over: float) -> float:
    """Invert P(total>=3)=p_over for mu via bisection. Clamped to a sane goal range."""
    lo, hi = 0.2, 7.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _p_over_25(mid) < p_over:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _match_probs(lam_h: float, lam_a: float, max_goals: int = 12) -> tuple:
    """Return (p_home, p_draw, p_away) from two independent Poisson lambdas."""
    ph = pd = pa = 0.0
    for i in range(max_goals + 1):
        pi = _pois_pmf(i, lam_h)
        for j in range(max_goals + 1):
            pij = pi * _pois_pmf(j, lam_a)
            if i > j:
                ph += pij
            elif i == j:
                pd += pij
            else:
                pa += pij
    return ph, pd, pa


def _solve_lambdas(p_home: float, p_draw: float, p_away: float, p_over: float) -> tuple:
    """
    Solve two independent Poisson lambdas matching:
      total mean  -> O/U 2.5 over-probability
      split       -> 1X2 home/away supremacy
    Returns (lam_home, lam_away).
    """
    mu = _solve_mu_from_over(p_over)
    target = p_home - p_away          # supremacy signal, monotonic in lam_h share
    lo, hi = 0.0, mu                  # lam_h in [0, mu]; lam_a = mu - lam_h
    for _ in range(60):
        lam_h = 0.5 * (lo + hi)
        ph, _pd, pa = _match_probs(lam_h, mu - lam_h)
        if (ph - pa) < target:
            lo = lam_h
        else:
            hi = lam_h
    lam_h = 0.5 * (lo + hi)
    return lam_h, mu - lam_h


# ── Odds de-vig ────────────────────────────────────────────────────────────────

def _devig(odds: list) -> list:
    """Decimal odds -> de-vigged probabilities (proportional / Shin-lite)."""
    inv = [1.0 / o for o in odds if o and o > 1.0]
    s = sum(inv)
    if s <= 0:
        return []
    return [x / s for x in inv]


# ── Elo ────────────────────────────────────────────────────────────────────────

def _elo_advance_prob(elo_a: float, elo_b: float) -> float:
    """P(team A advances past B) from Elo expected score (penalties folded in)."""
    return 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / 400.0))


def load_elo(codes: list, elo_file: str = None) -> dict:
    """code -> Elo rating. Tries --elo-file (CSV: code,rating), then datafc, then World.tsv."""
    elo: dict = {}

    if elo_file and os.path.exists(elo_file):
        with open(elo_file) as f:
            for line in f:
                parts = [p.strip() for p in line.replace("\t", ",").split(",")]
                if len(parts) >= 2 and parts[0].upper() in _CODE_TO_ELO_SLUG:
                    try:
                        elo[parts[0].upper()] = float(parts[1])
                    except ValueError:
                        pass
        if elo:
            print(f"  Elo: loaded {len(elo)} from {elo_file}")
            return elo

    # datafc (preferred — wraps eloratings.net and parses the headerless TSV correctly)
    try:
        from datafc.eloratings import world_ranking_data
        wr = world_ranking_data()
        slug_to_code = {v.replace("_", " ").lower(): k for k, v in _CODE_TO_ELO_SLUG.items()}
        for _, row in wr.iterrows():
            name = str(row.get("country", row.get("team", ""))).replace("_", " ").lower()
            rating = row.get("rating", row.get("total", None))
            code = slug_to_code.get(name)
            if code and rating is not None:
                try:
                    elo[code] = float(rating)
                except (ValueError, TypeError):
                    pass
        if elo:
            print(f"  Elo: loaded {len(elo)} via datafc (eloratings.net)")
            return elo
    except Exception as e:
        print(f"  Elo: datafc unavailable ({e}); trying direct World.tsv")

    # Direct World.tsv fallback
    if requests is not None:
        try:
            r = requests.get("https://www.eloratings.net/World.tsv", timeout=20,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            name_to_code = {v.replace("_", " ").lower(): k for k, v in _CODE_TO_ELO_SLUG.items()}
            for line in r.text.splitlines():
                cols = line.split("\t")
                ratings = [c for c in cols if c.replace(".", "").isdigit() and 900 < float(c) < 2400]
                row_name = next((c.replace("_", " ").lower() for c in cols
                                 if c.replace("_", " ").lower() in name_to_code), None)
                if row_name and ratings:
                    elo[name_to_code[row_name]] = float(ratings[0])
            if elo:
                print(f"  Elo: loaded {len(elo)} via direct World.tsv")
                return elo
        except Exception as e:
            print(f"  Elo: World.tsv fetch failed ({e})")

    missing = [c for c in codes if c not in elo]
    if missing:
        print(f"  [WARN] No Elo for {missing} — defaulting them to 1500. "
              f"Supply --elo-file code,rating to fix.")
        for c in missing:
            elo[c] = 1500.0
    return elo


# ── API-Football fetch ─────────────────────────────────────────────────────────

_REQS = 0


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            return json.load(open(CACHE_FILE))
        except Exception:
            pass
    return {}


def _save_cache(c: dict) -> None:
    json.dump(c, open(CACHE_FILE, "w"), indent=2, ensure_ascii=False)


def _get(endpoint: str, params: dict, cache: dict, key: str, headers: dict,
         allow_cache: bool = True) -> dict:
    global _REQS
    if allow_cache and key in cache:
        return cache[key]
    time.sleep(DELAY)
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{endpoint}", headers=headers, params=params, timeout=25)
            if r.status_code == 429:
                w = 60 * (attempt + 1)
                print(f"  Rate-limited — waiting {w}s..."); time.sleep(w); continue
            r.raise_for_status()
            data = r.json()
            _REQS += 1
            cache[key] = data
            _save_cache(cache)
            return data
        except Exception as e:
            print(f"  [ERR] {endpoint} {params}: {e}")
            return {}
    return {}


def get_r32_fixtures(round_name: str, cache: dict, headers: dict) -> list:
    """Return list of {fixture_id, home_code, away_code} for the requested round."""
    data = _get("fixtures", {"league": WC_LEAGUE_ID, "season": WC_SEASON, "round": round_name},
                cache, f"fixtures_{round_name}", headers, allow_cache=False)
    out = []
    for fix in data.get("response", []):
        hid = fix.get("teams", {}).get("home", {})
        aid = fix.get("teams", {}).get("away", {})
        hc = _NAME_TO_CODE.get(hid.get("name"))
        ac = _NAME_TO_CODE.get(aid.get("name"))
        if not hc or not ac:
            print(f"  [WARN] Unmapped team: {hid.get('name')} / {aid.get('name')} "
                  f"— add to _NAME_TO_CODE")
            continue
        out.append({"fixture_id": fix.get("fixture", {}).get("id"),
                    "home_code": hc, "away_code": ac})
    return out


def get_fixture_odds(fixture_id: int, cache: dict, headers: dict) -> tuple:
    """Return (p_home, p_draw, p_away, p_over25) de-vigged, averaged across bookmakers."""
    data = _get("odds", {"league": WC_LEAGUE_ID, "season": WC_SEASON, "fixture": fixture_id},
                cache, f"odds_{fixture_id}", headers)
    wins, overs = [], []
    for resp in data.get("response", []):
        for bm in resp.get("bookmakers", []):
            for bet in bm.get("bets", []):
                bid = bet.get("id")
                vals = bet.get("values", [])
                if bid == BET_MATCH_WINNER:
                    od = {v.get("value"): float(v.get("odd")) for v in vals if v.get("odd")}
                    if {"Home", "Draw", "Away"} <= set(od):
                        p = _devig([od["Home"], od["Draw"], od["Away"]])
                        if len(p) == 3:
                            wins.append(p)
                elif bid == BET_OVER_UNDER:
                    od = {v.get("value"): float(v.get("odd")) for v in vals if v.get("odd")}
                    o, u = od.get(f"Over {OU_LINE}"), od.get(f"Under {OU_LINE}")
                    if o and u:
                        p = _devig([o, u])
                        if len(p) == 2:
                            overs.append(p[0])
    if not wins or not overs:
        return None
    ph = sum(w[0] for w in wins) / len(wins)
    pdw = sum(w[1] for w in wins) / len(wins)
    pa = sum(w[2] for w in wins) / len(wins)
    return ph, pdw, pa, sum(overs) / len(overs)


# ── Bracket Monte-Carlo ────────────────────────────────────────────────────────

def simulate_bracket(r32_pairs: list, r32_adv: dict, elo: dict, n_sims: int) -> dict:
    """
    r32_pairs: ordered list of (codeA, codeB) — bracket order, so pairs
               (0,1),(2,3),... meet in R16, etc.
    r32_adv:   {(codeA,codeB): prob_A_advances} from odds (round 1 only).
    elo:       code -> rating, used for all rounds AFTER R32.
    Returns code -> {"r32","r16","qf","sf","f"} reach-probabilities.
    """
    import random
    rounds = ["r16", "qf", "sf", "f"]
    teams = [c for pair in r32_pairs for c in pair]
    reach = {c: {"r32": float(n_sims), "r16": 0, "qf": 0, "sf": 0, "f": 0} for c in teams}

    def play(a, b, p_a):
        return a if random.random() < p_a else b

    for _ in range(n_sims):
        # Round of 32 (odds-driven)
        winners = []
        for (a, b) in r32_pairs:
            pa = r32_adv.get((a, b), _elo_advance_prob(elo.get(a, 1500), elo.get(b, 1500)))
            winners.append(play(a, b, pa))
        # subsequent rounds (Elo-driven); stop once a champion remains
        for rd in rounds:
            if len(winners) < 2:
                break
            for w in winners:
                reach[w][rd] += 1
            nxt = []
            for i in range(0, len(winners) - 1, 2):
                a, b = winners[i], winners[i + 1]
                pa = _elo_advance_prob(elo.get(a, 1500), elo.get(b, 1500))
                nxt.append(play(a, b, pa))
            winners = nxt

    return {c: {k: round(v / n_sims, 4) for k, v in d.items()} for c, d in reach.items()}


# ── FDR banding (matches data/team_stats.py) ───────────────────────────────────

def _fdr_band(opp_threat: float) -> int:
    if opp_threat < 0.45:
        return 1
    if opp_threat < 0.62:
        return 2
    if opp_threat < 0.85:
        return 3
    if opp_threat < 1.20:
        return 4
    return 5


# ── Self-test (no network) ─────────────────────────────────────────────────────

def _self_test() -> None:
    print("Self-test: Poisson solver + bracket MC (no network)\n")

    # A clear favourite: low O/U over-prob would mean few goals; pick a goal-heavy fav.
    p_home, p_draw, p_away, p_over = 0.62, 0.22, 0.16, 0.55
    lam_h, lam_a = _solve_lambdas(p_home, p_draw, p_away, p_over)
    ph, pdw, pa = _match_probs(lam_h, lam_a)
    print(f"  inputs : 1X2={p_home:.2f}/{p_draw:.2f}/{p_away:.2f}  over2.5={p_over:.2f}")
    print(f"  lambdas: home={lam_h:.2f} away={lam_a:.2f}  (mu={lam_h+lam_a:.2f})")
    print(f"  refit  : 1X2={ph:.2f}/{pdw:.2f}/{pa:.2f}  over2.5={_p_over_25(lam_h+lam_a):.2f}")
    print(f"  CS%    : home={math.exp(-lam_a):.2f} away={math.exp(-lam_h):.2f}")
    assert lam_h > lam_a, "favourite should have higher lambda"
    assert abs(ph - p_home) < 0.06, "home prob should refit closely"

    # 4-team mini bracket: A strong, D weak.
    elo = {"A": 2000, "B": 1800, "C": 1700, "D": 1500}
    pairs = [("A", "D"), ("B", "C")]
    r32_adv = {("A", "D"): 0.85, ("B", "C"): 0.55}
    probs = simulate_bracket(pairs, r32_adv, elo, 20000)
    print("\n  mini-bracket reach probabilities (r16 = won R32 match):")
    for c in ["A", "B", "C", "D"]:
        d = probs[c]
        print(f"    {c}: r32={d['r32']:.2f} r16={d['r16']:.2f}")
    assert probs["A"]["r16"] > probs["D"]["r16"], "A should reach R16 more than D"
    assert abs(probs["A"]["r16"] - 0.85) < 0.03, "A R16 should track its odds-based adv"
    print("\n  ✓ all assertions passed")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", help="API-Football key")
    ap.add_argument("--round", default="Round of 32", help='API round name (default "Round of 32")')
    ap.add_argument("--sims", type=int, default=50000, help="Monte-Carlo iterations")
    ap.add_argument("--elo-file", help="Optional CSV/TSV fallback: code,rating per line")
    ap.add_argument("--self-test", action="store_true", help="Run math self-test, no network")
    args = ap.parse_args()

    if args.self_test:
        _self_test()
        return
    if not args.key:
        ap.error("--key is required (or use --self-test)")
    if requests is None:
        ap.error("requests not installed: pip install requests")

    headers = {"x-apisports-key": args.key}
    cache = _load_cache()

    print(f"Step 1/4 — Fetching '{args.round}' fixtures...")
    fixtures = get_r32_fixtures(args.round, cache, headers)
    if not fixtures:
        print("No fixtures found. Has the bracket been set? Check --round name.")
        sys.exit(1)
    print(f"  {len(fixtures)} fixtures.")

    print("Step 2/4 — Fetching odds + solving Poisson lambdas...")
    proj_goals, cs_pct, fixtures_map = {}, {}, {}
    r32_pairs, r32_adv = [], {}
    lam = {}  # code -> projected goals (lambda)
    for fx in fixtures:
        h, a = fx["home_code"], fx["away_code"]
        fixtures_map[h], fixtures_map[a] = a, h
        odds = get_fixture_odds(fx["fixture_id"], cache, headers)
        if not odds:
            print(f"  [WARN] No odds for {h} v {a} — skipping (fill manually).")
            continue
        ph, pdw, pa, pov = odds
        lam_h, lam_a = _solve_lambdas(ph, pdw, pa, pov)
        lam[h], lam[a] = round(lam_h, 2), round(lam_a, 2)
        proj_goals[h], proj_goals[a] = round(lam_h, 2), round(lam_a, 2)
        cs_pct[h] = round(math.exp(-lam_a), 2)   # home CS = away scores 0
        cs_pct[a] = round(math.exp(-lam_h), 2)
        r32_pairs.append((h, a))
        r32_adv[(h, a)] = round(ph + 0.5 * pdw, 4)

    print("Step 3/4 — Loading Elo + Monte-Carlo bracket...")
    codes = [c for pair in r32_pairs for c in pair]
    elo = load_elo(codes, args.elo_file)
    qual = simulate_bracket(r32_pairs, r32_adv, elo, args.sims)
    qual_probs = {c: {"r32": d["r32"], "r16": d["r16"], "qf": d["qf"],
                      "sf": d["sf"], "f": d["f"]} for c, d in qual.items()}

    print("Step 4/4 — Banding FDR...")
    fdr = {}
    for c in codes:
        opp = fixtures_map[c]
        opp_threat = (lam.get(opp, 1.0) + cs_pct.get(opp, 0.3)) / 2.0
        fdr[c] = _fdr_band(opp_threat)

    out = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "round": args.round,
        "sims": args.sims,
        "api_requests": _REQS,
        "FIXTURES": fixtures_map,
        "PROJ_GOALS": proj_goals,
        "CS_PCT": cs_pct,
        "FDR": fdr,
        "QUAL_PROBS": qual_probs,
        "_note": "r32_pairs are in API order; verify bracket order vs the official "
                 "bracket before trusting R16+ probabilities.",
        "r32_pairs": r32_pairs,
    }
    json.dump(out, open(OUTPUT, "w"), indent=2, ensure_ascii=False)
    print(f"\nSaved → {OUTPUT}  ({len(codes)} teams, {_REQS} API requests)")
    print("\n── paste-ready (cross-check vs FPLJoe + bracket screenshots first) ──")
    for name in ("FIXTURES", "PROJ_GOALS", "CS_PCT", "FDR", "QUAL_PROBS"):
        print(f"\n{name} = {json.dumps(out[name], indent=4)}")
    print("\nNext: send Claude data/r32_output.json (or paste the dicts above).")


if __name__ == "__main__":
    main()
