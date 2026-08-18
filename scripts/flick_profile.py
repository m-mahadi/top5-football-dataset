"""Phase 1: measure what Flick's system actually demands, from Barca's own data.
Produces the numeric target ranges that Phases 2-3 screen candidates against.
"""
import pandas as pd

pn = pd.read_csv('data/clean/barca_passing_network.csv')
sh = pd.read_csv('data/clean/barca_shots.csv')
pn = pn[pn.competition.isin(['LaLiga', 'UEFA Champions League'])]

print('=' * 62)
print('A. DEFENSIVE LINE HEIGHT  (avg_x 0-100, own goal=0, attack=100)')
print('=' * 62)
cbs = ['Pau Cubarsí', 'Íñigo Martínez', 'Ronald Araújo', 'Eric García',
       'Andreas Christensen', 'Gerard Martín']
d = pn[pn.player.isin(cbs)]
prof = (d.groupby('player')
          .agg(matches=('match_id', 'nunique'), avg_x=('avg_x', 'mean'),
               touches=('touches', 'mean'))
          .query('matches >= 8').sort_values('avg_x', ascending=False).round(1))
print(prof.to_string())
line = d[d.player.isin(prof.index)].avg_x.mean()
print(f'\n  -> Barca CB line sits at x = {line:.1f} / 100')
print(f'  -> squad-wide average position: {pn.avg_x.mean():.1f}')
gk = pn[pn.player.str.contains('Szczęsny|Ter Stegen|Peña|García', na=False)]
print(f'  -> CB touches/match: {d.touches.mean():.0f} (build-up load)')

print()
print('=' * 62)
print('B. WHERE BARCA CREATE  (shot locations, x 0-100 toward goal)')
print('=' * 62)
b = sh[sh.team == 'Barcelona']
print(f'  shots: {len(b)}   total xG: {b.xg.sum():.0f}   xG/shot: {b.xg.mean():.3f}')
print(f'  median shot distance from goal line: x = {b.x.median():.1f}')
print(f'  share of shots inside x>83 (approx. box): '
      f'{(b.x > 83).mean()*100:.0f}%')
print('\n  by situation:')
sit = (b.groupby('situation').agg(shots=('xg', 'size'), xg=('xg', 'sum'),
                                  xg_per_shot=('xg', 'mean')).round(3)
       .sort_values('shots', ascending=False))
print(sit.head(6).to_string())

print()
print('=' * 62)
print('C. THE STRIKER ROLE  (what Lewandowski does / what must be replaced)')
print('=' * 62)
top = (b.groupby('player').agg(shots=('xg', 'size'), xg=('xg', 'sum'),
                               xg_per_shot=('xg', 'mean'),
                               goals=('outcome', lambda s: (s == 'goal').sum()),
                               med_x=('x', 'median'))
       .sort_values('xg', ascending=False).round(3))
print(top.head(6).to_string())
lew = top.loc['Robert Lewandowski'] if 'Robert Lewandowski' in top.index else None
if lew is not None:
    print(f'\n  -> Lewandowski takes {lew.shots/len(b)*100:.0f}% of Barca shots '
          f'at {lew.xg_per_shot:.3f} xG/shot from median x={lew.med_x:.0f}')
    print(f'  -> he converts {lew.goals:.0f} from {lew.xg:.1f} xG '
          f'({lew.goals - lew.xg:+.1f})')
    print('  -> REPLACEMENT TARGET: >= %.3f xG/shot, high box presence,'
          % lew.xg_per_shot)
    print('     plus the link play he does NOT provide (check xA/xgChain)')
