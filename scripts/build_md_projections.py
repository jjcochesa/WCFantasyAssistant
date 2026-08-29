#!/usr/bin/env python3
"""
Build per-matchday projected goals, clean-sheet odds and FDR for the league
phase, and write them to data/ucl_md_projections.json (loaded by
data/team_stats.py).

    python3 scripts/build_md_projections.py

Numbers come from the club ratings in data/ucl_elo.csv via the same Elo ->
Poisson model the league-phase simulation uses, including home advantage. They
are a stand-in: when a bookmaker-derived board (goals / CS% per club per
matchday) is available, pass it with --board and those values are used instead,
with the model only filling gaps.

    python3 scripts/build_md_projections.py --board data/md1_board.json

--board expects {"1": {"BAR": {"goals": 2.4, "cs": 0.55}, ...}, ...}
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))

from data.ucl_calendar import DATES, FIXTURES          # noqa: E402
import scripts.build_league_phase as lp                # noqa: E402

OUT = os.path.join(DATA, "ucl_md_projections.json")


def fdr_band(threat: float) -> int:
    """Same banding the rest of the app uses: opponent threat -> 1 (easiest) to 5."""
    if threat < 0.45:
        return 1
    if threat < 0.62:
        return 2
    if threat < 0.85:
        return 3
    if threat < 1.20:
        return 4
    return 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elo", default=os.path.join(DATA, "ucl_elo.csv"))
    ap.add_argument("--board", help="Optional bookmaker board JSON to override the model")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    elo = lp.load_elo(args.elo)
    board = {}
    if args.board:
        board = {int(k): v for k, v in json.load(open(args.board)).items()}

    schedule, home, goals, cs, fdr, source, model_fdr = {}, {}, {}, {}, {}, {}, {}
    for md in sorted(FIXTURES):
        smd, hmd, gmd, cmd = {}, [], {}, {}
        b = board.get(md, {})
        for h, a in FIXTURES[md]:
            smd[h], smd[a] = a, h
            hmd.append(h)
            lam_h, lam_a = lp.lambdas(elo.get(h, 1500.0), elo.get(a, 1500.0))
            # A supplied board wins; the model only fills what it doesn't cover.
            gmd[h] = round(float(b.get(h, {}).get("goals", lam_h)), 2)
            gmd[a] = round(float(b.get(a, {}).get("goals", lam_a)), 2)
            cmd[h] = round(float(b.get(h, {}).get("cs", math.exp(-gmd[a]))), 3)
            cmd[a] = round(float(b.get(a, {}).get("cs", math.exp(-gmd[h]))), 3)
        # FDR from the opponent's threat, once goals/CS are settled for the round
        fmd = {}
        for club, opp in smd.items():
            fmd[club] = fdr_band((gmd[opp] + cmd[opp]) / 2.0)
        schedule[md], home[md] = smd, sorted(hmd)
        goals[md], cs[md], fdr[md] = gmd, cmd, fmd
        model_fdr[md] = dict(fmd)   # kept separate so a later import can be
                                    # compared against the model, not itself
        source[md] = "board" if b else "model"

    payload = {
        "dates": DATES,
        "schedule": schedule,
        "home": home,
        "proj_goals": goals,
        "cs_pct": cs,
        "fdr": fdr,
        "fdr_model": model_fdr,
        "source": source,
        "_note": ("goals/CS are Elo-derived unless a bookmaker board was supplied "
                  "for that matchday; see 'source'"),
    }
    json.dump(payload, open(args.out, "w"), indent=2)
    print(f"Saved → {args.out}")
    for md in sorted(FIXTURES):
        top = sorted(goals[md].items(), key=lambda kv: -kv[1])[:3]
        pretty = ", ".join(f"{c} {g:.2f}" for c, g in top)
        print(f"  MD{md} ({source[md]:5s}) highest projected goals: {pretty}")


if __name__ == "__main__":
    main()
