# Top-5 European Leagues — Player Dataset & Scouting Toolkit

A merged, analysis-ready football dataset for the **2024/25 and 2025/26** seasons
across the Premier League, La Liga, Serie A, Bundesliga and Ligue 1 — plus the
scouting models built on top of it.

**5,693 player-seasons · 3,591 players · 220 columns · 4 sources**

---

## Why this exists

FBref, the usual free source for advanced football stats, currently serves its
advanced tables **near-empty**. Verified on a fresh 7.5 MB fetch with caching
disabled — not a stale-cache artifact:

| FBref table | Empty columns | Usable? |
|---|---|---|
| `possession` | 20 / 20 | no |
| `gca` (chance creation) | 16 / 16 | no |
| `passing` | 19 / 20 | no |
| `defense` | 14 / 16 | tackles-won and interceptions only |
| `keeper_adv` | 23 / 25 | no |
| `standard`, `shooting`, `playing_time`, `keeper`, `misc` | 0 | **yes** |

Expected goals, progression (PrgC/PrgP) and aerial duels are stripped
everywhere. Anything built on FBref advanced stats right now is quietly running
on empty columns.

This repo routes around that by combining four sources, and documents exactly
which field comes from where.

## Sources

| Source | Provides | Access |
|---|---|---|
| **FBref** | goals, assists, shots, minutes, cards | `soccerdata` |
| **Understat** | xG, npxG, xA, xGChain, xGBuildup | `soccerdata` |
| **SofaScore** | duels, aerials, clearances, interceptions, tackles, own/opposition-half passing, errors, pressing, **measured physical data** (top speed, distance covered, sprints), plus every shot with coordinates | public API |
| **SoFIFA** (EA FC 26) | market value, wage, release clause, contract dates, ~40 technical/mental/physical attributes | public pages |

**Transfermarkt is deliberately absent.** It blocks automated access behind a
human-verification wall, which was not circumvented. SoFIFA valuations stand in
for the money side — see limitations.

## Two surfaces

**For code and agents**

| File | Shape | What |
|---|---|---|
| `data/master/player_seasons.csv` | 5,693 × 220 | master table, one row per player-season, columns prefixed by origin (`fb_`, `us_`, `ss_`, `fifa_`, `*_p90`) |
| `data/master/player_seasons_adj.csv` | 5,693 × 286 | the same, plus possession-adjusted volume metrics |
| `data/master/players.json` | 3,591 | nested per-player objects with attributes, per-season output and percentile ranks |

**For humans**

`output/player_cards.html` — a self-contained, searchable card viewer (2,304
players with a real minutes sample). Percentile bars ranked within position
group, attribute blocks with quality tiering, per-season output, on-ball and
pressing detail. No build step, no network calls.

Also included: 2,726 Barcelona shots (La Liga + Champions League) with xG and
pitch coordinates, 2,651 World Cup 2026 shots, and passing-network node
positions.

## Quick start

```python
import pandas as pd
df = pd.read_csv('data/master/player_seasons.csv')

# best young forwards by non-penalty xG per 90 (min ~900 minutes)
elig = df[(df.nineties >= 10) & (df.age <= 23) & df.pos.str.contains('FW', na=False)]
elig.nlargest(10, 'np_xg_p90')[
    ['player', 'team', 'season_label', 'np_xg_p90', 'fifa_value_eur', 'fifa_contract_end']
]

# ball-playing centre-backs: accurate, genuinely quick, low-risk
# ss_topSpeed is MEASURED (km/h) - prefer it over EA's scouted fifa_pace
cb = df[(df.nineties >= 10) & (df.ss_accuratePassesPercentage > 90)]
cb.nlargest(10, 'ss_topSpeed')[
    ['player', 'team', 'ss_topSpeed', 'ss_aerialDuelsWonPercentage', 'ss_errorLeadToShot']
]
```

Full column dictionary: [`data/clean/README.md`](data/clean/README.md).
Quality report: [`docs/DATA_QUALITY.md`](docs/DATA_QUALITY.md).

## Methods worth stealing

Two ideas here generalise beyond this dataset.

**1. Possession adjustment — judge the player, not his team.**
A forward at a 68%-possession side is handed chances; one at 48% receives in
transition under pressure. `scripts/team_adjust.py` splits metrics in two:
ratio metrics (box share, xG per shot, duel and pass percentages) are already
team-neutral and left alone; volume metrics are scaled against league-median
possession — in-possession actions divided by relative possession,
out-of-possession actions multiplied by it.

**2. Filter by type, then rank by level.**
Similarity finds players who do the same *job*, not players who do it *well*.
`scripts/type_then_quality.py` takes the N closest season profiles to a template
player, then ranks only those on the fit model. The nearest profile match to a
given striker is often a distinctly lesser player.

## Repo layout

```
data/
  players/ teams/ schedule/     raw FBref pulls
  understat/                    xG by season
  barcelona/  worldcup/         shot-level and match-level data
  clean/                        tidy, flat, documented
  master/                       merged dataset + nested JSON
scripts/                        every pull, clean, merge and model step
docs/                           project log, data quality report
output/                         card viewer, shot maps, model results
```

## Regenerate everything

```bash
pip install -r requirements.txt

python scripts/pull.py               # FBref league data
python scripts/understat_pull.py     # xG
python scripts/sofascore_seasons.py  # defensive/passing detail (resumable)
python scripts/sofifa_pull.py        # value, contract, attributes
python scripts/clean.py              # tidy layer
python scripts/scout_base.py         # FBref + Understat spine
python scripts/build_master.py       # merged master
python scripts/team_adjust.py        # possession-adjusted columns
python scripts/build_cards.py        # players.json
python scripts/build_viewer.py       # card viewer
python scripts/validate.py           # quality report
```

Network pulls run in parallel (`scripts/fetch.py`, 8 workers) and the long
SofaScore pull resumes from disk if interrupted.

## Limitations

1. **SoFIFA is a current snapshot** — value, contract and attributes do not vary
   by season, and only match players still in the top-5 leagues (73% of rows).
2. **SoFIFA values are EA's model, not transfer quotes**, and its attributes are
   scouted estimates. Note that EA's pace rating correlates with SofaScore's
   **measured** top speed at only **r = 0.14** — prefer `ss_topSpeed` where present.
3. **Name matching is imperfect.** Joins use normalised names, first-initial +
   surname, and club/age sanity checks. Ambiguous matches are left null rather
   than guessed, so 4–6% of rows lack one source.
4. **Squad membership drifts** — the data reflects 24/25 and 25/26, not the
   current transfer window.
5. **No pass-level event data.** Chance-creation origins and true pass maps need
   a paid provider (StatsBomb/Opta).
6. **Copa del Rey / Supercopa have little or no xG.**
7. **Measured physical data (`ss_topSpeed`, `ss_kilometersCovered`,
   `ss_numberOfSprints`) exists for 2025/26 only**, at 93% coverage that season.
   Top speed is a season maximum, so it rises with minutes played
   (r = 0.31) — apply a minutes floor before comparing players.

Cross-source validation: SofaScore and Understat count goals independently and
correlate at **r = 0.967** across 5,244 comparable rows — the main evidence that
the name joins are sound.

## Licence and terms

The **code** in `scripts/` is MIT licensed — see [LICENSE](LICENSE).

The **data** is not mine to license. It was collected from publicly accessible
pages; no paywall, login or bot-protection was circumvented. Each source retains
rights to its own data under its own terms. Provided for research and education —
**verify the relevant terms before redistributing or using commercially.**
