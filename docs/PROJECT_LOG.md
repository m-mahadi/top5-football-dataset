# Top-5 League Dataset — Working Log

The dataset is general-purpose; it was built while answering a Barcelona
scouting question, which is why the worked examples are Barca-flavoured.

**Goal:** find Barcelona a striker and a style-fit centre-back, using Flick's
two seasons (2024/25 + 2025/26) as the system definition.

**Repo:** `D:\barca-analytics` → GitHub `m-mahadi/barca-analytics` (private)

---

## 1. The finding that shaped everything

**FBref now serves its advanced tables almost entirely empty.** Verified on a
fresh 7.5 MB fetch with caching disabled — *not* a stale-cache artifact:
2,981 possession cells, 117 populated (~4%).

| FBref table | Empty columns | Verdict |
|---|---|---|
| `possession` | 20 / 20 | dead |
| `gca` | 16 / 16 | dead |
| `passing` | 19 / 20 | dead (only assists) |
| `defense` | 14 / 16 | only tackles-won + interceptions |
| `keeper_adv` | 23 / 25 | dead |
| `standard`, `shooting`, `playing_time`, `keeper`, `misc` | 0 | **usable** |

Also stripped everywhere: **xG, progression (PrgC/PrgP/PrgR), aerial duels.**

This killed the original CB plan (tackles-by-third, progressive carries, aerial
win %) and forced a source change.

## 2. Sources actually used

| Source | Role | Access |
|---|---|---|
| **FBref** | basic stats only (goals, shots, minutes, cards) | soccerdata |
| **Understat** | xG engine — top-5 only, no cups | soccerdata |
| **SofaScore** | *primary* for defensive/passing detail + all shot-level data | direct API via `tls_requests` |
| **SoFIFA** (EA FC 26) | value, wage, release clause, contract expiry, pace | direct scrape |

**Transfermarkt was NOT scraped** — it returns 405 behind a "Human Verification"
wall. Bot detection was not circumvented. For real market values, look up a
shortlist manually and merge.

Key SofaScore endpoints:
- `/player/{id}/unique-tournament/{t}/season/{s}/statistics/overall` → 111 fields
- `/event/{id}/shotmap` → per-shot xG + coords (JSON key is `shotmap`, not `shots`)
- `/event/{id}/average-positions` → passing-network nodes (no pass edges exist free)

## 3. Datasets produced

| File | Rows | Contents |
|---|---|---|
| `data/master/player_seasons.csv` | 5,693 × 202 | **the merged master** — all sources, one row per player-season |
| `data/clean/sofascore_player_seasons.csv` | 5,400 × 123 | defensive/passing detail, 100% populated |
| `data/clean/scout_base.csv` | 5,693 × 238 | FBref + Understat spine |
| `data/clean/sofifa_players.csv` | 2,790 | value / contract / pace |
| `data/clean/understat_players.csv` | 5,549 | xG block |
| `data/clean/barca_shots.csv` | 2,726 | Barça shots, La Liga + UCL |
| `data/clean/barca_passing_network.csv` | 1,980 | node positions + touches |
| `data/clean/wc_shots.csv` | 2,651 | World Cup 2026, every shot |
| `data/barcelona/fbref_allcomps_*.csv` | 60 + 57 | every Barça match, all competitions |

## 4. Bugs found and fixed

1. **Transferred-player per-90 inflation** — FBref splits a player into one row
   per club stint, but Understat xG is a *season total*. Dividing season xG by
   one stint's minutes inflated rates (Gouiri showed 0.93 npxG/90; true 0.46).
   Fixed with a `season_nineties` denominator.
2. **`Cmp%` → `cmp_1`** — the flattener mangled percent columns. Now `cmp_pct`.
3. **`league_x` / `league_y` collision** — SofaScore's own `league` column
   silently displaced the real one during the master merge.
4. **Compound surnames broke Understat joins** — Mbappé had *no xG* because
   Understat lists "Kylian Mbappe-Lottin". A repair pass on first-initial + any
   surname token recovered **+292 rows** (89% → 94%), while correctly keeping
   Kylian separate from Ethan Mbappé.
5. **44 false SoFIFA matches** rejected by an age sanity check.
6. **UCL knockouts silently dropped** — they use tournament names
   `"...Knockout Phase"` / `"...Knockout stage"`; an exact-match filter missed
   10 matches including the 24/25 semi-final.
7. **Shot `situation` labels unharmonised** across Understat/SofaScore
   ("OpenPlay" vs "regular"/"assisted" were counted separately).

## 5. Decisions taken (with rationale)

| Decision | Choice | Why |
|---|---|---|
| League scope | **Top 5 only** | comparable, and every player has xG |
| Money data | SoFIFA, no budget cap | rank on football, show value so nothing good is hidden |
| Striker brief | **System-fit 9** | Ferrán Torres already gives 0.221 xG/shot; duplicating a poacher doesn't improve the team |
| Age cap | **≤ 30** | widened from 26 at Monir's request |
| G−xG | **flag, never a ranker** | hot finishing regresses; it's a sell signal, not a buy signal |

## 6. What Flick's system actually demands (measured, not assumed)

