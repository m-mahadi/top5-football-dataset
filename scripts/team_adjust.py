"""Strip team context out of player metrics.

The problem: a striker at 68%-possession PSG is handed box chances; a striker at
48%-possession Atletico receives in transition under pressure. Raw per-90s score
the team as much as the player.

Two classes of metric:

1. RATIO metrics are already team-neutral - they describe the player's own
   behaviour regardless of how often his side has the ball:
   box_share, npxg_per_shot, conversion %, aerial %, ground-duel %, pass %.
   Left untouched.

2. VOLUME metrics scale with team context and are possession-adjusted:
   - in-possession actions (box shots, npxG, xA, key passes, xGChain, dribbles,
     fouls won, dispossessions, presses won in the attacking third) happen more
     often when your side has the ball -> divide by relative possession.
   - out-of-possession actions (recoveries, tackles, interceptions) happen more
     often when your side does NOT have the ball -> multiply by relative
     possession.

Adjusted value = raw * (league_median_possession / team_possession) for the
in-possession group, and raw * (team_possession / league_median) for the other.
A player at a dominant side is therefore held to a higher bar, and one at a
passive side is credited for doing more with fewer opportunities.

Output: data/master/player_seasons_adj.csv (adds *_adj columns)
"""
import numpy as np
import pandas as pd

m = pd.read_csv('data/master/player_seasons.csv', low_memory=False)
m['season'] = m.season.astype(str)

tm = pd.read_csv('data/clean/teams/standard.csv')
tm['season'] = tm.season.astype(str)
tm['poss'] = pd.to_numeric(tm.poss, errors='coerce')
poss = tm.groupby(['team', 'season']).poss.mean()
m['team_poss'] = pd.Series(
    list(zip(m.team, m.season))).map(poss).values
med = tm.poss.median()
print('league median possession: %.1f%%' % med)
print('team possession matched: %d / %d' % (m.team_poss.notna().sum(), len(m)))

# relative possession: >1 means the side has the ball more than a median team
rel = (m.team_poss / med).replace(0, np.nan)

IN_POSS = ['ss_shotsFromInsideTheBox', 'ss_totalShots', 'us_np_xg', 'us_xg',
           'us_xa', 'us_xg_chain', 'us_shots', 'ss_keyPasses',
           'ss_bigChancesCreated', 'ss_successfulDribbles', 'ss_wasFouled',
           'ss_dispossessed', 'ss_possessionWonAttThird', 'ss_touches',
           'ss_accurateFinalThirdPasses', 'ss_accurateOppositionHalfPasses',
           'ss_accurateOwnHalfPasses', 'ss_accurateLongBalls', 'ss_accuratePasses',
           'ss_totalPasses', 'ss_errorLeadToShot', 'ss_errorLeadToGoal']
OUT_POSS = ['ss_ballRecovery', 'ss_tackles', 'ss_tacklesWon', 'ss_interceptions',
            'ss_clearances', 'ss_blockedShots', 'ss_aerialDuelsWon',
            'ss_dribbledPast', 'ss_fouls', 'ss_groundDuelsWon', 'ss_duelLost']

for c in IN_POSS:
    if c in m.columns:
        m[c + '_adj'] = pd.to_numeric(m[c], errors='coerce') / rel
for c in OUT_POSS:
    if c in m.columns:
        m[c + '_adj'] = pd.to_numeric(m[c], errors='coerce') * rel

m.to_csv('data/master/player_seasons_adj.csv', index=False, encoding='utf-8')
made = [c for c in m.columns if c.endswith('_adj')]
print('%d adjusted columns -> data/master/player_seasons_adj.csv' % len(made))

# quick illustration of the effect
show = ['Julián Álvarez', 'Robert Lewandowski', 'Lautaro Martínez',
        'Marcus Thuram', 'Bradley Barcola', 'Raphinha']
sub = m[m.player.isin(show) & (m.season == '2425')]
if len(sub):
    out = pd.DataFrame({
        'player': sub.player, 'team': sub.team,
        'poss': sub.team_poss.round(1),
        'box_shots': sub.ss_shotsFromInsideTheBox.round(0),
        'box_adj': sub.ss_shotsFromInsideTheBox_adj.round(0),
        'press': sub.ss_possessionWonAttThird.round(0),
        'press_adj': sub.ss_possessionWonAttThird_adj.round(0),
        'recov': sub.ss_ballRecovery.round(0),
        'recov_adj': sub.ss_ballRecovery_adj.round(0),
    }).sort_values('poss')
    print('\neffect of the adjustment (2024/25):')
    print(out.to_string(index=False))
