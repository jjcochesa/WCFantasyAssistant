#!/usr/bin/env python3
"""
Compare Wildcard timings: how much does playing it before MD3 vs MD4 (or any
other matchday) actually gain?

    python3 scripts/compare_wildcard.py
    python3 scripts/compare_wildcard.py --options 3,4,5 --last-md 7

For each candidate matchday W the season splits into two windows: the opening
squad covers MD1..W-1, the Wildcard squad covers W..LAST. Each window gets its
own optimised 15 under the real rules (EUR 100m, 2 GK / 5 DEF / 5 MID / 3 FWD,
max 3 per club), and every squad is scored by its best legal XI each matchday.

Assumptions worth knowing:
  * No free transfers between matchdays. Real transfers narrow every gap below,
    so treat the numbers as an upper bound on what the timing is worth.
  * Bench is not scored. UCL allows unlimited substitutions between days inside
    a matchday, so real bench depth adds points this does not count.
  * MD8 is excluded by default (--last-md 7) because the unlimited-transfers
    chip covers it, making the squad you carry into it irrelevant.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from scoring_rules import BUDGET_GROUP, SQUAD_SLOTS, MAX_PER_CLUB_BY_STAGE  # noqa: E402

# A legal XI: exactly 1 GK, and at least this many outfield by position.
XI_MIN = {"GK": 1, "DEF": 3, "MID": 2, "FWD": 1}
XI_MAX = {"GK": 1, "DEF": 5, "MID": 5, "FWD": 3}
XI_SIZE = 11


def best_xi(players: list, col: str) -> float:
    """Highest-scoring legal XI from a squad for one matchday."""
    by_pos = {p: sorted((x for x in players if x["pos"] == p),
                        key=lambda x: -x[col]) for p in XI_MIN}
    xi, total = {}, 0.0
    for pos, n in XI_MIN.items():                 # fill the minimums first
        take = by_pos[pos][:n]
        xi[pos] = len(take)
        total += sum(x[col] for x in take)
    # then fill the remaining slots with the best players still eligible
    pool = []
    for pos, taken in xi.items():
        pool += [(x[col], pos) for x in by_pos[pos][taken:]]
    pool.sort(reverse=True)
    for val, pos in pool:
        if sum(xi.values()) >= XI_SIZE:
            break
        if xi[pos] < XI_MAX[pos]:
            xi[pos] += 1
            total += val
    return total


def optimise(rows: list, window: list, budget: float, cap: int) -> list:
    """Greedy 15 maximising total points over `window`, respecting budget,
    squad shape and the per-club cap. Reserves enough budget to fill the
    remaining slots at their cheapest, so it can't paint itself into a corner."""
    col = "_w"
    for r in rows:
        r[col] = sum(r.get(f"xPts_md{m}", 0.0) for m in window)
    cheapest = {p: sorted((r["price"] for r in rows if r["pos"] == p))
                for p in SQUAD_SLOTS}

    picked, filled, spent, per_club = [], {p: 0 for p in SQUAD_SLOTS}, 0.0, {}
    for r in sorted(rows, key=lambda x: -x[col]):
        pos = r["pos"]
        if filled[pos] >= SQUAD_SLOTS[pos]:
            continue
        if per_club.get(r["team_code"], 0) >= cap:
            continue
        reserve = 0.0
        for p, need in SQUAD_SLOTS.items():
            still = need - filled[p] - (1 if p == pos else 0)
            if still > 0:
                reserve += sum(cheapest[p][:still])
        if spent + r["price"] + reserve > budget:
            continue
        picked.append(r)
        filled[pos] += 1
        spent += r["price"]
        per_club[r["team_code"]] = per_club.get(r["team_code"], 0) + 1
        if sum(filled.values()) == sum(SQUAD_SLOTS.values()):
            break
    return picked


def score(squad: list, window: list) -> float:
    return sum(best_xi(squad, f"xPts_md{m}") for m in window)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--options", default="3,4", help="Candidate Wildcard matchdays")
    ap.add_argument("--last-md", type=int, default=7,
                    help="Last matchday the Wildcard squad must cover (default 7; "
                         "MD8 is assumed covered by the unlimited-transfers chip)")
    ap.add_argument("--budget", type=float, default=BUDGET_GROUP)
    args = ap.parse_args()

    import data_engine as de
    df = de.load_data(use_squads=True, enrich_with_api=False)
    df = df[df["in_round"]] if "in_round" in df.columns else df
    keep = ["name", "pos", "team_code", "price"] + \
           [c for c in df.columns if c.startswith("xPts_md")]
    rows = df[keep].to_dict("records")
    cap = MAX_PER_CLUB_BY_STAGE["league"]

    print(f"\npool {len(rows)} players | budget EUR {args.budget:.0f}m | max {cap}/club "
          f"| scoring MD1-MD{args.last_md}\n")

    results = {}
    for w in [int(x) for x in args.options.split(",")]:
        pre, post = list(range(1, w)), list(range(w, args.last_md + 1))
        s_pre = optimise(rows, pre, args.budget, cap) if pre else []
        s_post = optimise(rows, post, args.budget, cap)
        pts = (score(s_pre, pre) if pre else 0.0) + score(s_post, post)
        results[w] = pts
        print(f"Wildcard at MD{w}:  opening squad covers MD{pre[0]}-MD{pre[-1]} "
              f"({score(s_pre, pre):.1f} pts), WC squad covers MD{post[0]}-MD{post[-1]} "
              f"({score(s_post, post):.1f} pts)  ->  TOTAL {pts:.1f}")

    best = max(results, key=results.get)
    print(f"\nBest timing: MD{best}")
    for w, pts in sorted(results.items()):
        if w != best:
            print(f"  vs MD{w}: {results[best] - pts:+.1f} pts over the window")

    # How much does the fixture landscape actually move at each split point? If
    # the same clubs have the good fixtures either side, the Wildcard has little
    # to re-optimise toward and the timing barely matters.
    import data.team_stats as ts
    print("\nFixture-landscape shift at each split (mean |FDR change| per club,")
    print("comparing the window before the Wildcard with the window after):")
    for w in [int(x) for x in args.options.split(",")]:
        pre, post = list(range(1, w)), list(range(w, args.last_md + 1))
        if not pre:
            continue
        deltas = []
        for c in ts.TEAM_NAMES:
            a = sum(ts.get_md_fdr(m, c) for m in pre) / len(pre)
            b = sum(ts.get_md_fdr(m, c) for m in post) / len(post)
            deltas.append(abs(a - b))
        print(f"  MD{w}: {sum(deltas)/len(deltas):.2f}")


if __name__ == "__main__":
    main()
