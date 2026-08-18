"""Find players whose SEASON profile resembles a template season.

Usage:
  python scripts/similar.py cb  "Iñigo Martínez"   2425
  python scripts/similar.py fw  "Robert Lewandowski" 2425

Works on one season, not a career average, so "Iñigo in 24/25" means exactly
that. Volume metrics are possession-adjusted first, so a defender at a passive
side is not flattered by sheer workload. Similarity is Euclidean distance over
z-scored features within the relevant positional pool - lower is closer.
"""
import sys
import numpy as np
import pandas as pd

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'cb').lower()
NAME = sys.argv[2] if len(sys.argv) > 2 else 'Iñigo Martínez'
SEASON = sys.argv[3] if len(sys.argv) > 3 else '2425'
EXTRA = sys.argv[4:] if len(sys.argv) > 4 else []

m = pd.read_csv('data/master/player_seasons_adj.csv', low_memory=False)
m['season'] = m.season.astype(str)
m = m.sort_values('nineties', ascending=False).drop_duplicates(['player', 'season'])
n = m.season_nineties.replace(0, np.nan)


def p90(base):
    src = base + '_adj' if base + '_adj' in m.columns else base
    return pd.to_numeric(m[src], errors='coerce') / n


m['passes_p90'] = p90('ss_accuratePasses')
m['ownhalf_p90'] = p90('ss_accurateOwnHalfPasses')
m['opphalf_p90'] = p90('ss_accurateOppositionHalfPasses')
m['final3rd_p90'] = p90('ss_accurateFinalThirdPasses')
m['longballs_p90'] = p90('ss_accurateLongBalls')
m['clearances_p90'] = p90('ss_clearances')
m['intercept_p90'] = p90('ss_interceptions')
m['blocks_p90'] = p90('ss_blockedShots')
m['tackles_p90'] = p90('ss_tackles')
m['aerials_p90'] = p90('ss_aerialDuelsWon')
m['grounddw_p90'] = p90('ss_groundDuelsWon')
m['errors_p90'] = p90('ss_errorLeadToShot')
m['dribbledpast_p90'] = p90('ss_dribbledPast')
m['fouls_p90'] = p90('ss_fouls')
m['dribbles_p90'] = p90('ss_successfulDribbles')
m['recov_p90'] = p90('ss_ballRecovery')
m['npxg_p90'] = p90('us_np_xg')
m['shots_p90'] = p90('us_shots')
m['boxshots_p90'] = p90('ss_shotsFromInsideTheBox')
m['xa_p90'] = p90('us_xa')
m['chain_p90'] = p90('us_xg_chain')
m['keyp_p90'] = p90('ss_keyPasses')
m['bcc_p90'] = p90('ss_bigChancesCreated')
m['press_p90'] = p90('ss_possessionWonAttThird')
m['fouled_p90'] = p90('ss_wasFouled')
m['disp_p90'] = p90('ss_dispossessed')
m['npxg_per_shot'] = pd.to_numeric(m.us_np_xg, errors='coerce') / \
    pd.to_numeric(m.us_shots, errors='coerce').replace(0, np.nan)
m['box_share'] = pd.to_numeric(m.ss_shotsFromInsideTheBox, errors='coerce') / \
    pd.to_numeric(m.ss_totalShots, errors='coerce').replace(0, np.nan)

CB_F = ['ss_accuratePassesPercentage', 'passes_p90', 'ss_accurateLongBallsPercentage',
        'ownhalf_p90', 'opphalf_p90', 'final3rd_p90', 'longballs_p90',
        'ss_aerialDuelsWonPercentage', 'aerials_p90', 'ss_groundDuelsWonPercentage',
        'ss_tacklesWonPercentage', 'clearances_p90', 'intercept_p90', 'blocks_p90',
        'tackles_p90', 'errors_p90', 'dribbledpast_p90', 'fouls_p90', 'dribbles_p90']
FW_F = ['npxg_p90', 'npxg_per_shot', 'shots_p90', 'boxshots_p90', 'box_share',
        'ss_goalConversionPercentage', 'xa_p90', 'chain_p90', 'keyp_p90', 'bcc_p90',
        'press_p90', 'recov_p90', 'fouled_p90', 'disp_p90', 'dribbles_p90',
        'ss_aerialDuelsWonPercentage', 'aerials_p90',
        'ss_groundDuelsWonPercentage', 'ss_accuratePassesPercentage']

