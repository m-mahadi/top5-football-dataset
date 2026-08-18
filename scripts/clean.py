"""Polish everything into data/clean/: flat single-row headers, snake_case
columns, consistent team names, one unified Barca shot table, a data dictionary.
Raw files under data/ are left untouched; clean/ is the analysis-ready copy.
"""
import re
import os
from pathlib import Path
import pandas as pd

CLEAN = Path('data/clean')
CLEAN.mkdir(parents=True, exist_ok=True)


def snake(s):
    s = str(s).replace('%', '_pct').replace('+/-', '_plusminus')
    s = re.sub(r'[^0-9a-zA-Z]+', '_', s).strip('_').lower()
    return re.sub(r'_+', '_', s)


def canon_team(s):
    s = str(s).strip()
    for p in ('FC ', 'CF ', 'RC ', 'SC '):
        if s.startswith(p):
            s = s[len(p):]
    for suf in (' FC', ' CF', ' CF.', ' SC'):
        if s.endswith(suf):
            s = s[:-len(suf)]
    return s.strip()


def flatten_fbref(path, n_idx):
    df = pd.read_csv(path, header=[0, 1], index_col=list(range(n_idx)))
    cols, seen = [], {}
    for a, b in df.columns:
        a, b = str(a), ('' if str(b).startswith('Unnamed') else str(b))
        name = snake(f'{a}_{b}' if b else a)
        if name in seen:
            seen[name] += 1
            name = f'{name}_{seen[name]}'
        else:
            seen[name] = 0
        cols.append(name)
    df.columns = cols
    return df.reset_index()


# 1) FBref season stats -> flat
fbref_sets = [
    ('data/players', 4, 'players'), ('data/teams', 3, 'teams'),
    ('data/worldcup/players', 4, 'wc_players'), ('data/worldcup/teams', 3, 'wc_teams'),
]
for src, nidx, prefix in fbref_sets:
    outdir = CLEAN / prefix
    outdir.mkdir(exist_ok=True)
    for f in sorted(Path(src).glob('*.csv')):
        df = flatten_fbref(f, nidx)
        if 'team' in df.columns:
            df['team'] = df['team'].map(canon_team)
        df.to_csv(outdir / f.name, index=False, encoding='utf-8')
    print(f'[flat] {prefix}: {len(list(outdir.glob("*.csv")))} files')

# 2) Understat league xG -> one file, both seasons
u = pd.concat([pd.read_csv(f) for f in sorted(Path('data/understat').glob('players_*.csv'))])
u['team'] = u['team'].map(canon_team)
u.to_csv(CLEAN / 'understat_players.csv', index=False, encoding='utf-8')
print(f'[merge] understat_players: {u.shape}')

# 3) Unified Barca shot table: La Liga (Understat, 0-1) + UCL (SofaScore, 0-100)
def norm_outcome(v):  # harmonise result labels across sources
    t = str(v).lower()
    if 'own' in t:
        return 'own_goal'
    for key, out in (('goal', 'goal'), ('miss', 'missed'), ('block', 'blocked'),
                     ('save', 'saved'), ('post', 'post')):
        if key in t:
            return out
    return t
ll = pd.read_csv('data/barcelona/understat_shots.csv')
ll = pd.DataFrame({
    'season': ll['season'].astype(str), 'competition': 'La Liga', 'date': ll.get('date'),
    'team': ll['team'].map(canon_team), 'player': ll['player'],
    'xg': ll['xg'], 'x': ll['location_x'] * 100, 'y': ll['location_y'] * 100,
    'situation': ll['situation'], 'body_part': ll.get('shotType', ll.get('body_part')),
    'outcome': ll['result'].map(norm_outcome),
    'minute': ll['minute'], 'source': 'understat',
})
uc = pd.read_csv('data/barcelona/sofascore_ucl_shots.csv')
uc = pd.DataFrame({
    'season': uc['season'].astype(str), 'competition': 'Champions League', 'date': uc['date'],
    'team': uc['team'].map(canon_team), 'player': uc['player'],
    'xg': uc['xg'], 'x': uc['x'], 'y': uc['y'],
    'situation': uc['situation'], 'body_part': uc['body_part'],
    'outcome': uc['shot_type'].map(norm_outcome),
    'minute': uc['minute'], 'source': 'sofascore',
})
shots = pd.concat([ll, uc], ignore_index=True)
shots.to_csv(CLEAN / 'barca_shots.csv', index=False, encoding='utf-8')
print(f'[unify] barca_shots: {shots.shape} '
      f'({(shots.team=="Barcelona").sum()} Barca, {shots.competition.nunique()} comps)')

# 4) Barca passing network + all-comps logs -> clean names
pn = pd.read_csv('data/barcelona/sofascore_passing_network.csv')
pn['opponent'] = pn['opponent'].map(canon_team)
pn.to_csv(CLEAN / 'barca_passing_network.csv', index=False, encoding='utf-8')
for tag in ('2425', '2526'):
    ac = pd.read_csv(f'data/barcelona/fbref_allcomps_{tag}.csv')
    ac.columns = [snake(c) for c in ac.columns]
    if 'opponent' in ac:
        ac['opponent'] = ac['opponent'].map(canon_team)
    ac.to_csv(CLEAN / f'barca_allcomps_{tag}.csv', index=False, encoding='utf-8')
print('[copy] passing network + all-comps logs cleaned')

# 5) World Cup shots -> clean names
ws = pd.read_csv('data/worldcup/sofascore_shots.csv')
ws['team'] = ws['team'].map(canon_team)
ws['opponent'] = ws['opponent'].map(canon_team)
ws['outcome'] = ws['shot_type'].map(norm_outcome)
ws.to_csv(CLEAN / 'wc_shots.csv', index=False, encoding='utf-8')
print(f'[copy] wc_shots: {ws.shape}')
print('\nclean layer written to data/clean/')
