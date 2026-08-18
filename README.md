# barca-analytics

Football data to answer: **what would help Barcelona most this season** — which
striker signing, which centre-back for the style, etc.

## Data

Full FBref season stats, **top-7 leagues**, seasons **2024-2025** and **2025-2026**:

| Leagues | Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Primeira Liga (POR), Eredivisie (NED) |
|---|---|
| Player stats | `data/players/<type>.csv` |
| Team stats | `data/teams/<type>.csv` |
| Match results | `data/schedule/matches.csv` |

Stat types (`<type>`): `standard shooting passing passing_types gca defense
possession playing_time misc keeper keeper_adv`.

Each CSV holds all 7 leagues x both seasons (indexed by league/season/team[/player]).

## Sources

- **FBref** (StatsBomb-powered) via [`soccerdata`](https://github.com/probberechts/soccerdata) — all advanced per-90 stats, free.
- Not yet pulled: **Transfermarkt** (market values / fees / contracts) — needed to turn "good player" into "realistic signing". Add when doing the signing shortlist.
- Not pulled: Understat shot-level xG (top-5 only) — FBref xG covers the season-level question.

## Refresh

```bash
pip install -r requirements.txt
python scripts/pull.py
```

Portugal + Netherlands aren't in soccerdata by default — they're added via
`~/soccerdata/config/league_dict.json` (FBref names "Primeira Liga",
"Eredivisie"). `scripts/fbref_full.py` unlocks the stat pages soccerdata 1.9.1
otherwise hides. FBref requires a real browser (Selenium auto-installs a driver);
first run downloads chromedriver.