if ROLE == 'cb':
    pool = m[m.pos.str.startswith('DF', na=False) & (m.clearances_p90 >= 2.5)
             & (m.season_nineties >= 12)].copy()
    F, label = CB_F, 'centre-backs'
else:
    pool = m[m.pos.str.contains('FW', na=False) & (m.season_nineties >= 12)].copy()
    F, label = FW_F, 'forwards'

F = [c for c in F if c in pool.columns and pool[c].notna().sum() > 50]
Z = pool[F].apply(lambda s: (s - s.mean()) / s.std(ddof=0))
Z = Z.fillna(0.0)

tgt = pool[(pool.player.str.contains(NAME, na=False)) & (pool.season == SEASON)]
if tgt.empty:
    print(f'template "{NAME}" {SEASON} not found in the {label} pool')
    avail = m[m.player.str.contains(NAME, na=False)][
        ['player', 'season_label', 'team', 'pos', 'season_nineties']]
    print(avail.to_string(index=False) if len(avail) else '  (no rows for that name)')
    sys.exit()

ti = tgt.index[0]
t = tgt.loc[ti]
sl = '20' + SEASON[:2] + '/' + SEASON[2:]
print('=' * 108)
print(f'TEMPLATE: {t.player} — {t.team} {sl} — {t.season_nineties:.0f} x90  '
      f'({len(pool)} {label} compared)')
print('=' * 108)
for c in F:
    v, pc = t[c], (pool[c].dropna() < t[c]).mean() * 100 if pd.notna(t[c]) else np.nan
    print(f'  {c:36} {v:>8.2f}   {"" if pd.isna(pc) else f"{pc:>3.0f} pct"}')

d = np.sqrt(((Z - Z.loc[ti]) ** 2).sum(axis=1))
pool = pool.assign(dist=d)
out = pool[(pool.index != ti) & (pool.player != t.player)].nsmallest(14, 'dist')

print('\n' + '=' * 108)
print(f'CLOSEST PROFILE MATCHES to {t.player} {sl}')
print('=' * 108)
print(f"{'player':24}{'team':16}{'szn':8}{'age':>4}{'90s':>5}{'dist':>7}"
      f"{'€M':>6}{'exp':>6}{'pace':>6}")
for _, r in out.iterrows():
    print(f"{str(r.player)[:23]:24}{str(r.team)[:15]:16}{str(r.season_label):8}"
          f"{r.age:>4.0f}{r.season_nineties:>5.0f}{r.dist:>7.2f}"
          f"{(r.fifa_value_eur/1e6 if pd.notna(r.fifa_value_eur) else 0):>6.0f}"
          f"{str(r.fifa_contract_end)[:4]:>6}"
          f"{(r.fifa_pace if pd.notna(r.fifa_pace) else 0):>6.0f}")

for name in EXTRA:
    rows = pool[pool.player.str.contains(name, na=False)]
    print('\n' + '-' * 108)
    if rows.empty:
        any_row = m[m.player.str.contains(name, na=False)]
        print(f'LOOKUP "{name}": not in the {label} pool.')
        if len(any_row):
            print(any_row[['player', 'season_label', 'team', 'pos',
                           'season_nineties']].to_string(index=False))
        else:
            print('  no rows anywhere in the dataset (likely outside the top-5 leagues)')
        continue
    print(f'LOOKUP "{name}" — distance from the template (lower = more similar)')
    print(f"{'player':24}{'team':16}{'szn':8}{'age':>4}{'90s':>5}{'dist':>7}"
          f"{'rank':>7}")
    for _, r in rows.sort_values('dist').iterrows():
        rank = (pool.dist < r.dist).sum() + 1
        print(f"{str(r.player)[:23]:24}{str(r.team)[:15]:16}{str(r.season_label):8}"
              f"{r.age:>4.0f}{r.season_nineties:>5.0f}{r.dist:>7.2f}{rank:>7}")
