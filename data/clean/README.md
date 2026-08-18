# clean/ — analysis-ready data

Flat, tidy copies of everything under `data/`. Raw files are left untouched;
regenerate this folder anytime with `python scripts/clean.py`.

## Conventions (apply everywhere)

- **Columns:** single-row, `snake_case`. FBref stat groups are prefixed, e.g.
  `performance_gls`, `per_90_minutes_gls`, `expected_xg` (where present).
- **Seasons:** `"2425"` = 2024/25, `"2526"` = 2025/26.
- **Team names:** canonical, no club affixes — `Barcelona`, not `FC Barcelona`.
  Safe to join across sources on `team`.
- **Shot coordinates:** `x`, `y` on a **0–100** scale, attacking toward `x=100`.
  (Raw Understat is 0–1; already rescaled here.)
- **xG:** present in Understat/SofaScore-derived files. FBref files have **no xG**
  (the source is currently serving pages with xG stripped).

## Files

| File | Rows | What / key columns |
|---|---|---|
| `players/<stat>.csv` (11) | ~7.9k | FBref player season stats, 7 leagues × 2 seasons. Join: `league, season, team, player`. No xG. |
| `teams/<stat>.csv` (11) | ~200–270 | FBref team season stats. Join: `league, season, team`. |
| `understat_players.csv` | 5,549 | La Liga-family per-player xG (`xg, np_xg, xa, xg_chain, xg_buildup, shots, key_passes`). Join: `player, team, season`. |
| `wc_players/<stat>.csv` (11) | 1,039 | World Cup 2026 player stats (incl. a `club` column). |
| `wc_teams/<stat>.csv` (11) | 48 | World Cup 2026 team stats. |
| `barca_shots.csv` | 2,726 | **Unified Barça shots** — La Liga (Understat) + Champions League (SofaScore). `season, competition, date, team, player, xg, x, y, situation, body_part, outcome, minute, source`. `outcome ∈ {goal, saved, missed, blocked, post, own_goal}`. |
| `barca_passing_network.csv` | 1,980 | Per-player-per-match node layout, all comps. `season, date, competition, venue, opponent, player, avg_x, avg_y, touches`. Node positions only (no pass edges). |
| `barca_allcomps_2425.csv` / `_2526.csv` | 60 / 57 | Every Barça match, all comps: `date, comp, venue, result, gf, ga, opponent, poss, formation, …`. No xG for UCL/Copa. |
| `wc_shots.csv` | 2,651 | Every World Cup 2026 shot. `date, round, team, opponent, player, xg, xgot, x, y, situation, body_part, outcome, minute`. |

## Quick start

```python
import pandas as pd
shots = pd.read_csv('data/clean/barca_shots.csv')
barca = shots[shots.team == 'Barcelona']
# xG per player, both competitions
barca.groupby('player').xg.sum().sort_values(ascending=False).head(10)
```

## Coverage ceiling (no free source fills these for 24/25–25/26)

- xG for Copa del Rey / Supercopa (patchy) and for FBref tables (stripped).
- True pass **edges** and chance-creation **origin** coordinates (need paid event data).
