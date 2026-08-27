#!/usr/bin/env python3
"""
Expand data/ucl_draw.py into the 144 league-phase fixtures and validate them.

    python3 scripts/build_draw.py            # validate + write data/ucl_fixtures.json
    python3 scripts/build_draw.py --check    # validate only

Validation is the point: the draw is hand-transcribed from the published grids,
and every tie appears twice (home for one club, away for the other), so any
mistyped opponent shows up as an asymmetry rather than sneaking into the model.

Matchday numbers are NOT known until UEFA publishes the calendar, so every
fixture is written with md=0. The league-phase simulation doesn't care — only
the set of 144 ties affects the final table. Matchdays matter only for the
horizon planner (best squad for MD1-MD3), which stays disabled until then.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
from data.ucl_draw import CLUBS, POTS, DRAW  # noqa: E402

OUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ucl_fixtures.json"))


def validate() -> list:
    """Returns the list of fixtures, or exits with every problem found."""
    errors = []

    # Club set / pot structure
    if len(CLUBS) != 36:
        errors.append(f"Expected 36 clubs, got {len(CLUBS)}")
    pot_of = {}
    for pot, members in POTS.items():
        if len(members) != 9:
            errors.append(f"Pot {pot} has {len(members)} clubs, expected 9")
        for c in members:
            if c in pot_of:
                errors.append(f"{c} appears in more than one pot")
            pot_of[c] = pot
    for c in CLUBS:
        if c not in pot_of:
            errors.append(f"{c} is in CLUBS but not in any pot")
    for c in DRAW:
        if c not in CLUBS:
            errors.append(f"DRAW has unknown club {c}")
    for c in CLUBS:
        if c not in DRAW:
            errors.append(f"{c} has no DRAW entry")

    # Per-club shape: 4 home + 4 away, one opponent per pot on each side,
    # never the same club twice, never itself.
    for club, entry in DRAW.items():
        if entry.get("pot") != pot_of.get(club):
            errors.append(f"{club}: pot {entry.get('pot')} disagrees with POTS "
                          f"({pot_of.get(club)})")
        h, a = entry.get("h", []), entry.get("a", [])
        if len(h) != 4 or len(a) != 4:
            errors.append(f"{club}: expected 4 home + 4 away, got {len(h)}+{len(a)}")
            continue
        opponents = h + a
        if club in opponents:
            errors.append(f"{club}: drawn against itself")
        if len(set(opponents)) != 8:
            dupes = {o for o in opponents if opponents.count(o) > 1}
            errors.append(f"{club}: duplicate opponent(s) {sorted(dupes)}")
        for side, lst in (("home", h), ("away", a)):
            for i, opp in enumerate(lst, start=1):
                if opp not in CLUBS:
                    errors.append(f"{club}: unknown {side} opponent {opp!r}")
                elif pot_of.get(opp) != i:
                    errors.append(f"{club}: {side} slot {i} should be a Pot {i} club, "
                                  f"but {opp} is Pot {pot_of.get(opp)}")

    # Symmetry: A hosting B must appear as B away to A.
    home_pairs, away_pairs = set(), set()
    for club, entry in DRAW.items():
        for opp in entry.get("h", []):
            home_pairs.add((club, opp))
        for opp in entry.get("a", []):
            away_pairs.add((opp, club))       # normalise to (home, away)
    for pair in sorted(home_pairs - away_pairs):
        errors.append(f"{pair[0]} lists {pair[1]} at home, but {pair[1]} does not "
                      f"list {pair[0]} away")
    for pair in sorted(away_pairs - home_pairs):
        errors.append(f"{pair[1]} lists {pair[0]} away, but {pair[0]} does not "
                      f"list {pair[1]} at home")

    if errors:
        print(f"VALIDATION FAILED — {len(errors)} problem(s):\n")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    fixtures = [{"md": 0, "home": h, "away": a} for (h, a) in sorted(home_pairs)]
    if len(fixtures) != 144:
        print(f"VALIDATION FAILED — {len(fixtures)} fixtures, expected 144")
        sys.exit(1)
    return fixtures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Validate without writing")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    fixtures = validate()
    counts = {c: 0 for c in CLUBS}
    for f in fixtures:
        counts[f["home"]] += 1
        counts[f["away"]] += 1
    assert all(v == 8 for v in counts.values())

    print(f"✓ 36 clubs, 4 pots, {len(fixtures)} fixtures — every club plays 8, "
          f"4 home / 4 away, one per pot each way, all ties symmetric")

    if args.check:
        return
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)
    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
