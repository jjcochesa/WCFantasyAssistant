"""
Predicted starting XIs for the UEFA Champions League, keyed by 3-letter club code.

Names must match the UEFA fantasy feed (data/ucl_players.json) after
normalisation — use the exact roster spellings. These XIs are AUTHORITATIVE:
a player in the XI is projected STARTER_MINUTES, everyone else at that club
gets BENCH_MINUTES (no blending with past rotation history — the point of
hand-feeding a lineup is to override what the data thinks).
Clubs not listed fall back to the stats pipeline (starter_rate + real minutes).

Note for UCL: unlike the World Cup game, UEFA lets you substitute BETWEEN days
within a matchday — up to 4 players per day, and only for players whose clubs
have not yet played. So bench players still score and bench depth is worth more
here than a pure starters-only view suggests, but it is capped, not unlimited,
and on MD8 (and the final) every match kicks off together so there are no
in-matchday subs at all.

Refill each matchday once lineups are known.
"""

STARTER_MINUTES = 80   # projected minutes for a predicted starter
BENCH_MINUTES   = 20   # projected minutes for a non-starter at a club with a known XI

PREDICTED_XI: dict[str, list[str]] = {}
