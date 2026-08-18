"""Phase 3: which centre-backs fit Flick's Barcelona.

What the system demands, measured in Phase 1 rather than assumed:
  - the CB line sits at x=41.7/100, very high -> recovery pace is insurance
  - Cubarsi touches the ball 97.6 times a match -> the CB is the build-up hub
  - 66.8% possession -> few defensive actions, but errors are punished hard

Six dimensions, all possession-adjusted so a defender at a passive side is not
penalised for facing more work. Ratio metrics (pass %, duel %, aerial %) are
already team-neutral and are left alone.

SECURE is inverted: errors, being dribbled past and fouls all count against.
Output: output/cb_fit.csv
"""
import numpy as np
import pandas as pd

MIN90 = 15
THIN = 25
AGE_MAX = 30

m = pd.read_csv('data/master/player_seasons_adj.csv', low_memory=False)
m['season'] = m.season.astype(str)
m = m.sort_values('nineties', ascending=False).drop_duplicates(['player', 'season'])

SUMS = ['ss_accuratePasses', 'ss_totalPasses', 'ss_accurateOwnHalfPasses',
        'ss_accurateOppositionHalfPasses', 'ss_accurateFinalThirdPasses',
        'ss_accurateLongBalls', 'ss_clearances', 'ss_interceptions',
        'ss_blockedShots', 'ss_tackles', 'ss_tacklesWon', 'ss_aerialDuelsWon',
        'ss_groundDuelsWon', 'ss_successfulDribbles', 'ss_errorLeadToShot',
        'ss_errorLeadToGoal', 'ss_dribbledPast', 'ss_fouls', 'ss_ballRecovery']
SUMS += [c + '_adj' for c in SUMS]
agg = {c: 'sum' for c in SUMS if c in m.columns}
agg.update({'season_nineties': 'sum', 'nineties': 'sum', 'age': 'max',
            'league': 'last', 'team': 'last', 'pos': 'last', 'season': 'nunique',
            'fifa_value_eur': 'max', 'fifa_release_clause_eur': 'max',
            'fifa_contract_end': 'max', 'fifa_pace': 'max',
            'fifa_sprint_speed': 'max', 'fifa_acceleration': 'max',
            'ss_topSpeed': 'max', 'ss_numberOfSprints': 'sum',
            'ss_kilometersCovered': 'sum',
            'fifa_best_position': 'last', 'fifa_height': 'last',
            'fifa_defensive_awareness': 'max', 'fifa_composure': 'max',
            'fifa_overall_rating': 'max', 'fifa_potential': 'max',
            'ss_accuratePassesPercentage': 'mean',
            'ss_accurateLongBallsPercentage': 'mean',
            'ss_aerialDuelsWonPercentage': 'mean',
            'ss_groundDuelsWonPercentage': 'mean',
            'ss_totalDuelsWonPercentage': 'mean',
            'ss_tacklesWonPercentage': 'mean'})
p = m.groupby('player').agg(agg).rename(columns={'season': 'seasons'}).reset_index()

n = p.season_nineties.replace(0, np.nan)
for base in ['ss_accuratePasses', 'ss_accurateOwnHalfPasses',
             'ss_accurateOppositionHalfPasses', 'ss_accurateFinalThirdPasses',
             'ss_accurateLongBalls', 'ss_clearances', 'ss_interceptions',
             'ss_blockedShots', 'ss_aerialDuelsWon', 'ss_successfulDribbles',
             'ss_errorLeadToShot', 'ss_dribbledPast', 'ss_fouls',
             'ss_ballRecovery', 'ss_tackles']:
    src = base + '_adj' if base + '_adj' in p.columns else base
    p[base + '_p90'] = p[src] / n
p['sprints_p90'] = p.ss_numberOfSprints / n
p['km_p90'] = p.ss_kilometersCovered / n

# centre-backs: EA best position where known, else behavioural (a full-back does
# not clear and head this much)
is_df = p.pos.str.startswith('DF', na=False)
p['is_cb'] = ((p.fifa_best_position == 'CB')
              | (is_df & (p.ss_clearances_p90 >= 3.0)
                 & (p.ss_aerialDuelsWon_p90 >= 1.5)))

ranked = p[is_df & p.is_cb & (p.season_nineties >= MIN90)
           & (p.age <= AGE_MAX) & p.ss_accuratePassesPercentage.notna()].copy()
barca = p[is_df & p.is_cb & (p.team == 'Barcelona') & (p.season_nineties >= 8)].copy()
print('centre-back pool: %d  (age<=%d, >=%d x90, top-5)' % (len(ranked), AGE_MAX, MIN90))

