"""Phase 2 (v2): system-fit striker for Barcelona under Flick.

v1 was wrong: npxG/90 carried 30% of the weight, so raw chance volume dragged
pure poachers at counter-attacking sides up the list (Sorloth: 0.85 npxG/90 but
0.06 xA/90, age 29, 53%-possession side). A Flick 9 must also PRESS, HOLD UP,
and LINK. This version scores five explicit dimensions from real match data and
applies gates, so failing a core requirement cannot be bought off with goals.

Output: output/striker_shortlist.csv
"""
import numpy as np
import pandas as pd

m = pd.read_csv('data/master/player_seasons.csv', low_memory=False)
m['season'] = m.season.astype(str)
m = m.sort_values('nineties', ascending=False).drop_duplicates(['player', 'season'])
POS = m.set_index('player').pos.groupby(level=0).last()

SUMS = ['us_np_xg', 'us_xa', 'us_xg_chain', 'us_shots', 'us_np_goals',
        'ss_shotsFromInsideTheBox', 'ss_totalShots', 'ss_bigChancesCreated',
        'ss_keyPasses', 'ss_possessionWonAttThird', 'ss_ballRecovery',
        'ss_wasFouled', 'ss_dispossessed', 'ss_possessionLost',
        'ss_successfulDribbles', 'ss_touches', 'ss_aerialDuelsWon',
        'ss_totalDuelsWon', 'ss_minutesPlayed']
agg = {c: 'sum' for c in SUMS if c in m.columns}
agg.update({'season_nineties': 'sum', 'age': 'max', 'league': 'last',
            'team': 'last', 'season': 'nunique', 'fifa_value_eur': 'max',
            'fifa_contract_end': 'max', 'fifa_pace': 'max',
            'fifa_release_clause_eur': 'max',
            'ss_aerialDuelsWonPercentage': 'mean',
            'ss_groundDuelsWonPercentage': 'mean',
            'ss_accuratePassesPercentage': 'mean',
            'fifa_best_position': 'last', 'fifa_defensive_work_rate': 'last',
            'fifa_stamina': 'max', 'fifa_aggression': 'max'})
p = m.groupby('player').agg(agg).rename(columns={'season': 'seasons'}).reset_index()
p['pos'] = p.player.map(POS)

tm = pd.read_csv('data/clean/teams/standard.csv')
tm['poss'] = pd.to_numeric(tm.poss, errors='coerce')
p['team_poss'] = p.team.map(tm.groupby('team').poss.mean())

n = p.season_nineties.replace(0, np.nan)
p['np_xg_p90'] = p.us_np_xg / n
p['npxg_per_shot'] = p.us_np_xg / p.us_shots.replace(0, np.nan)
p['xa_p90'] = p.us_xa / n
p['xg_chain_p90'] = p.us_xg_chain / n
p['key_passes_p90'] = p.ss_keyPasses / n
p['big_chances_created_p90'] = p.ss_bigChancesCreated / n
p['press_won_att3rd_p90'] = p.ss_possessionWonAttThird / n     # PRESSING
p['ball_recov_p90'] = p.ss_ballRecovery / n
p['fouled_p90'] = p.ss_wasFouled / n                            # HOLD-UP
p['dispossessed_p90'] = p.ss_dispossessed / n
p['dribbles_p90'] = p.ss_successfulDribbles / n
p['box_shot_share'] = p.ss_shotsFromInsideTheBox / p.ss_totalShots.replace(0, np.nan)
p['np_g_minus_xg'] = p.us_np_goals - p.us_np_xg


def z(s):
    s = pd.to_numeric(s, errors='coerce')
    return (s - s.mean()) / s.std(ddof=0)


BARCA = p[p.team == 'Barcelona'].copy()
pool = p[(p.season_nineties >= 15) & (p.age <= 30) & (p.team != 'Barcelona')
         & p.pos.str.contains('FW', na=False) & p.np_xg_p90.notna()].copy()
print(f'pool: {len(pool)} forwards (age<=30, >=15x90, top-5, excl. Barca)')

both = pd.concat([pool, BARCA[BARCA.pos.str.contains('FW', na=False)]])


