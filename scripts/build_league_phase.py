#!/usr/bin/env python3
"""
Monte-Carlo the UEFA Champions League league phase (36 teams, 8 games each) and
the knockout bracket that follows, producing the reach-probabilities and
expected-remaining-matches that data/team_stats.py consumes.

    # full season from scratch (before MD1)
    python3 scripts/build_league_phase.py --elo data/ucl_elo.csv

    # mid-season: only simulate MD5 onward, using the real table so far
    python3 scripts/build_league_phase.py --elo data/ucl_elo.csv \
        --from-md 5 --standings data/ucl_standings.json

    python3 scripts/build_league_phase.py --self-test     # no files needed

Outputs data/ucl_league_output.json plus paste-ready QUAL_PROBS / EXP_GAMES.

Format modelled
---------------
  * League phase: single table, 3-1-0, ranked on points → goal difference →
    goals for. Positions 1-8 go straight to the R16; 9-24 play a two-legged
    knockout playoff; 25-36 are eliminated.
  * Knockouts: PO / R16 / QF / SF are TWO legs (two fantasy matchdays each),
    the Final is one match. EXP_GAMES counts both legs.
  * Bracket seeding is by league position (1 meets the weakest playoff winner,
    and so on). UEFA publishes the exact tree with the draw — until then this
    is the standard seeded shape, which is what the deep-round numbers assume.

Inputs
------
  --fixtures  JSON list of {"md": int, "home": CODE, "away": CODE}   (144 rows)
  --elo       CSV "Name,Rating" — either our 3-letter codes or ClubElo club
              names (mapped via CLUBELO_NAME_TO_CODE below)
  --standings JSON {CODE: {"pts": int, "gf": int, "ga": int, "played": int}}
"""
import argparse
import json
import math
import os
import random
from collections import defaultdict

DATA = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data"))
OUTPUT = os.path.join(DATA, "ucl_league_output.json")

# ── Model constants (tunable) ─────────────────────────────────────────────────
HOME_ADV_ELO       = 60.0    # home edge, in Elo points
SUPREMACY_PER_ELO  = 0.006   # goal supremacy per Elo point of difference
BASE_TOTAL_GOALS   = 3.0     # expected combined goals in a neutral UCL tie
MIN_LAMBDA, MAX_LAMBDA = 0.15, 5.0
# Knockout variance: a one-off tie is closer to a coin flip than raw strength
# suggests (extra time, penalties). Same calibration as the WC bracket model.
KO_VARIANCE_K = 0.65

# ClubElo spells clubs its own way; map the ones we care about to our codes.
# Extend as needed once the 36 participants are known.
CLUBELO_NAME_TO_CODE = {
    "Man City": "MCI", "Liverpool": "LIV", "Arsenal": "ARS", "Chelsea": "CHE",
    "Tottenham": "TOT", "Newcastle": "NEW", "Aston Villa": "AVL",
    "Real Madrid": "RMA", "Barcelona": "BAR", "Atletico": "ATM",
    "Athletic": "ATH", "Villarreal": "VIL", "Betis": "BET",
    "Bayern": "BAY", "Dortmund": "DOR", "Leverkusen": "LEV",
    "RB Leipzig": "RBL", "Stuttgart": "STU", "Frankfurt": "FRA",
    "Inter": "INT", "Milan": "MIL", "Juventus": "JUV", "Napoli": "NAP",
    "Atalanta": "ATA", "Roma": "ROM",
    "Paris SG": "PSG", "Monaco": "MON", "Marseille": "MAR", "Lille": "LIL",
    "Lyon": "LYO",
    "Benfica": "BEN", "Porto": "POR", "Sporting": "SPO",
    "Ajax": "AJA", "PSV": "PSV", "Feyenoord": "FEY", "Club Brugge": "CLB",
    "Celtic": "CEL", "Galatasaray": "GAL", "Fenerbahce": "FEN",
    "Salzburg": "RBS", "Shakhtar": "SHK", "Slavia Praha": "SLP",
    "Dinamo Zagreb": "DZG", "Olympiacos": "OLY", "Sturm Graz": "STE",
    "Young Boys": "BSC", "FC Kobenhavn": "COP", "Bodo/Glimt": "BOD",
}