DIMS = {
    'BUILD':   [('ss_accuratePassesPercentage', .35), ('ss_accuratePasses_p90', .25),
                ('ss_accurateLongBallsPercentage', .25),
                ('ss_accurateOwnHalfPasses_p90', .15)],
    'PROGRESS': [('ss_accurateOppositionHalfPasses_p90', .40),
                 ('ss_accurateFinalThirdPasses_p90', .35),
                 ('ss_successfulDribbles_p90', .25)],
    'AERIAL':  [('ss_aerialDuelsWonPercentage', .60), ('ss_aerialDuelsWon_p90', .40)],
    'DUEL':    [('ss_groundDuelsWonPercentage', .40), ('ss_tacklesWonPercentage', .30),
                ('ss_totalDuelsWonPercentage', .30)],
    'PACE':    [('ss_topSpeed', .60), ('sprints_p90', .40)],
    'SECURE':  [('ss_errorLeadToShot_p90', -.30), ('ss_dribbledPast_p90', -.30),
                ('ss_fouls_p90', -.20), ('fifa_defensive_awareness', .20)],
}
allrows = pd.concat([ranked, barca[~barca.player.isin(ranked.player)]])


def pct(col):
    ref = ranked[col].dropna()
    if ref.empty:
        return pd.Series(np.nan, index=allrows.index)
    return allrows[col].apply(lambda v: np.nan if pd.isna(v) else (ref < v).mean() * 100)


PCT = {c: pct(c) for c in {c for spec in DIMS.values() for c, _ in spec}}
for dim, spec in DIMS.items():
    acc = pd.Series(0.0, index=allrows.index)
    wsum = pd.Series(0.0, index=allrows.index)
    for col, w in spec:
        v = PCT[col]
        v = (100 - v) if w < 0 else v
        ok = v.notna()
        acc[ok] += v[ok] * abs(w)
        wsum[ok] += abs(w)
    allrows[dim] = (acc / wsum.replace(0, np.nan)).round(0)

D = list(DIMS)
# a high line lives on pace and on not making mistakes; the CB is also the
# build-up hub, so BUILD leads
W = {'BUILD': .22, 'PACE': .20, 'SECURE': .17, 'DUEL': .16, 'AERIAL': .13,
     'PROGRESS': .12}
allrows['FIT'] = sum(allrows[k] * w for k, w in W.items()).round(1)
allrows['FLOOR'] = allrows[D].min(axis=1).round(0)
allrows['thin'] = allrows.season_nineties < THIN

cand = allrows[(allrows.team != 'Barcelona') & allrows.player.isin(ranked.player)]
cand = cand.sort_values('FIT', ascending=False)
cand.to_csv('output/cb_fit.csv', index=False, encoding='utf-8')

HDR = (f"{'player':22}{'team':15}{'age':>4}{'90s':>5}"
       + ''.join(f'{d:>9}' for d in D) + f"{'FIT':>7}{'FLR':>5}{'€M':>6}{'exp':>6}{'km/h':>7}")


def show(r, mark=''):
    return (f"{str(r.player)[:21]:22}{str(r.team)[:14]:15}{r.age:>4.0f}"
            f"{r.season_nineties:>5.0f}"
            + ''.join(f'{(r[d] if pd.notna(r[d]) else 0):>9.0f}' for d in D)
            + f"{r.FIT:>7.1f}{(r.FLOOR if pd.notna(r.FLOOR) else 0):>5.0f}"
            f"{(r.fifa_value_eur/1e6 if pd.notna(r.fifa_value_eur) else 0):>6.0f}"
            f"{str(r.fifa_contract_end)[:4]:>6}"
            f"{(r.ss_topSpeed if pd.notna(r.ss_topSpeed) else 0):>7.1f}{mark}")


print('\n' + '=' * 132)
print('BARCELONA BENCHMARK — the CBs Flick actually uses')
print('=' * 132); print(HDR)
for _, r in allrows[allrows.team == 'Barcelona'].sort_values('FIT', ascending=False).iterrows():
    print(show(r))

print('\n' + '=' * 132)
print('BEST SYSTEM FIT — balanced centre-backs (FLOOR >= 40)')
print('=' * 132); print(HDR)
for _, r in cand[(cand.FLOOR >= 40) & ~cand.thin].head(12).iterrows():
    print(show(r))

print('\n' + '-' * 132)
print('THIN SAMPLE (<%d x90)' % THIN)
for _, r in cand[(cand.FLOOR >= 40) & cand.thin].head(5).iterrows():
    print(show(r, '  *'))

print('\n' + '-' * 132)
print('FAST BUT FLAWED — pace for the high line, a hole somewhere else')
fast = cand[(cand.PACE >= 75) & (cand.FLOOR < 40)]
for _, r in fast.head(6).iterrows():
    weak = [d for d in D if pd.notna(r[d]) and r[d] < 40]
    print(f"   {str(r.player)[:21]:22}{str(r.team)[:14]:15} PACE {r.PACE:>3.0f}  "
          f"FIT {r.FIT:>5.1f}   weak: {', '.join(f'{d} {r[d]:.0f}' for d in weak)}")
print('=' * 132)
print('BUILD=passing from the back  PROGRESS=ball forward  AERIAL / DUEL=defending')
print('PACE = MEASURED top speed (km/h) + sprints per 90, from SofaScore 2025/26')
print('  (EA scouted pace correlates with measured speed at only r=0.14 - not used)')
print('SECURE=few errors, rarely dribbled past')
print('Weights: BUILD .22 PACE .20 SECURE .17 DUEL .16 AERIAL .13 PROGRESS .12')
