"""Phase 2 (final): which forwards fit Flick's Barcelona best.

The brief in plain terms: press like Raphinha, finish like Lewandowski, hold the
ball up against a deep block, live in the box, and link play in a 67%-possession
side. So we score SIX dimensions, each from real match data, and judge a player
on his FLOOR as well as his average - a forward who is elite at one thing and
useless at the rest does not fit this system.

Dimensions are percentile ranks within the forward pool, so 50 = median forward.
Output: output/forward_fit.csv
"""
import numpy as np
import pandas as pd

MIN90 = 15          # minimum 90s across both seasons to be ranked
THIN = 25           # below this, flag the sample as thin
AGE_MAX = 30

m = pd.read_csv('data/master/player_seasons.csv', low_memory=False)
m['season'] = m.season.astype(str)
m = m.sort_values('nineties', ascending=False).drop_duplicates(['player', 'season'])

SUMS = ['us_np_xg', 'us_xa', 'us_xg_chain', 'us_shots', 'us_np_goals', 'us_goals',
        'ss_shotsFromInsideTheBox', 'ss_totalShots', 'ss_goalsFromInsideTheBox',
        'ss_bigChancesCreated', 'ss_bigChancesMissed', 'ss_keyPasses',
        'ss_possessionWonAttThird', 'ss_ballRecovery', 'ss_tackles',
        'ss_wasFouled', 'ss_dispossessed', 'ss_aerialDuelsWon',
        'ss_successfulDribbles', 'ss_touches', 'ss_goals', 'fb_ast']
agg = {c: 'sum' for c in SUMS if c in m.columns}
agg.update({'season_nineties': 'sum', 'nineties': 'sum', 'age': 'max',
            'league': 'last', 'team': 'last', 'pos': 'last', 'season': 'nunique',
            'fifa_value_eur': 'max', 'fifa_release_clause_eur': 'max',
            'fifa_contract_end': 'max', 'fifa_pace': 'max',
            'fifa_acceleration': 'max', 'fifa_finishing': 'max',
            'fifa_strength': 'max', 'fifa_composure': 'max',
            'fifa_heading_accuracy': 'max', 'fifa_attack_position': 'max',
            'fifa_best_position': 'last', 'fifa_overall_rating': 'max',
            'fifa_potential': 'max',
            'ss_aerialDuelsWonPercentage': 'mean',
            'ss_groundDuelsWonPercentage': 'mean',
            'ss_accuratePassesPercentage': 'mean',
            'ss_goalConversionPercentage': 'mean'})
p = m.groupby('player').agg(agg).rename(columns={'season': 'seasons'}).reset_index()

n = p.season_nineties.replace(0, np.nan)
p['npxg_p90'] = p.us_np_xg / n
p['npxg_per_shot'] = p.us_np_xg / p.us_shots.replace(0, np.nan)
p['shots_p90'] = p.us_shots / n
p['box_shots_p90'] = p.ss_shotsFromInsideTheBox / n
p['box_share'] = p.ss_shotsFromInsideTheBox / p.ss_totalShots.replace(0, np.nan)
p['press_p90'] = p.ss_possessionWonAttThird / n
p['recov_p90'] = p.ss_ballRecovery / n
p['tackles_p90'] = p.ss_tackles / n
p['fouled_p90'] = p.ss_wasFouled / n
p['aerials_p90'] = p.ss_aerialDuelsWon / n
p['disp_p90'] = p.ss_dispossessed / n
p['xa_p90'] = p.us_xa / n
p['chain_p90'] = p.us_xg_chain / n
p['keyp_p90'] = p.ss_keyPasses / n
p['bcc_p90'] = p.ss_bigChancesCreated / n
p['dribbles_p90'] = p.ss_successfulDribbles / n
p['np_g_minus_xg'] = p.us_np_goals - p.us_np_xg
p['goals_p90'] = p.ss_goals / n
p['ga_p90'] = (p.ss_goals.fillna(0) + p.fb_ast.fillna(0)) / n

is_fw = p.pos.str.contains('FW', na=False)
# "plays as a nine": EA best position ST/CF, OR most shots taken inside the box.
# Behavioural, because EA labels Julian Alvarez a CAM while he plays centrally.
p['is_nine'] = (p.fifa_best_position.isin(['ST', 'CF'])
                | ((p.box_share >= 0.55) & is_fw))
ranked = p[is_fw & p.is_nine & (p.season_nineties >= MIN90)
           & (p.age <= AGE_MAX) & p.npxg_p90.notna()].copy()
barca = p[is_fw & (p.team == 'Barcelona') & (p.season_nineties >= 8)].copy()
print('centre-forward pool: %d  (plays as a nine, age<=%d, >=%d x90, top-5)'
      % (len(ranked), AGE_MAX, MIN90))

# ---- six dimensions, each a weighted blend of percentile ranks --------------
DIMS = {
    'FINISH': [('npxg_per_shot', .45), ('ss_goalConversionPercentage', .35),
               ('fifa_finishing', .20)],
    'BOX':    [('box_shots_p90', .45), ('npxg_p90', .35), ('box_share', .20)],
    'PRESS':  [('press_p90', .55), ('recov_p90', .25), ('tackles_p90', .20)],
    'HOLDUP': [('fouled_p90', .35), ('ss_aerialDuelsWonPercentage', .25),
               ('ss_groundDuelsWonPercentage', .25), ('disp_p90', -.15)],
    'LINK':   [('xa_p90', .30), ('chain_p90', .25), ('keyp_p90', .20),
               ('bcc_p90', .15), ('ss_accuratePassesPercentage', .10)],
    'RUN':    [('fifa_pace', .40), ('dribbles_p90', .35), ('fifa_acceleration', .25)],
}
# percentile ranks are computed against the ranked pool; Barca players are then
# scored on the same scale so the benchmark is directly comparable
allrows = pd.concat([ranked, barca[~barca.player.isin(ranked.player)]])


