# FBref Download Guide

## How to save a page from FBref

1. Open the URL in your browser
2. Press **Ctrl+S** (Windows) or **Cmd+S** (Mac)
3. In the save dialog, select format: **"Webpage, HTML Only"** (not "Complete")
4. Save it into the `data/fbref/` folder with the exact filename shown below

That's it. No need to find any export button.

---

## Part 1 — Club Stats (2025/26)

### Best option: Big 5 European Leagues (one file = PL + La Liga + Bundesliga + Serie A + Ligue 1)

| Save as | URL |
|---|---|
| `Big5_standard.html` | https://fbref.com/en/comps/Big5/stats/players/Big-5-European-Leagues-Stats |
| `Big5_shooting.html` | https://fbref.com/en/comps/Big5/shooting/players/Big-5-European-Leagues-Stats |

> These two files alone cover ~60% of all WC 2026 players.

---

### Other leagues (each adds more players)

| Save as | URL |
|---|---|
| `club_Saudi_standard.html` | https://fbref.com/en/comps/70/2025-2026/stats/2025-2026-Saudi-Pro-League-Stats |
| `club_Saudi_shooting.html` | https://fbref.com/en/comps/70/2025-2026/shooting/2025-2026-Saudi-Pro-League-Stats |
| `club_Eredivisie_standard.html` | https://fbref.com/en/comps/23/2025-2026/stats/2025-2026-Eredivisie-Stats |
| `club_Eredivisie_shooting.html` | https://fbref.com/en/comps/23/2025-2026/shooting/2025-2026-Eredivisie-Stats |
| `club_PrimeiraLiga_standard.html` | https://fbref.com/en/comps/32/2025-2026/stats/2025-2026-Primeira-Liga-Stats |
| `club_PrimeiraLiga_shooting.html` | https://fbref.com/en/comps/32/2025-2026/shooting/2025-2026-Primeira-Liga-Stats |
| `club_SuperLig_standard.html` | https://fbref.com/en/comps/26/2025-2026/stats/2025-2026-Super-Lig-Stats |
| `club_SuperLig_shooting.html` | https://fbref.com/en/comps/26/2025-2026/shooting/2025-2026-Super-Lig-Stats |
| `club_Scottish_standard.html` | https://fbref.com/en/comps/40/2025-2026/stats/2025-2026-Scottish-Premiership-Stats |
| `club_Scottish_shooting.html` | https://fbref.com/en/comps/40/2025-2026/shooting/2025-2026-Scottish-Premiership-Stats |
| `club_Belgian_standard.html` | https://fbref.com/en/comps/37/2025-2026/stats/2025-2026-Belgian-Pro-League-Stats |
| `club_Belgian_shooting.html` | https://fbref.com/en/comps/37/2025-2026/shooting/2025-2026-Belgian-Pro-League-Stats |
| `club_MLS_standard.html` | https://fbref.com/en/comps/22/2025/stats/2025-Major-League-Soccer-Stats |
| `club_MLS_shooting.html` | https://fbref.com/en/comps/22/2025/shooting/2025-Major-League-Soccer-Stats |
| `club_LigaMX_standard.html` | https://fbref.com/en/comps/31/2025-2026/stats/2025-2026-Liga-MX-Stats |
| `club_LigaMX_shooting.html` | https://fbref.com/en/comps/31/2025-2026/shooting/2025-2026-Liga-MX-Stats |
| `club_BrazilA_standard.html` | https://fbref.com/en/comps/24/2025/stats/2025-Serie-A-Stats |
| `club_BrazilA_shooting.html` | https://fbref.com/en/comps/24/2025/shooting/2025-Serie-A-Stats |
| `club_Argentina_standard.html` | https://fbref.com/en/comps/21/2025/stats/2025-Primera-Division-Stats |
| `club_Argentina_shooting.html` | https://fbref.com/en/comps/21/2025/shooting/2025-Primera-Division-Stats |

---

## Part 2 — National Team Stats

For each competition, save the **Player Standard Stats** page.

| Save as | Search on FBref for |
|---|---|
| `nt_UEFA_WC.html` | "UEFA World Cup Qualifying 2026" → Stats → Player Standard Stats |
| `nt_CONMEBOL_WC.html` | "CONMEBOL World Cup Qualifying 2026" → Stats |
| `nt_CAF_WC.html` | "CAF World Cup Qualifying 2026" → Stats |
| `nt_CONCACAF_WC.html` | "CONCACAF World Cup Qualifying 2026" → Stats |
| `nt_AFC_WC.html` | "AFC World Cup Qualifying 2026" → Stats |
| `nt_AFCON2025.html` | "Africa Cup of Nations 2025" → Stats |
| `nt_CopaAmerica2024.html` | "Copa América 2024" → Stats |
| `nt_UEFANationsLeague.html` | "UEFA Nations League 2024-25" → Stats |

---

## After saving files

```bash
pip install pandas lxml beautifulsoup4
python scripts/build_stats_from_fbref.py --dry-run   # preview first
python scripts/build_stats_from_fbref.py              # write files
git add data/manual_stats.json data/manual_nt_stats.json
git commit -m "Update stats from FBref 2025/26"
git push
```

## Start small

You don't need all files at once. Just `Big5_standard.html` and `Big5_shooting.html`
are enough to test the pipeline on the most important players.