def dims(df, ref):
    """z-score each dimension against the POOL, so Barca players are comparable."""
    def zz(col, invert=False):
        s = pd.to_numeric(df[col], errors='coerce')
        r = pd.to_numeric(ref[col], errors='coerce')
        out = (s - r.mean()) / r.std(ddof=0)
        return -out if invert else out
    d = pd.DataFrame(index=df.index)
    d['FINISH'] = 0.6 * zz('np_xg_p90') + 0.4 * zz('npxg_per_shot')
    d['LINK'] = (0.4 * zz('xa_p90') + 0.3 * zz('xg_chain_p90')
                 + 0.2 * zz('key_passes_p90') + 0.1 * zz('big_chances_created_p90'))
    d['PRESS'] = 0.7 * zz('press_won_att3rd_p90') + 0.3 * zz('ball_recov_p90')
    d['HOLDUP'] = (0.4 * zz('fouled_p90') + 0.3 * zz('ss_aerialDuelsWonPercentage')
                   + 0.2 * zz('ss_groundDuelsWonPercentage')
                   + 0.1 * zz('dispossessed_p90', invert=True))
    d['SPACE'] = 0.6 * zz('fifa_pace').fillna(0) + 0.4 * zz('dribbles_p90')
    return d


D = dims(both, pool)
both = pd.concat([both.reset_index(drop=True), D.reset_index(drop=True)], axis=1)

# GATES: a Flick 9 cannot be elite at one thing and useless at the others.
GATE = -0.25
both['gates_passed'] = ((both.LINK > GATE).astype(int) + (both.PRESS > GATE).astype(int)
                        + (both.HOLDUP > GATE).astype(int))
W = {'FINISH': .25, 'LINK': .25, 'PRESS': .20, 'HOLDUP': .15, 'SPACE': .15}
both['score'] = sum(both[k] * w for k, w in W.items())

both['role'] = np.where(both.fifa_best_position.isin(['ST', 'CF']), 'CF',
                        np.where(both.fifa_best_position.isna(), '?', 'wide/AM'))
cand = both[both.team != 'Barcelona'].copy()
qual = cand[cand.gates_passed == 3].sort_values('score', ascending=False)
cand.sort_values('score', ascending=False).to_csv(
    'output/striker_shortlist.csv', index=False, encoding='utf-8')

hdr = (f"{'#':>2} {'player':21}{'team':15}{'age':>4}{'90s':>5}"
       f"{'FIN':>6}{'LINK':>6}{'PRESS':>6}{'HOLD':>6}{'SPACE':>6}"
       f"{'npxG/90':>8}{'G-xG':>6}{'€M':>6}{'exp':>6}{'poss':>6}")


def row(i, r):
    return (f"{i:>2} {str(r.player)[:20]:21}{str(r.team)[:14]:15}{r.age:>4.0f}"
            f"{r.season_nineties:>5.0f}{r.FINISH:>6.1f}{r.LINK:>6.1f}"
            f"{r.PRESS:>6.1f}{r.HOLDUP:>6.1f}{r.SPACE:>6.1f}"
            f"{r.np_xg_p90:>8.2f}{r.np_g_minus_xg:>+6.1f}"
            f"{(r.fifa_value_eur/1e6 if pd.notna(r.fifa_value_eur) else 0):>6.0f}"
            f"{str(r.fifa_contract_end)[:4]:>6}"
            f"{(r.team_poss if pd.notna(r.team_poss) else 0):>5.0f}%")


nine = qual[qual.role == 'CF']
wide = qual[qual.role == 'wide/AM']
print(chr(10) + '=' * 122)
print('TRUE CENTRE-FORWARDS (best position ST/CF) - cleared all 3 system gates')
print('=' * 122); print(hdr)
for i, (_, r) in enumerate(nine.head(10).iterrows(), 1):
    print(row(i, r))
print('-' * 122)
print('WIDE / ATTACKING-MID forwards that also cleared the gates (different role):')
for i, (_, r) in enumerate(wide.head(6).iterrows(), 1):
    print(row(i, r))
print('=' * 122)
print('BARCELONA BENCHMARK (same scale)')
for _, r in both[both.team == 'Barcelona'].sort_values('score', ascending=False).head(4).iterrows():
    print(row(0, r))
print('=' * 122)
print('FAILED GATES — high scorers who do not fit the system:')
fail = cand[cand.gates_passed < 3].sort_values('np_xg_p90', ascending=False).head(5)
for _, r in fail.iterrows():
    miss = [k for k in ('LINK', 'PRESS', 'HOLDUP') if getattr(r, k) <= GATE]
    print(f"   {str(r.player)[:22]:23}{str(r.team)[:14]:15} npxG/90 {r.np_xg_p90:.2f}"
          f"  fails: {','.join(miss)}")
