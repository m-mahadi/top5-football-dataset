"""Merge every source into one player-season dataset, ready for publication.

Spine = scout_base (FBref basics + Understat xG), joined to SofaScore
season aggregates (defensive/passing detail) and SoFIFA (value, contract, pace).
Reports match rates at each step; no silent joins.
Output: data/master/player_seasons.csv
"""
import re
import unicodedata
from pathlib import Path
import pandas as pd

OUT = Path('data/master')
OUT.mkdir(parents=True, exist_ok=True)


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z ]', ' ', s).lower()
    return re.sub(r'\s+', ' ', s).strip()


def surname(s):
    parts = norm(s).split()
    return parts[-1] if parts else ''


def canon_team(s):
    s = norm(s)
    for w in ('fc', 'cf', 'rc', 'sc', 'ac', 'as', 'ss', 'us', 'ssc', 'afc'):
        s = re.sub(rf'\b{w}\b', '', s)
    return re.sub(r'\s+', ' ', s).strip()


# ---------- 1. spine: FBref + Understat ----------
base = pd.read_csv('data/clean/scout_base.csv', low_memory=False)
base['season'] = base.season.astype(str)
keep_fb = ['league', 'season', 'team', 'player', 'nation', 'pos', 'age', 'born',
           'nineties', 'season_nineties', 'multi_club',
           'playing_time_mp', 'playing_time_starts', 'playing_time_min',
           'performance_gls', 'performance_ast', 'performance_g_a',
           'performance_crdy', 'performance_crdr',
           'shooting_standard_sh', 'shooting_standard_sot',
           'shooting_standard_sot_pct', 'shooting_standard_g_sh']
keep_us = [c for c in base.columns if c.startswith('us_')]
keep_p90 = [c for c in base.columns if c.endswith('_p90')]
extra = [c for c in ('np_g_minus_xg',) if c in base.columns]
m = base[[c for c in keep_fb if c in base.columns] + keep_us + keep_p90 + extra].copy()
m = m.rename(columns={c: c.replace('performance_', 'fb_').replace('shooting_standard_', 'fb_')
                      for c in m.columns})
m['_name'] = m.player.map(norm)
m['_sur'] = m.player.map(surname)
m['_team'] = m.team.map(canon_team)
print(f'spine (FBref+Understat): {len(m)} player-seasons')

# ---------- 2. SofaScore season aggregates ----------
ss = pd.read_csv('data/clean/sofascore_player_seasons.csv', low_memory=False)
ss['season'] = ss.season.astype(str)
drop = {'league', 'tourn_id', 'season_id', 'position', 'team'}
ss_cols = [c for c in ss.columns if c not in drop and c not in ('player', 'season')]
ss = ss.rename(columns={c: f'ss_{c}' for c in ss_cols})
ss['_name'] = ss.player.map(norm)
ss['_team'] = ss.team.map(canon_team)
ss['_sur'] = ss.player.map(surname)

# pass 1: full name + season ; pass 2: surname + team + season
SSCOLS = [c for c in ss.columns if c.startswith('ss_')]
p1 = ss.drop_duplicates(['_name', 'season'])
m = m.merge(p1[['_name', 'season'] + SSCOLS], on=['_name', 'season'], how='left')
hit1 = m.ss_player_id.notna().sum()

miss = m.ss_player_id.isna()
p2 = ss.drop_duplicates(['_sur', '_team', 'season'])
fill = m.loc[miss, ['_sur', '_team', 'season']].merge(
    p2[['_sur', '_team', 'season'] + SSCOLS], on=['_sur', '_team', 'season'], how='left')
for c in SSCOLS:
    m.loc[miss, c] = fill[c].values
hit2 = m.ss_player_id.notna().sum()
print(f'SofaScore matched: {hit1} by name, +{hit2-hit1} by surname+team = '
      f'{hit2}/{len(m)} ({hit2/len(m)*100:.0f}%)')

