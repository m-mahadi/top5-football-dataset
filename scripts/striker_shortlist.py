"""Phase 2: system-fit striker shortlist for Barcelona under Flick.

Brief = a 9 that fits a very high line and press: scores, links play, and can
run in behind. Not a pure poacher (Ferran Torres already gives Barca 0.221
xG/shot). Aggregates both seasons to player level; per-90s come from totals.
Output: output/striker_shortlist.csv
"""
import numpy as np
import pandas as pd

m = pd.read_csv('data/master/player_seasons.csv', low_memory=False)
m['season'] = m.season.astype(str)

# one row per player-season (transfer stints duplicate Understat season totals)
m = m.sort_values('nineties', ascending=False).drop_duplicates(['player', 'season'])

SUM_US = ['us_np_xg', 'us_xa', 'us_xg_chain', 'us_shots', 'us_np_goals']
SUM_SS = ['ss_shotsFromInsideTheBox', 'ss_totalShots', 'ss_bigChancesCreated',
          'ss_bigChancesMissed', 'ss_aerialDuelsWon', 'ss_minutesPlayed',
          'ss_successfulDribbles', 'ss_touches']
agg = {c: 'sum' for c in SUM_US + SUM_SS if c in m.columns}
agg.update({'season_nineties': 'sum', 'age': 'max', 'league': 'last',
            'team': 'last', 'pos': 'last', 'season': 'nunique',
            'fifa_value_eur': 'max', 'fifa_contract_end': 'max',
            'fifa_pace': 'max', 'fifa_release_clause_eur': 'max',
            'ss_aerialDuelsWonPercentage': 'mean'})
p = m.groupby('player').agg(agg).rename(columns={'season': 'seasons_played'}).reset_index()

# ---- pool ----
pool = p[(p.season_nineties >= 15) & (p.age <= 30)
         & (p.team.astype(str) != 'Barcelona')
         & m.set_index('player').pos.groupby(level=0).last()
             .reindex(p.player).str.contains('FW', na=False).values].copy()

n90 = pool.season_nineties
pool['np_xg_p90'] = pool.us_np_xg / n90
pool['xa_p90'] = pool.us_xa / n90
pool['xg_chain_p90'] = pool.us_xg_chain / n90
pool['npxg_per_shot'] = pool.us_np_xg / pool.us_shots.replace(0, np.nan)
pool['box_shot_share'] = (pool.ss_shotsFromInsideTheBox
                          / pool.ss_totalShots.replace(0, np.nan))
pool['big_chances_created_p90'] = pool.ss_bigChancesCreated / n90
pool['np_g_minus_xg'] = pool.us_np_goals - pool.us_np_xg
pool = pool[pool.np_xg_p90.notna()]
print(f'pool: {len(pool)} forwards (age<=30, >=15x90, top-5, excl. Barca)')


def z(s):
    return (s - s.mean()) / s.std(ddof=0)


# link play = creation for others, the thing Lewandowski does NOT provide
pool['link_z'] = z(z(pool.xa_p90) + z(pool.xg_chain_p90)
                   + z(pool.big_chances_created_p90.fillna(0)))
pool['pace_z'] = z(pool.fifa_pace)
pool['pace_z'] = pool.pace_z.fillna(0)          # missing pace = neutral, flagged
pool['no_pace_data'] = pool.fifa_pace.isna()


# ---- system fit: Barca play 66.8% possession, so opponents sit deep. A striker
# whose output comes at a low-possession (counter-attacking) side faces a very
# different problem at Barca. Team possession = style-transfer risk proxy.
tm = pd.read_csv('data/clean/teams/standard.csv')
tm['poss'] = pd.to_numeric(tm.poss, errors='coerce')
poss = tm.groupby('team').poss.mean()
pool['team_poss'] = pool.team.map(poss)


def style(v):
    if pd.isna(v):
        return '?'
    return 'possession' if v >= 55 else ('balanced' if v >= 48 else 'COUNTER-risk')


pool['style_fit'] = pool.team_poss.map(style)

W = {'np_xg_p90': .30, 'link_z': .25, 'pace_z': .20,
     'box_shot_share': .15, 'npxg_per_shot': .10}
pool['score'] = sum(
    (pool[c] if c.endswith('_z') else z(pool[c].fillna(pool[c].median()))) * w
    for c, w in W.items())

for c in ['np_xg_p90', 'link_z', 'pace_z', 'box_shot_share', 'npxg_per_shot']:
    pool[f'rank_{c}'] = pool[c].rank(ascending=False)

out = pool.sort_values('score', ascending=False)
cols = ['player', 'team', 'league', 'age', 'season_nineties', 'seasons_played',
        'np_xg_p90', 'npxg_per_shot', 'xa_p90', 'xg_chain_p90',
        'big_chances_created_p90', 'box_shot_share', 'fifa_pace',
        'ss_aerialDuelsWonPercentage', 'np_g_minus_xg', 'fifa_value_eur',
        'fifa_release_clause_eur', 'fifa_contract_end', 'no_pace_data',
        'team_poss', 'style_fit', 'score']
out[cols].to_csv('output/striker_shortlist.csv', index=False, encoding='utf-8')

LEW = 0.253  # Lewandowski xG/shot benchmark from flick_profile.py
show = out.head(15).copy()
show['val'] = (show.fifa_value_eur / 1e6).round(0)
print('\n' + '=' * 118)
print('SYSTEM-FIT STRIKER SHORTLIST  (Barca under Flick)')
print('=' * 118)
print(f"{'#':>2} {'player':22}{'team':16}{'age':>4}{'90s':>6}{'npxG/90':>8}"
      f"{'xG/sh':>7}{'xA/90':>7}{'chain':>7}{'box%':>6}{'pace':>5}"
      f"{'G-xG':>7}{'val€M':>7}{'exp':>6}  {'style(poss%)':<16}")
for i, (_, r) in enumerate(show.iterrows(), 1):
    print(f"{i:>2} {r.player[:21]:22}{str(r.team)[:15]:16}{r.age:>4.0f}"
          f"{r.season_nineties:>6.0f}{r.np_xg_p90:>8.2f}{r.npxg_per_shot:>7.3f}"
          f"{r.xa_p90:>7.2f}{r.xg_chain_p90:>7.2f}"
          f"{(r.box_shot_share*100 if pd.notna(r.box_shot_share) else 0):>5.0f}%"
          f"{(r.fifa_pace if pd.notna(r.fifa_pace) else 0):>5.0f}"
          f"{r.np_g_minus_xg:>+7.1f}{(r.val if pd.notna(r.val) else 0):>7.0f}"
          f"{str(r.fifa_contract_end)[:4]:>6}  "
          f"{r.style_fit:<12}{(r.team_poss if pd.notna(r.team_poss) else 0):>4.0f}%")
print('=' * 118)
print(f'Lewandowski benchmark: 0.253 xG/shot, pace 71, age 36, contract 2028')
print('Barca context: 66.8% possession, 4-2-3-1, CB line x=41.7, 50% of shots in box')
print('COUNTER-risk = player produces at a low-possession side; output may not transfer')
print('G-xG is a REGRESSION FLAG, not a ranking input: large + = finishing likely to fall back')