# ── Match model ───────────────────────────────────────────────────────────────

def lambdas(elo_h: float, elo_a: float, neutral: bool = False) -> tuple:
    """Expected goals for (home, away) from Elo ratings."""
    diff = (elo_h - elo_a) + (0.0 if neutral else HOME_ADV_ELO)
    sup = diff * SUPREMACY_PER_ELO
    lh = (BASE_TOTAL_GOALS + sup) / 2.0
    la = (BASE_TOTAL_GOALS - sup) / 2.0
    return (max(MIN_LAMBDA, min(MAX_LAMBDA, lh)),
            max(MIN_LAMBDA, min(MAX_LAMBDA, la)))


def _poisson(lam: float, rng: random.Random) -> int:
    """Knuth sampler — plenty fast for these lambdas."""
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= l:
            return k
        k += 1
        if k > 15:
            return k


def elo_advance_prob(elo_a: float, elo_b: float) -> float:
    """P(A advances past B) in a knockout, shrunk toward 0.5 for tie variance."""
    p = 1.0 / (1.0 + 10 ** (-(elo_a - elo_b) / 400.0))
    return 0.5 + KO_VARIANCE_K * (p - 0.5)


def two_legged_winner(a: str, b: str, elo: dict, rng: random.Random) -> str:
    """Two legs, aggregate goals; level ties resolved by dampened Elo."""
    ea, eb = elo.get(a, 1500.0), elo.get(b, 1500.0)
    # leg 1 at A, leg 2 at B
    l1h, l1a = lambdas(ea, eb)
    l2h, l2a = lambdas(eb, ea)
    agg_a = _poisson(l1h, rng) + _poisson(l2a, rng)
    agg_b = _poisson(l1a, rng) + _poisson(l2h, rng)
    if agg_a != agg_b:
        return a if agg_a > agg_b else b
    return a if rng.random() < elo_advance_prob(ea, eb) else b


def single_match_winner(a: str, b: str, elo: dict, rng: random.Random) -> str:
    ea, eb = elo.get(a, 1500.0), elo.get(b, 1500.0)
    lh, la = lambdas(ea, eb, neutral=True)
    ga, gb = _poisson(lh, rng), _poisson(la, rng)
    if ga != gb:
        return a if ga > gb else b
    return a if rng.random() < elo_advance_prob(ea, eb) else b


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_elo(path: str) -> dict:
    elo: dict = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.replace("\t", ",").split(",")]
            if len(parts) < 2:
                continue
            name, rating = parts[0], parts[1]
            try:
                val = float(rating)
            except ValueError:
                continue
            code = name.upper() if len(name) == 3 else CLUBELO_NAME_TO_CODE.get(name)
            if code:
                elo[code] = val
    return elo


def load_fixtures(path: str) -> list:
    with open(path) as f:
        rows = json.load(f)
    return [{"md": int(r["md"]), "home": r["home"], "away": r["away"]} for r in rows]


# ── Simulation ────────────────────────────────────────────────────────────────

