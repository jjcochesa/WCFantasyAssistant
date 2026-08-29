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

Transfers are now modelled from the real rules: 2 free per league matchday,
at most 1 carried forward, and playing a chip forfeits any carry. Each matchday
the squad may swap up to that many players toward the optimum for the remaining
window, which is what stops the comparison from simply rewarding whoever
wildcards earliest.

Assumptions worth knowing:
  * Bench is not scored. Within a matchday you may sub out up to SUBS_PER_DAY
    (4) players per day, for players whose clubs have not yet played, so real
    bench depth adds points this does not count. That option disappears on MD8,
    where every match kicks off at once.
  * MD8 is excluded by default (--last-md 7) because the unlimited-transfers
    chip covers it, making the squad you carry into it irrelevant.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from scoring_rules import (BUDGET_GROUP, SQUAD_SLOTS, MAX_PER_CLUB_BY_STAGE,  # noqa: E402
                           FREE_TRANSFERS, MAX_CARRIED_TRANSFERS, XI_MIN, XI_MAX,
                           XI_SIZE)



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


def score_with_transfers(squad: list, window: list, pool: list, budget: float,
                         cap: int, carry_in: int = 0) -> float:
    """Play a squad through a window, spending the real free-transfer allowance
    each matchday on the swaps that most improve the rest of the window."""
    squad = list(squad)
    spent = sum(p["price"] for p in squad)
    banked = carry_in
    total = 0.0
    for i, md in enumerate(window):
        free = FREE_TRANSFERS.get(md)
        allowance = 99 if free is None else min(free + banked, free + MAX_CARRIED_TRANSFERS)
        remaining = window[i:]
        rest = window[i + 1:]

        made = 0
        while made < allowance:
            names = {p["name"] for p in squad}
            counts = {}
            for p in squad:
                counts[p["team_code"]] = counts.get(p["team_code"], 0) + 1
            # value a swap by what it adds over the matchdays still to come
            def val(p, mds):
                return sum(p.get(f"xPts_md{m}", 0.0) for m in mds)
            best = None
            for out in squad:
                for inn in pool:
                    if inn["name"] in names or inn["pos"] != out["pos"]:
                        continue
                    if spent - out["price"] + inn["price"] > budget:
                        continue
                    if inn["team_code"] != out["team_code"] and \
                       counts.get(inn["team_code"], 0) >= cap:
                        continue
                    gain = val(inn, remaining) - val(out, remaining)
                    if gain > 0 and (best is None or gain > best[0]):
                        best = (gain, out, inn)
            if best is None:
                break
            _, out, inn = best
            squad = [inn if p is out else p for p in squad]
            spent += inn["price"] - out["price"]
            made += 1

        banked = min(MAX_CARRIED_TRANSFERS, allowance - made) if free is not None else 0
        total += best_xi(squad, f"xPts_md{md}")
        _ = rest
    return total


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
        pre_pts = score_with_transfers(s_pre, pre, rows, args.budget, cap) if pre else 0.0
        post_pts = score_with_transfers(s_post, post, rows, args.budget, cap)
        pts = pre_pts + post_pts
        results[w] = pts
        print(f"Wildcard at MD{w}:  opener MD{pre[0]}-MD{pre[-1]} ({pre_pts:.1f}) + "
              f"WC squad MD{post[0]}-MD{post[-1]} ({post_pts:.1f})  ->  TOTAL {pts:.1f}")

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