- **CB line sits at x = 41.7 / 100** — genuinely high; recovery pace matters.
- **Cubarsí: 97.6 touches/match** — CBs are the build-up hub, not just defenders.
  Any CB target needs ~72+ touches/match of build-up load.
- **66.8% possession, 4-2-3-1** — opponents sit deep; strikers face packed boxes,
  not open space. Output from a counter-attacking side may not transfer.
- **1,797 shots, 258 xG, 0.144 xG/shot, 50% inside the box, 75% of xG from open
  play** — not a set-piece team.
- **Lewandowski: 0.253 xG/shot from median x=87.5**, 13% of all Barça shots,
  56 goals from 59.6 xG. Age 36, pace 71, contract 2028.

## 6b. Striker scoring — v1 was wrong, v2 fixed it

**v1 error:** npxG/90 carried 30% of the composite, so raw chance volume dragged
system misfits up the list. Sorloth ranked 6th on 0.85 npxG/90 despite 0.06
xA/90 (no link play), age 29, at a 53%-possession counter side.

**v2:** five dimensions from real match data, plus *gates* — fail any of
link/press/hold-up and you are excluded regardless of goals.

| Dimension | Built from |
|---|---|
| PRESS | `ss_possessionWonAttThird` + `ss_ballRecovery` |
| HOLDUP | `ss_wasFouled`, aerial %, ground-duel %, minus dispossessed |
| LINK | xA, xGChain, key passes, big chances created |
| FINISH | npxG/90 + npxG per shot |
| SPACE | pace + successful dribbles |

Gates now exclude Sorloth, Haaland, Guirassy (all fail PRESS) and Dembele
(fails HOLDUP). Barca's own forwards set the standard: Yamal LINK 3.5,
Raphinha 3.2, while Ferran Torres scores FIN 2.5 but PRESS -0.3.

Output is split by role (SoFIFA best position ST/CF vs wide/attacking mid),
because the link/press weighting naturally favours wingers.

## 6c. SoFIFA now carries a full Football-Manager-style profile

88 columns pulled (was 27): technical (finishing, crossing, curve, dribbling,
ball control, short/long passing, long shots, heading, volleys, FK accuracy,
penalties, standing/sliding tackle, shot power), mental (composure, vision,
aggression, attack position, defensive awareness, interceptions, attacking and
defensive work rate), physical (pace, acceleration, sprint speed, stamina,
strength, jumping, agility, balance, reactions, height, weight), plus
PlayStyles, weak foot, skill moves, reputation, potential and growth.

## 6d. Pulls are parallel

`scripts/fetch.py` provides `pmap()` — an 8-worker thread pool with retries and
periodic checkpointing. Applied to the SoFIFA page pull and the 5,400-request
SofaScore player pull. Workers kept modest to stay polite to public endpoints.

## 6e. Possession adjustment — judging the player, not the team

Raw per-90s partly score the club. A striker at 68%-possession PSG is handed box
chances; one at 48%-possession Atletico receives in transition under pressure.

`scripts/team_adjust.py` splits metrics in two:
- **Ratio metrics are already team-neutral** and are left alone: box share,
  xG per shot, conversion %, aerial %, ground-duel %, pass accuracy.
- **Volume metrics are adjusted** against the 48.9% league median. In-possession
  actions (box shots, npxG, xA, key passes, presses in the attacking third) are
  divided by relative possession; out-of-possession actions (recoveries,
  tackles, clearances, aerials) are multiplied by it.

Effects: Lewandowski's 95 box shots become 68, and his FIT falls 62.1 -> 55.8.
Raphinha's 94 recoveries become 131 (Barca rarely defend, so each is rarer).
Forwards at 40-47% possession sides gain up to +8.

The decisive result: **Julian Alvarez barely moves, 54.5 -> 53.5, floor 21.**
If Atletico's system were suppressing him, removing team context would rescue
him. It does not - the dispossessions, lost ground duels and 1.57 box shots per
90 are his own profile. Emegha moves -0.1, so his numbers were never inflated.

## 7. Progress

- [x] Phase 0 — data pull, clean layer, master merge
- [x] Phase 1 — Flick system profile (`scripts/flick_profile.py`)
- [x] Phase 2 — striker shortlist (`scripts/striker_shortlist.py`)
- [x] Phase 3 — CB shortlist (`scripts/cb_fit.py`)
- [ ] Phase 4 — corroboration (season split, World Cup, shot maps)

## 8. Regenerating everything

```bash
python scripts/pull.py              # FBref league data
python scripts/understat_pull.py    # xG, top-5
python scripts/sofascore_seasons.py # defensive detail (resumable)
python scripts/sofifa_pull.py       # value / contract / pace
python scripts/clean.py             # tidy layer
python scripts/scout_base.py        # FBref + Understat spine
python scripts/build_master.py      # merged master
python scripts/flick_profile.py     # system profile
python scripts/striker_shortlist.py # Phase 2
```

## 9. Hard limits (no free source fixes these)

- Pass **edges** and chance-creation **origin** coordinates → paid event data only.
- Real market values → Transfermarkt blocks automation.
- Measured pace → SoFIFA ratings are scouted estimates, not GPS.
- xG for Copa del Rey / Supercopa → patchy to nonexistent.