def simulate(fixtures: list, elo: dict, standings: dict, from_md: int,
             n_sims: int, seed: int = 20260901) -> tuple:
    """Returns (qual_probs, exp_games, pos_hist)."""
    teams = sorted({t for f in fixtures for t in (f["home"], f["away"])})
    to_play = [f for f in fixtures if f["md"] >= from_md]
    rng = random.Random(seed)

    reach = {t: defaultdict(float) for t in teams}
    games = {t: 0.0 for t in teams}
    pos_hist = {t: defaultdict(float) for t in teams}

    for _ in range(n_sims):
        pts = {t: float(standings.get(t, {}).get("pts", 0)) for t in teams}
        gf  = {t: float(standings.get(t, {}).get("gf", 0)) for t in teams}
        ga  = {t: float(standings.get(t, {}).get("ga", 0)) for t in teams}

        # League phase
        for fx in to_play:
            h, a = fx["home"], fx["away"]
            lh, la = lambdas(elo.get(h, 1500.0), elo.get(a, 1500.0))
            gh, gaw = _poisson(lh, rng), _poisson(la, rng)
            gf[h] += gh; ga[h] += gaw
            gf[a] += gaw; ga[a] += gh
            games[h] += 1; games[a] += 1
            if gh > gaw:
                pts[h] += 3
            elif gh < gaw:
                pts[a] += 3
            else:
                pts[h] += 1; pts[a] += 1

        table = sorted(teams, key=lambda t: (pts[t], gf[t] - ga[t], gf[t]), reverse=True)
        for i, t in enumerate(table, start=1):
            pos_hist[t][i] += 1
        top8, playoff = table[:8], table[8:24]
        for t in top8:
            reach[t]["top8"] += 1
            reach[t]["r16"] += 1
        for t in playoff:
            reach[t]["po"] += 1

        # Knockout playoff: seeded 9-16 vs 17-24 (9v24, 10v23, ...)
        po_winners = []
        for i in range(8):
            hi, lo = playoff[i], playoff[15 - i]     # hi = better league position
            for t in (hi, lo):
                games[t] += 2                        # two legs
            w = two_legged_winner(hi, lo, elo, rng)
            po_winners.append(w)
            reach[w]["r16"] += 1

        # R16: seed 1 meets the weakest surviving playoff winner, etc.
        # po_winners[0] came from the 9v24 tie (strongest slot) -> faces seed 8.
        r16_pairs = [(top8[i], po_winners[7 - i]) for i in range(8)]
        winners = []
        for a, b in r16_pairs:
            for t in (a, b):
                games[t] += 2
            w = two_legged_winner(a, b, elo, rng)
            winners.append(w)
            reach[w]["qf"] += 1

        # QF and SF: two legs each
        for stage in ("sf", "f"):
            nxt = []
            for i in range(0, len(winners), 2):
                a, b = winners[i], winners[i + 1]
                for t in (a, b):
                    games[t] += 2
                w = two_legged_winner(a, b, elo, rng)
                nxt.append(w)
                reach[w][stage] += 1
            winners = nxt

        # Final: single match
        for t in winners:
            games[t] += 1
        if len(winners) == 2:
            single_match_winner(winners[0], winners[1], elo, rng)

    qual = {t: {k: round(reach[t][k] / n_sims, 4)
                for k in ("top8", "po", "r16", "qf", "sf", "f")} for t in teams}
    exp = {t: round(games[t] / n_sims, 3) for t in teams}
    pos = {t: {p: round(c / n_sims, 4) for p, c in sorted(pos_hist[t].items())}
           for t in teams}
    return qual, exp, pos


# ── Self-test ─────────────────────────────────────────────────────────────────