# ---------- 3. SoFIFA (current snapshot: value / contract / pace) ----------
# SoFIFA abbreviates first names ("K. Mbappe"), and it is a CURRENT snapshot, so
# a 24/25 row cannot be matched on club if the player has since moved. Key on
# first-initial + surname, with club as a tiebreak and an age sanity check.
def ikey(s):
    p = norm(s).split()
    return f'{p[0][0]} {p[-1]}' if len(p) > 1 else (p[0] if p else '')

sf = pd.read_csv('data/clean/sofifa_players.csv', low_memory=False)
sf_cols = [c for c in sf.columns if c not in ('player', 'team', 'league', 'age',
                                              'positions', 'surname_key')]
sf = sf.rename(columns={c: f'fifa_{c}' for c in sf_cols})
sf['_ik'] = sf.player.map(ikey)
sf['_team'] = sf.team.map(canon_team)
sf['fifa_age'] = sf['age'] if 'age' in sf.columns else pd.NA
FCOLS = [c for c in sf.columns if c.startswith('fifa_')]

m['_ik'] = m.player.map(ikey)
# pass 1: initial+surname AND club (safest)
p1 = sf.drop_duplicates(['_ik', '_team'])
m = m.merge(p1[['_ik', '_team'] + FCOLS], on=['_ik', '_team'], how='left')
h1 = m.fifa_value_eur.notna().sum()

# pass 2: initial+surname alone, only where that key is UNIQUE in SoFIFA
uniq = sf[~sf._ik.duplicated(keep=False)]
miss = m.fifa_value_eur.isna()
fill = m.loc[miss, ['_ik']].merge(uniq[['_ik'] + FCOLS], on='_ik', how='left')
for c in FCOLS:
    m.loc[miss, c] = fill[c].values
h2 = m.fifa_value_eur.notna().sum()
# age sanity: SoFIFA is 2026, so it must not be YOUNGER than the season age
bad = (m.fifa_age.notna() & m.age.notna() &
       ((m.fifa_age < m.age - 1) | (m.fifa_age > m.age + 3)))
m.loc[bad, FCOLS] = pd.NA
h3 = m.fifa_value_eur.notna().sum()
print(f'SoFIFA matched: {h1} by name+club, +{h2-h1} by unique name, '
      f'-{h2-h3} rejected on age = {h3}/{len(m)} ({h3/len(m)*100:.0f}%)')
m = m.drop(columns=['_ik'])


# ---------- 3b. repair Understat misses (compound surnames) ----------
# scout_base keys Understat on the full normalised name, which fails for
# compound surnames ("Kylian Mbappe-Lottin" vs "Kylian Mbappe"). Retry using
# first-initial + ANY surname token, accepting only unambiguous hits.
u = pd.read_csv('data/clean/understat_players.csv', low_memory=False)
u['season'] = u.season.astype(str)
UCOLS = ['xg', 'np_xg', 'xa', 'xg_chain', 'xg_buildup', 'shots', 'key_passes',
         'np_goals', 'minutes']


def cand_keys(name):
    p = norm(name).split()
    return {f'{p[0][0]} {t}' for t in p[1:]} if len(p) > 1 else set()


ulook = {}
for _, r in u.iterrows():
    for k in cand_keys(r.player):
        ulook.setdefault((k, r.season), []).append(r)

need = m.us_np_xg.isna()
fixed = 0
for i in m.index[need]:
    hits = []
    for k in cand_keys(m.at[i, 'player']):
        hits += ulook.get((k, str(m.at[i, 'season'])), [])
    ids = {h.get('player_id') for h in hits}
    if len(ids) == 1:
        h = hits[0]
        for c in UCOLS:
            if f'us_{c}' in m.columns:
                m.at[i, f'us_{c}'] = h[c]
        fixed += 1
