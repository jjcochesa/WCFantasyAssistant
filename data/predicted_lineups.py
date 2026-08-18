"""
Predicted starting XIs for the UEFA Champions League, keyed by 3-letter club code.

Names must match the UEFA fantasy feed (data/ucl_players.json) after
normalisation — use the exact roster spellings. These XIs are AUTHORITATIVE:
a player in the XI is projected STARTER_MINUTES, everyone else at that club
gets BENCH_MINUTES (no blending with past rotation history — the point of
hand-feeding a lineup is to override what the data thinks).
Clubs not listed fall back to the stats pipeline (starter_rate + real minutes).

Note for UCL: unlike the World Cup game, UEFA allows unlimited substitutions
BETWEEN days within a matchday, so bench players still score. Bench depth is
worth more here than a pure starters-only view suggests.

Refill each matchday once lineups are known.
"""

STARTER_MINUTES = 80   # projected minutes for a predicted starter
BENCH_MINUTES   = 20   # projected minutes for a non-starter at a club with a known XI

PREDICTED_XI: dict[str, list[str]] = {}