def _self_test() -> None:
    print("Self-test: synthetic 36-team league phase (no files needed)\n")
    codes = [f"T{i:02d}" for i in range(1, 37)]
    # Descending strength so the ordering is checkable.
    elo = {c: 2050.0 - 12.0 * i for i, c in enumerate(codes)}
    rng = random.Random(1)
    fixtures, used = [], defaultdict(int)
    # Give everyone 8 opponents via a simple round-robin over 8 rounds.
    for md in range(1, 9):
        shifted = codes[md:] + codes[:md]
        for i in range(0, 36, 2):
            h, a = shifted[i], shifted[i + 1]
            if md % 2 == 0:
                h, a = a, h
            fixtures.append({"md": md, "home": h, "away": a})
            used[h] += 1; used[a] += 1
    assert all(v == 8 for v in used.values()), "every team must play 8"
    assert len(fixtures) == 144, len(fixtures)

    qual, exp, _ = simulate(fixtures, elo, {}, 1, 4000, seed=7)

    t8 = sum(q["top8"] for q in qual.values())
    po = sum(q["po"] for q in qual.values())
    r16 = sum(q["r16"] for q in qual.values())
    f = sum(q["f"] for q in qual.values())
    print(f"  sum top8 = {t8:.2f} (expect 8)    sum po = {po:.2f} (expect 16)")
    print(f"  sum r16  = {r16:.2f} (expect 16)   sum f  = {f:.2f} (expect 2)")
    assert abs(t8 - 8) < 0.05 and abs(po - 16) < 0.05
    assert abs(r16 - 16) < 0.05 and abs(f - 2) < 0.05
    assert qual["T01"]["top8"] > qual["T36"]["top8"], "stronger team must rank higher"
    print(f"\n  strongest T01: top8={qual['T01']['top8']:.2f} f={qual['T01']['f']:.3f} "
          f"exp_games={exp['T01']:.2f}")
    print(f"  weakest  T36: top8={qual['T36']['top8']:.2f} f={qual['T36']['f']:.3f} "
          f"exp_games={exp['T36']:.2f}")
    assert exp["T01"] > exp["T36"], "stronger team should play more matches"
    print("\n  ✓ all assertions passed")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=os.path.join(DATA, "ucl_fixtures.json"))
    ap.add_argument("--elo", default=os.path.join(DATA, "ucl_elo.csv"))
    ap.add_argument("--standings", default=None,
                    help="JSON {CODE:{pts,gf,ga,played}} for matchdays already played")
    ap.add_argument("--from-md", type=int, default=1,
                    help="First matchday still to be played (default 1)")
    ap.add_argument("--sims", type=int, default=20000)
    ap.add_argument("--out", default=OUTPUT)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        _self_test()
        return

    for path, what in ((args.fixtures, "fixtures"), (args.elo, "Elo")):
        if not os.path.exists(path):
            raise SystemExit(
                f"Missing {what} file: {path}\n"
                "Fixtures come from the league-phase draw; Elo from "
                "`python3 scripts/fetch_clubelo.py`."
            )

    fixtures = load_fixtures(args.fixtures)
    elo = load_elo(args.elo)
    standings = {}
    if args.standings and os.path.exists(args.standings):
        standings = json.load(open(args.standings))

    teams = sorted({t for f in fixtures for t in (f["home"], f["away"])})
    missing = [t for t in teams if t not in elo]
    if missing:
        print(f"  [WARN] No Elo for {missing} — defaulting to 1500. "
              f"Add them to CLUBELO_NAME_TO_CODE or the Elo CSV.")

    print(f"Simulating {args.sims} seasons from MD{args.from_md} "
          f"({len(teams)} teams, {len(fixtures)} fixtures)...")
    qual, exp, pos = simulate(fixtures, elo, standings, args.from_md, args.sims)

    out = {"sims": args.sims, "from_md": args.from_md,
           "QUAL_PROBS": qual, "EXP_GAMES": exp, "FINISH_POS": pos}
    json.dump(out, open(args.out, "w"), indent=2)
    print(f"\nSaved → {args.out}")

    print("\n── paste-ready ──\nQUAL_PROBS = {")
    for t in sorted(qual, key=lambda x: -qual[x]["top8"]):
        q = qual[t]
        print(f'    "{t}": {{"top8": {q["top8"]}, "po": {q["po"]}, "r16": {q["r16"]}, '
              f'"qf": {q["qf"]}, "sf": {q["sf"]}, "f": {q["f"]}}},')
    print("}\n\nEXP_GAMES = {")
    for t in sorted(exp, key=lambda x: -exp[x]):
        print(f'    "{t}": {exp[t]},')
    print("}")


if __name__ == "__main__":
    main()