def pct_against_pool(col):
    ref = ranked[col].dropna()
    if ref.empty:
        return pd.Series(np.nan, index=allrows.index)
    return allrows[col].apply(
        lambda v: np.nan if pd.isna(v) else (ref < v).mean() * 100)


PCT = {c: pct_against_pool(c) for c in
       {c for spec in DIMS.values() for c, _ in spec}}
for dim, spec in DIMS.items():
    tot = sum(abs(w) for _, w in spec)
    acc = pd.Series(0.0, index=allrows.index)
    wsum = pd.Series(0.0, index=allrows.index)
    for col, w in spec:
        v = PCT[col]
        v = (100 - v) if w < 0 else v          # negative weight = lower is better
        ok = v.notna()
        acc[ok] += v[ok] * abs(w)
        wsum[ok] += abs(w)
    allrows[dim] = (acc / wsum.replace(0, np.nan)).round(0)

D = list(DIMS)
# system weights: possession side vs deep blocks -> link and press lead
W = {'BOX': .22, 'PRESS': .20, 'HOLDUP': .18, 'FINISH': .18, 'LINK': .15, 'RUN': .07}
allrows['FIT'] = sum(allrows[k] * w for k, w in W.items()).round(1)
allrows['FLOOR'] = allrows[D].min(axis=1).round(0)   # weakest required trait
allrows['thin'] = allrows.season_nineties < THIN

cand = allrows[(allrows.team != 'Barcelona') & allrows.player.isin(ranked.player)]
cand = cand.sort_values('FIT', ascending=False)
cand.to_csv('output/forward_fit.csv', index=False, encoding='utf-8')

HDR = (f"{'player':22}{'team':15}{'age':>4}{'90s':>5}"
       + ''.join(f'{d:>7}' for d in D) + f"{'FIT':>7}{'FLR':>5}{'€M':>6}{'exp':>6}")


def show(r, mark=''):
    return (f"{str(r.player)[:21]:22}{str(r.team)[:14]:15}{r.age:>4.0f}"
            f"{r.season_nineties:>5.0f}"
            + ''.join(f'{(r[d] if pd.notna(r[d]) else 0):>7.0f}' for d in D)
            + f"{r.FIT:>7.1f}{(r.FLOOR if pd.notna(r.FLOOR) else 0):>5.0f}"
            f"{(r.fifa_value_eur/1e6 if pd.notna(r.fifa_value_eur) else 0):>6.0f}"
            f"{str(r.fifa_contract_end)[:4]:>6}{mark}")


print('\n' + '=' * 118)
print('BARCELONA BENCHMARK — what the system already has (same percentile scale)')
print('=' * 118); print(HDR)
for _, r in allrows[allrows.team == 'Barcelona'].sort_values('FIT', ascending=False).iterrows():
    print(show(r))
TARGETS = 'Julián Álvarez|Dušan Vlahović'
tg = allrows[allrows.player.str.contains(TARGETS, na=False, regex=True)]
if len(tg):
    print(chr(10) + '=' * 118)
    print('REPORTED BARCELONA TARGETS - how they actually score')
    print('=' * 118); print(HDR)
    for _, r in tg.sort_values('FIT', ascending=False).iterrows():
        print(show(r))


print('\n' + '=' * 118)
print('BEST OVERALL FIT — balanced forwards (FLOOR >= 40: no fatal weakness)')
print('=' * 118); print(HDR)
bal = cand[(cand.FLOOR >= 40) & ~cand.thin]
for _, r in bal.head(12).iterrows():
    print(show(r))

print('\n' + '-' * 118)
print('SAME TEST, THIN SAMPLE (<%d x90 — promising but less certain)' % THIN)
for _, r in cand[(cand.FLOOR >= 40) & cand.thin].head(6).iterrows():
    print(show(r, '  *'))

print('\n' + '-' * 118)
print('HIGH FIT BUT ONE BAD WEAKNESS (floor < 40) — the trap signings')
for _, r in cand[(cand.FLOOR < 40)].head(6).iterrows():
    weak = [d for d in D if pd.notna(r[d]) and r[d] < 40]
    print(f"   {str(r.player)[:21]:22}{str(r.team)[:14]:15} FIT {r.FIT:>5.1f}"
          f"   weak: {', '.join(f'{d} {r[d]:.0f}' for d in weak)}")

print('\n' + '=' * 118)
print('FINISHING WATCHLIST — over/underperformance vs xG (regression risk, not skill)')
top = cand.head(20)
for _, r in top.reindex(top.np_g_minus_xg.abs().sort_values(ascending=False).index).head(6).iterrows():
    tag = 'OVER (likely to fall back)' if r.np_g_minus_xg > 0 else 'UNDER (may improve)'
    print(f"   {str(r.player)[:21]:22} {r.np_g_minus_xg:>+6.1f} np goals vs npxG   {tag}")
print('=' * 118)
print('Dimension key: FINISH=conversion quality  BOX=scoring positions  '
      'PRESS=wins in att third\n  HOLDUP=fouls won/duels/ball retention  '
      'LINK=xA,xGChain,key passes  RUN=pace & carrying')
print('FLR = lowest of the six. Weights: BOX .22 PRESS .20 HOLDUP .18 '
      'FINISH .18 LINK .15 RUN .07')
