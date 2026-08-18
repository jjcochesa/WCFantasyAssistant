# ⚽ UCL Fantasy Assistant

Fantasy assistant for the **official UEFA Champions League Fantasy** game
(gaming.uefa.com) — projections, player rankings, FDR, qualification odds and a
squad builder. Streamlit app + local data pipeline.

> This project began life as the WC 2026 Fantasy Assistant. It is now fully in
> Champions League mode — the World Cup data and scoring have been replaced
> (they remain in git history). Awaiting the 2026-27 league-phase draw.

## Competition format (UCL 2026-27)

| Stage | Teams | Notes |
|---|---|---|
| League phase | 36 | MD1–MD8, single league table, each team plays 8 different opponents |
| Knockout playoff (PO) | 16 | Table positions 9–24; two legs. Positions 1–8 skip straight to R16 |
| Round of 16 → Final | 16 → 2 | R16, QF, SF two-legged; Final single match |

Fantasy matchdays: MD1–MD8, then PO, R16, QF, SF, F — the same
one-round-at-a-time cadence this tool already uses.

## Architecture (inherited from the WC edition)

- `app.py` — Streamlit UI: rankings, fixtures/FDR, squad builder, scouts/value,
  draft mode, accumulated real stats.
- `data_engine.py` — projection model: per-90 rates (club + NT/UCL blend),
  empirical-Bayes overlay of real tournament form, minutes from predicted XIs,
  Poisson team model → per-player expected points under the official scoring.
- `data/team_stats.py` — one round at a time: PROJ_GOALS / CS_PCT / FDR /
  FIXTURES / QUAL_PROBS / EXP_GAMES per team.
- `data/predicted_lineups.py` — manager-supplied XIs (authoritative 80'/20').
- `scripts/` — local fetchers (API keys are IP-locked to the owner's machine):
  - `fetch_wc_stats.py` — accumulated per-player stats from API-Football
    (`--league 2 --season 2026` pulls Champions League → `data/ucl_stats.json`).
  - `build_league_phase.py` — **the UCL core**: Monte-Carlo of the 36-team
    league table + seeded knockout bracket → P(top-8) / P(playoff) / reach
    probabilities and expected remaining matches (both legs counted).
    `--self-test` validates the math with no files needed.
  - `build_r32.py` — odds → de-vig → Poisson lambdas → goals/CS%/FDR for a
    single round (kept; works for any round with a bookmaker board).
  - `matchday_refresh.sh` — one command: stats + Elo + league sim.
  - `fetch_clubelo.py` — club Elo ratings from api.clubelo.com (free) for the
    knockout Monte-Carlo (replaces national-team eloratings.net).
  - `fetch_ucl_feed.py` — official UEFA Fantasy player feed (prices, positions,
    ownership) → `data/ucl_players.json`.

## Data sources per input

| Input | WC edition | UCL edition |
|---|---|---|
| Player pool / prices | FIFA fantasy feed | UEFA fantasy feed (`fetch_ucl_feed.py`) |
| Team goals / CS% | FPLJoe screenshots + API-Football odds | same (league id 2) |
| Strength for future rounds | eloratings.net (national) | **clubelo.com** (`fetch_clubelo.py`) |
| Accumulated form | API-Football league 1 | API-Football league 2 |

## UCL pivot checklist

- [x] Generalize stats fetcher to any league/season
- [x] ClubElo fetcher
- [x] UEFA fantasy feed fetcher (endpoint verified once the 26-27 game opens)
- [x] `data/team_stats.py` restructured for UCL (stages MD1–8 → PO → R16 → QF
      → SF → F, two-legged tie handling, pots, `top8`/`po` qualification keys).
      Team dicts empty until the draw — the app shows an "awaiting draw" banner.
- [x] League-phase qualification model (`build_league_phase.py`): P(top-8),
      P(9–24 playoff), P(out), reach probabilities and expected remaining
      matches from a league-table + seeded-bracket Monte-Carlo
- [ ] Fill the 36 clubs, pots and 144 fixtures after the draw (late August)
- [ ] Swap the player pool from the FIFA feed to the UEFA feed in `data_engine`
      (needs one real `fetch_ucl_feed.py` pull to confirm the JSON shape)
- [x] UEFA scoring rules in `scoring_rules.py` (goal 6/6/5/4, assist 3,
      CS 4/4/1, −1 per 2 conceded, recoveries via tackles proxy)
- [x] Squad rules: €105m budget, per-club cap by stage (3 league → 11 final);
      transfer allowances TBC from the in-game rules when 26-27 opens
- [ ] Rename repo → `UCLFantasyAssistant` (GitHub Settings → General → Rename;
      old URLs auto-redirect, then `git remote set-url origin
      https://github.com/jjcochesa/UCLFantasyAssistant.git`)

## Workflow each matchday (unchanged)

1. Owner runs `./scripts/matchday_refresh.sh KEY [FROM_MD]` locally (API key is
   IP-restricted) and pushes the JSON outputs.
2. FDR / goals / CS% board (FPLJoe or equivalent) lands as a screenshot and is
   wired into `data/team_stats.py`.
3. Manager supplies predicted XIs → authoritative 80'/20' minutes.
4. App re-ranks; squad builder picks only alive-team predicted starters.
