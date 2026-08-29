#!/usr/bin/env python3
"""
Validate the league-phase calendar against the draw and emit dated fixtures.

    python3 scripts/build_calendar.py          # validate + write data/ucl_fixtures.json
    python3 scripts/build_calendar.py --check  # validate only

The calendar is hand-transcribed from UEFA's schedule graphics, so it is checked
against the independently-validated draw rather than trusted:

  1. every matchday has 18 fixtures and each club appears exactly once in it
  2. every (home, away) pair exists in the draw with the SAME home/away
  3. the 144 draw ties are each used exactly once across the eight matchdays

A misread club name cannot satisfy all three at once — it will either duplicate
a club inside a matchday, fail to match a drawn tie, or leave a tie unplayed.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
from data.ucl_draw import CLUBS, DRAW                      # noqa: E402
from data.ucl_calendar import DATES, FIXTURES              # noqa: E402

OUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ucl_fixtures.json"))


def drawn_ties() -> set:
    """The 144 (home, away) pairs from the validated draw."""
    ties = set()
    for club, entry in DRAW.items():
        for opp in entry["h"]:
            ties.add((club, opp))
    return ties


def validate() -> list:
    errors = []
    ties = drawn_ties()
    seen = {}

    if sorted(FIXTURES) != list(range(1, 9)):
        errors.append(f"Expected matchdays 1-8, got {sorted(FIXTURES)}")

    for md in sorted(FIXTURES):
        fx = FIXTURES[md]
        if len(fx) != 18:
            errors.append(f"MD{md}: {len(fx)} fixtures, expected 18")

        # every club exactly once per matchday
        appear = {}
        for h, a in fx:
            for c in (h, a):
                if c not in CLUBS:
                    errors.append(f"MD{md}: unknown club {c!r}")
                appear[c] = appear.get(c, 0) + 1
        for c, n in sorted(appear.items()):
            if n > 1:
                errors.append(f"MD{md}: {c} appears {n} times")
        missing = sorted(set(CLUBS) - set(appear))
        if missing:
            errors.append(f"MD{md}: not playing: {missing}")

        # each fixture must be a real drawn tie, same orientation
        for h, a in fx:
            if (h, a) not in ties:
                if (a, h) in ties:
                    errors.append(f"MD{md}: {h} v {a} is drawn the other way round "
                                  f"({a} host {h})")
                else:
                    errors.append(f"MD{md}: {h} v {a} is not a drawn tie")
            elif (h, a) in seen:
                errors.append(f"MD{md}: {h} v {a} already played on MD{seen[(h, a)]}")
            else:
                seen[(h, a)] = md

        if md not in DATES or not DATES[md]:
            errors.append(f"MD{md}: no dates")

    unplayed = sorted(ties - set(seen))
    for h, a in unplayed:
        errors.append(f"drawn tie never played: {h} v {a}")

    if errors:
        print(f"VALIDATION FAILED — {len(errors)} problem(s):\n")
        for e in errors[:40]:
            print(f"  - {e}")
        if len(errors) > 40:
            print(f"  ... and {len(errors) - 40} more")
        sys.exit(1)

    return [{"md": md, "home": h, "away": a}
            for md in sorted(FIXTURES) for (h, a) in FIXTURES[md]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    fixtures = validate()
    print(f"✓ 8 matchdays x 18 fixtures = {len(fixtures)}; every club plays once per "
          f"matchday, every tie matches the draw's home/away, all 144 ties used once")
    for md in sorted(DATES):
        print(f"    MD{md}: {', '.join(DATES[md])}")

    if args.check:
        return
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)
    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