if fixed:
    nz = m.season_nineties.replace(0, pd.NA)
    for name, col in (('np_xg', 'us_np_xg'), ('xa', 'us_xa'),
                      ('xg_chain', 'us_xg_chain'), ('shots', 'us_shots'),
                      ('key_passes', 'us_key_passes')):
        if f'{name}_p90' in m.columns:
            m[f'{name}_p90'] = pd.to_numeric(m[col], errors='coerce') / nz
    m['np_g_minus_xg'] = (pd.to_numeric(m.us_np_goals, errors='coerce')
                          - pd.to_numeric(m.us_np_xg, errors='coerce'))
print(f'Understat repaired: +{fixed} rows -> {m.us_np_xg.notna().sum()}/{len(m)} '
      f'({m.us_np_xg.notna().mean()*100:.0f}%)')

# SoFIFA's combined face-stat headers are ambiguous ("Pace / Diving" serves both
# outfield pace and GK diving). Alias the ones we actually use, drop raw dupes.
ALIAS = {'fifa_pace_diving': 'fifa_pace',
         'fifa_shooting_handling': 'fifa_face_shooting',
         'fifa_passing_kicking': 'fifa_face_passing',
         'fifa_dribbling_reflexes': 'fifa_face_dribbling',
         'fifa_defending_pace': 'fifa_face_defending',
         'fifa_physical_positioning': 'fifa_face_physical'}
m = m.rename(columns={k: v for k, v in ALIAS.items() if k in m.columns})
m = m.drop(columns=[c for c in ('fifa_blank', 'fifa_name', 'fifa_team_contract',
                                'fifa_value', 'fifa_wage', 'fifa_release_clause')
                    if c in m.columns])

# columns that carry no information for anybody: constants, and FIFA group
# aggregates that are just sums of attributes already present in the same row.
DEAD_COLS = [
    'ss_type',                 # constant 'overall'
    'fifa_loan_date_end',      # constant single date
    'fifa_birth_year',         # age is already present
    'fifa_best_overall',       # duplicate of overall/potential
    'fifa_total_attacking', 'fifa_total_skill', 'fifa_total_movement',
    'fifa_total_power', 'fifa_total_mentality', 'fifa_total_defending',
    'fifa_total_goalkeeping', 'fifa_total_stats', 'fifa_base_stats',
]
gone = [c for c in DEAD_COLS if c in m.columns]
if gone:
    m = m.drop(columns=gone)
    print(f'dropped {len(gone)} redundant/constant columns')

# drop all-empty columns: FBref serves several advanced tables near-empty, so
# their derived per-90s carry no data, and SoFIFA's list view returns work-rate
# blank. Shipping empty columns misleads anyone reading the schema.
empty = [c for c in m.columns if m[c].notna().sum() == 0]
if empty:
    m = m.drop(columns=empty)
    print(f'dropped {len(empty)} all-empty columns: {", ".join(sorted(empty))}')

# ---------- 4. tidy ----------
m = m.drop(columns=[c for c in ('_name', '_sur', '_team') if c in m.columns])
m = m.loc[:, ~m.columns.duplicated()].copy()
m['season_label'] = '20' + m.season.astype(str).str[:2] + '/' + m.season.astype(str).str[2:]
front = ['league', 'season', 'season_label', 'team', 'player', 'nation', 'pos', 'age',
         'nineties', 'season_nineties', 'multi_club']
m = m[[c for c in front if c in m.columns] +
      [c for c in m.columns if c not in front]]
m.to_csv(OUT / 'player_seasons.csv', index=False, encoding='utf-8')
print(f'\nMASTER: {m.shape[0]} rows x {m.shape[1]} cols -> {OUT}/player_seasons.csv')
print('source blocks:',
      {'fbref': sum(c.startswith('fb_') for c in m.columns),
       'understat': sum(c.startswith('us_') for c in m.columns),
       'sofascore': sum(c.startswith('ss_') for c in m.columns),
       'sofifa': sum(c.startswith('fifa_') for c in m.columns),
       'per90': sum(c.endswith('_p90') for c in m.columns)})
