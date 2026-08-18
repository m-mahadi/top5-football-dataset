# Top-5 European Leagues — Player Season Dataset (2024/25 & 2025/26)

One row per **player-season**, merging four public football data sources into a
single analysis-ready table: shooting and expected goals, full defensive and
passing detail, and market value / contract / physical attributes.

**5,693 player-seasons · 3,591 unique players · 202 columns · 5 leagues · 2 seasons**

Leagues: Premier League, La Liga, Serie A, Bundesliga, Ligue 1.

## Why this exists

FBref — the usual free source for advanced football stats — currently serves its
advanced tables **almost entirely empty**. Verified on a fresh 7.5 MB fetch with
caching disabled: 2,981 possession cells, 117 populated (~4%). `possession`,
`gca`, and `passing` return no usable data; `defense` retains only tackles-won
and interceptions. Expected goals, progression, and aerial duels are stripped
everywhere.

This dataset routes around that by combining sources, so the advanced metrics are
actually present.

## Column blocks

Columns are prefixed by origin, so provenance is never ambiguous.

| Prefix | Source | Count | Contents |
|---|---|---|---|
| *(none)* | identity | — | `league, season, season_label, team, player, nation, pos, age, nineties` |
| `fb_` | FBref | 9 | goals, assists, shots, shots on target, cards, minutes |
| `us_` | Understat | 9 | `xg, np_xg, xa, xg_chain, xg_buildup, shots, key_passes, np_goals` |
| `ss_` | SofaScore | 116 | aerial/ground/total duels won (+%), clearances, interceptions, blocked shots, tackles (+won %), accurate passes (+%), own-half vs opposition-half passing, long balls, final-third passes, key passes, `errorLeadToShot`, `errorLeadToGoal`, and attacking aggregates |
| `fifa_` | SoFIFA (EA FC 26) | 27 | `value_eur, wage_eur, release_clause_eur, contract_start, contract_end, pace, acceleration, sprint_speed, jumping, strength, heading, def_awareness, standing_tackle, sliding_tackle` |
| `*_p90` | derived | 25 | per-90 rates for the metrics above |

## Coverage

| Field group | Rows populated |
|---|---|
| SofaScore detail (`ss_*`) | 5,450 / 5,693 (96%) |
| Understat xG (`us_*`) | 5,377 / 5,693 (94%) |
| SoFIFA value & pace | 4,137 / 5,693 (73%) |
| SoFIFA contract end | 3,622 / 5,693 (64%) |
| **All three sources present** | **3,933** |

SoFIFA coverage is lower by nature: it is a *current* snapshot, so players who
have since left the top-5 leagues cannot be matched.

## Known limitations — please read before drawing conclusions

1. **SoFIFA values are EA's model, not Transfermarkt quotes.** Directionally
   useful for tiering players; not a transfer fee. Transfermarkt itself blocks
   automated access behind human verification and was not scraped.
2. **`fifa_pace` and physical ratings are scouted estimates, not GPS/tracking
   data.** Treat as a screening filter, never as measured speed.
3. **SoFIFA is a single current snapshot**, joined to both seasons. Value and
   contract do not vary by season row.
4. **Transferred players** appear as one row per club stint (FBref convention),
   flagged by `multi_club`. Understat metrics are season totals, so their per-90s
   use `season_nineties` (full-season minutes) rather than stint minutes —
   without this correction, mid-season transfers show inflated per-90 rates.
5. **Name matching is imperfect.** Joins use normalised names, first-initial +
   surname, and club/age sanity checks. Ambiguous matches are left null rather
   than guessed. ~4-6% of rows lack one source.
6. **No pass-level event data.** Chance-creation *origin* coordinates and pass
   networks with edges require paid providers (StatsBomb/Opta) and are absent.

## Quick start

```python
import pandas as pd
df = pd.read_csv('player_seasons.csv')

# Best young strikers by non-penalty xG per 90 (min ~900 minutes)
elig = df[(df.nineties >= 10) & (df.age <= 23)]
(elig[elig.pos.str.contains('FW', na=False)]
   .nlargest(10, 'np_xg_p90')
   [['player','team','season_label','age','np_xg_p90','fifa_value_eur','fifa_contract_end']])

# Ball-playing centre-backs: high pass accuracy, low errors, quick
cb = df[(df.nineties >= 10) & (df.ss_accuratePassesPercentage > 90)]
cb.nlargest(10, 'fifa_pace')[['player','team','ss_aerialDuelsWonPercentage',
                              'ss_errorLeadToShot','fifa_pace','fifa_value_eur']]
```

## Sources & attribution

- **FBref / Sports Reference** — basic season statistics
- **Understat** — expected goals model (xG, xA, xGChain, xGBuildup)
- **SofaScore** — detailed per-player season aggregates
- **SoFIFA / EA Sports FC 26** — valuations, contracts, attribute ratings

All data was collected from publicly accessible pages. **No paywall, login, or
bot-protection was circumvented.** Each source retains rights to its own data and
its own terms of use; verify those terms before redistributing or using this
commercially. Provided for research and educational purposes.

## Companion files

The wider project also includes shot-level data (2,726 Barcelona shots with xG
and pitch coordinates; 2,651 World Cup 2026 shots) and passing-network node
positions. See the repository for those.

---

# Two surfaces

The dataset ships in two forms for two audiences.

## 1. Machine surface — `player_seasons.csv`

Flat, one row per player-season, 202+ columns, prefixed by origin
(`fb_`, `us_`, `ss_`, `fifa_`, `*_p90`). Load with one line of pandas; ready for
filtering, modelling, or an agent to query. This is the canonical data.

```python
df = pd.read_csv('player_seasons.csv')
df[(df.nineties >= 10) & (df.age <= 23)].nlargest(10, 'np_xg_p90')
```

## 2. Human surface — `players.json` + `player_cards.html`

`players.json` — 3,591 nested player objects:

```
player, team, league, position, pos_group,
identity   { age, height, foot, overall, potential, value_eur,
             release_clause_eur, wage_eur, contract_start/end, playstyles }
attributes { technical{15}, mental{7}, physical{8} }
seasons    [ { season, nineties, goals, assists, xg, npxg, xa, xg_chain,
               shots, on_ball{11}, defensive{15} } ]
percentiles{ 18 metrics, ranked within position group }
```

Good for agents that need one player's full story without joining columns, and
for rendering a card directly.

`player_cards.html` — a self-contained searchable card viewer (2,304 players
with a real minutes sample). Percentile bars ranked within position group,
EA attribute blocks with quality tiering, per-season match output, and on-ball
/ pressing detail. No build step, no network calls; open the file.

Regenerate both with:

```bash
python scripts/build_cards.py    # -> players.json
python scripts/build_viewer.py   # -> player_cards.html
```
