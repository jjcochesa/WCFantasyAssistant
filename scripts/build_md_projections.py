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


# Absolute cuts, kept for reference. These were fitted to the Elo model's own
# threat scale; a bookmaker board lives on a different scale, and applying these
# to it puts 62% of all fixtures in bands 4-5, which is not a usable rating.
ABSOLUTE_CUTS = [0.45, 0.62, 0.85, 1.20]

# Share of fixtures in each band. FDR is a RELATIVE rating — "how hard is this
# fixture compared with the others available this season" — so the bands are cut
# at quantiles of the actual threat distribution rather than at fixed values.
# This keeps the scale meaningful whatever the source numbers look like.
BAND_SHARES = [0.15, 0.20, 0.30, 0.20, 0.15]


def band_cuts(threats: list) -> list:
    """Threat values at which the band changes, from the observed distribution."""
    xs = sorted(threats)
    cuts, run = [], 0.0
    for share in BAND_SHARES[:-1]:
        run += share
        cuts.append(xs[min(int(run * len(xs)), len(xs) - 1)])
    return cuts


def fdr_band(threat: float, cuts: list = None) -> int:
    """Opponent threat -> 1 (easiest) to 5 (hardest)."""
    for i, c in enumerate(cuts if cuts is not None else ABSOLUTE_CUTS):
        if threat < c:
            return i + 1
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

    schedule, home, goals, cs, source = {}, {}, {}, {}, {}
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
        schedule[md], home[md] = smd, sorted(hmd)
        goals[md], cs[md] = gmd, cmd
        source[md] = "board" if b else "model"

    # FDR last, once every matchday's goals/CS are settled: the bands are cut on
    # the whole league phase, so a 2 in MD1 means the same as a 2 in MD7.
    def threat(md, club):
        return (goals[md][club] + cs[md][club]) / 2.0

    cuts = band_cuts([threat(md, opp) for md in schedule
                      for opp in schedule[md].values()])
    fdr, model_fdr = {}, {}
    for md in sorted(FIXTURES):
        fdr[md] = {club: fdr_band(threat(md, opp), cuts)
                   for club, opp in schedule[md].items()}
        model_fdr[md] = dict(fdr[md])   # kept separate so a later import can be
                                        # compared against the model, not itself

    payload = {
        "dates": DATES,
        "schedule": schedule,
        "home": home,
        "proj_goals": goals,
        "cs_pct": cs,
        "fdr": fdr,
        "fdr_model": model_fdr,
        "source": source,
        "fdr_cuts": [round(c, 3) for c in cuts],
        "_note": ("goals/CS are Elo-derived unless a bookmaker board was supplied "
                  "for that matchday; see 'source'. FDR bands are cut at quantiles "
                  "of the league phase's own threat distribution, so the rating is "
                  "relative to the fixtures actually available"),
    }
    json.dump(payload, open(args.out, "w"), indent=2)
    print(f"Saved → {args.out}")
    for md in sorted(FIXTURES):
        top = sorted(goals[md].items(), key=lambda kv: -kv[1])[:3]
        pretty = ", ".join(f"{c} {g:.2f}" for c, g in top)
        print(f"  MD{md} ({source[md]:5s}) highest projected goals: {pretty}")


if __name__ == "__main__":
    main()
