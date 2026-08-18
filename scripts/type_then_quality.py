"""Two-stage scouting: filter by TYPE, then rank by LEVEL.

Similarity alone finds players who do the same job, not players who do it well
(Watkins is the closest profile to Lewandowski but a clearly lesser player).
So: stage 1 takes the N closest profiles to a template season, stage 2 ranks
only those on the possession-adjusted six-dimension fit model.

Usage:
  python scripts/type_then_quality.py fw "Robert Lewandowski" 2425 50
  python scripts/type_then_quality.py cb "Iñigo Martínez"    2425 50
"""
import subprocess
import sys

import numpy as np
import pandas as pd

ROLE = (sys.argv[1] if len(sys.argv) > 1 else 'fw').lower()
NAME = sys.argv[2] if len(sys.argv) > 2 else 'Robert Lewandowski'
SEASON = sys.argv[3] if len(sys.argv) > 3 else '2425'
TOPN = int(sys.argv[4]) if len(sys.argv) > 4 else 50
EXCLUDE = {'Barcelona'}

# ---------- stage 1: type ----------
m = pd.read_csv('data/master/player_seasons_adj.csv', low_memory=False)
m['season'] = m.season.astype(str)
m = m.sort_values('nineties', ascending=False).drop_duplicates(['player', 'season'])
n = m.season_nineties.replace(0, np.nan)


def p90(base):
    src = base + '_adj' if base + '_adj' in m.columns else base
    return pd.to_numeric(m[src], errors='coerce') / n


feat = {}
for key, base in [('passes_p90', 'ss_accuratePasses'),
                  ('ownhalf_p90', 'ss_accurateOwnHalfPasses'),
                  ('opphalf_p90', 'ss_accurateOppositionHalfPasses'),
                  ('final3rd_p90', 'ss_accurateFinalThirdPasses'),
                  ('longballs_p90', 'ss_accurateLongBalls'),
                  ('clearances_p90', 'ss_clearances'),
                  ('intercept_p90', 'ss_interceptions'),
                  ('blocks_p90', 'ss_blockedShots'),
                  ('tackles_p90', 'ss_tackles'),
                  ('aerials_p90', 'ss_aerialDuelsWon'),
                  ('errors_p90', 'ss_errorLeadToShot'),
                  ('dribbledpast_p90', 'ss_dribbledPast'),
                  ('fouls_p90', 'ss_fouls'),
                  ('dribbles_p90', 'ss_successfulDribbles'),
                  ('recov_p90', 'ss_ballRecovery'),
                  ('npxg_p90', 'us_np_xg'), ('shots_p90', 'us_shots'),
                  ('boxshots_p90', 'ss_shotsFromInsideTheBox'),
                  ('xa_p90', 'us_xa'), ('chain_p90', 'us_xg_chain'),
                  ('keyp_p90', 'ss_keyPasses'), ('bcc_p90', 'ss_bigChancesCreated'),
                  ('press_p90', 'ss_possessionWonAttThird'),
                  ('fouled_p90', 'ss_wasFouled'), ('disp_p90', 'ss_dispossessed')]:
    m[key] = p90(base)
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
    F, fitfile = CB_F, 'output/cb_fit.csv'
else:
    pool = m[m.pos.str.contains('FW', na=False) & (m.season_nineties >= 12)].copy()
    F, fitfile = FW_F, 'output/forward_fit_adj.csv'
F = [c for c in F if c in pool.columns and pool[c].notna().sum() > 50]
Z = pool[F].apply(lambda s: (s - s.mean()) / s.std(ddof=0)).fillna(0.0)

tgt = pool[(pool.player.str.contains(NAME, na=False)) & (pool.season == SEASON)]
if tgt.empty:
    sys.exit(f'template "{NAME}" {SEASON} not found')
ti = tgt.index[0]
pool = pool.assign(dist=np.sqrt(((Z - Z.loc[ti]) ** 2).sum(axis=1)))

# closest season per player, then the N nearest players
best = pool.sort_values('dist').drop_duplicates('player')
best = best[(best.player != tgt.loc[ti, 'player']) & (~best.team.isin(EXCLUDE))]
typed = best.head(TOPN)
print(f'stage 1 — {TOPN} closest profiles to {tgt.loc[ti, "player"]} '
      f'{SEASON[:2]}/{SEASON[2:]}  (from {len(pool)} seasons)')

# ---------- stage 2: level ----------
fit = pd.read_csv(fitfile)
DIMS = (['FINISH', 'BOX', 'PRESS', 'HOLDUP', 'LINK', 'RUN'] if ROLE == 'fw'
        else ['BUILD', 'PROGRESS', 'AERIAL', 'DUEL', 'PACE', 'SECURE'])
keep = ['player', 'team', 'age', 'season_nineties', 'FIT', 'FLOOR',
        'fifa_value_eur', 'fifa_contract_end', 'fifa_pace'] + DIMS
fit = fit[[c for c in keep if c in fit.columns]]

out = typed[['player', 'dist']].merge(fit, on='player', how='inner')
print(f'stage 2 — {len(out)} of them cleared the fit model'
      f' (age/minutes filters applied there)\n')

out = out.sort_values('FIT', ascending=False)
hdr = (f"{'player':23}{'team':15}{'age':>4}{'90s':>5}{'dist':>6}"
       + ''.join(f'{d[:6]:>8}' for d in DIMS) + f"{'FIT':>7}{'FLR':>5}{'€M':>6}{'exp':>6}")
print('=' * len(hdr))
print(f'BEST PLAYERS *OF THIS TYPE* — ranked by system fit, not by similarity')
print('=' * len(hdr)); print(hdr)
for _, r in out.head(15).iterrows():
    print(f"{str(r.player)[:22]:23}{str(r.team)[:14]:15}{r.age:>4.0f}"
          f"{r.season_nineties:>5.0f}{r.dist:>6.2f}"
          + ''.join(f'{(r[d] if pd.notna(r[d]) else 0):>8.0f}' for d in DIMS)
          + f"{r.FIT:>7.1f}{(r.FLOOR if pd.notna(r.FLOOR) else 0):>5.0f}"
          f"{(r.fifa_value_eur/1e6 if pd.notna(r.fifa_value_eur) else 0):>6.0f}"
          f"{str(r.fifa_contract_end)[:4]:>6}")
print('=' * len(hdr))
print('dist = profile distance from the template (lower = same job)')
print('FIT/FLR = possession-adjusted system fit and weakest dimension')
out.to_csv(f'output/type_then_quality_{ROLE}.csv', index=False, encoding='utf-8')
