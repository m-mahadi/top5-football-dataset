"""Phase 0: one analysis-ready row per player-season (top-5 leagues).

Merges all 11 FBref stat tables + the Understat xG block, adds per-90 versions of
the metrics we actually rank on. Everything downstream is a filter on this file.
Output: data/clean/scout_base.csv
"""
import re
import unicodedata
from pathlib import Path
import pandas as pd

BIG5 = ['ENG-Premier League', 'ESP-La Liga', 'ITA-Serie A',
        'GER-Bundesliga', 'FRA-Ligue 1']
KEY = ['league', 'season', 'team', 'player']
SRC = Path('data/clean/players')


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z ]', '', s.lower()).strip()


# --- merge the 11 FBref tables, keeping each file's *new* columns only ---
base = pd.read_csv(SRC / 'standard.csv')
base = base[base.league.isin(BIG5)].copy()
base['season'] = base.season.astype(str)

for f in sorted(SRC.glob('*.csv')):
    if f.name == 'standard.csv':
        continue
    d = pd.read_csv(f)
    d = d[d.league.isin(BIG5)].copy()
    d['season'] = d.season.astype(str)
    stat = f.stem
    new = [c for c in d.columns if c not in base.columns or c in KEY]
    d = d[new]
    # prefix non-key columns with the stat type so origins stay obvious
    d = d.rename(columns={c: f'{stat}_{c}' for c in d.columns if c not in KEY})
    base = base.merge(d, on=KEY, how='left')

print(f'FBref merged: {base.shape[0]} player-seasons, {base.shape[1]} cols')

# --- attach Understat xG ---
u = pd.read_csv('data/clean/understat_players.csv')
u['season'] = u.season.astype(str)
u['_k'] = u.player.map(norm) + '|' + u.season
ucols = ['xg', 'np_xg', 'xa', 'xg_chain', 'xg_buildup', 'shots', 'key_passes',
         'np_goals', 'minutes']
u = (u.sort_values('minutes', ascending=False)
       .drop_duplicates('_k')[['_k'] + ucols]
       .rename(columns={c: f'us_{c}' for c in ucols}))

base['_k'] = base.player.map(norm) + '|' + base.season
base = base.merge(u, on='_k', how='left').drop(columns='_k')
hit = base.us_np_xg.notna().mean()
print(f'Understat matched: {base.us_np_xg.notna().sum()} / {len(base)} ({hit*100:.0f}%)')

# --- per-90s for the metrics we rank on ---
base['nineties'] = pd.to_numeric(base.playing_time_90s, errors='coerce')
# FBref splits a transferred player into one row per club, but Understat xG is a
# SEASON total. Dividing season xG by one stint's minutes inflates per-90s, so
# Understat metrics use season-total minutes while FBref metrics stay per-stint.
_pk = base.player.map(norm) + '|' + base.season
base['season_nineties'] = _pk.map(base.groupby(_pk).nineties.sum())
base['multi_club'] = _pk.map(_pk.value_counts()) > 1
P90 = {
    # striker
    'np_xg': 'us_np_xg', 'xa': 'us_xa', 'xg_chain': 'us_xg_chain',
    'shots': 'us_shots', 'key_passes': 'us_key_passes',
    'box_touches': 'possession_touches_att_pen',
    'passes_received': 'possession_rec',
    'att_3rd_touches': 'possession_touches_att_3rd',
    'take_ons_succ': 'possession_take_ons_succ',
    # CB / build-up. FBref currently strips PrgC/PrgP counts, so use the
    # progressive *distance* equivalents, which survive and measure the same idea.
    'prog_carry_dist': 'possession_carries_prgdist',
    'prog_pass_dist': 'passing_total_prgdist',
    'carries_final_third': 'possession_carries_1_3',
    'carries_into_box': 'possession_carries_cpa',
    'carries': 'possession_carries_carries',
    'tackles': 'defense_tackles_tkl',
    'tackles_def_3rd': 'defense_tackles_def_3rd',
    'tackles_mid_3rd': 'defense_tackles_mid_3rd',
    'tackles_att_3rd': 'defense_tackles_att_3rd',
    'interceptions': 'defense_int',
    'blocks': 'defense_blocks_blocks',
    'fouls': 'misc_performance_fls',
    'tackles_won': 'misc_performance_tklw',
    # NOTE: FBref currently serves misc/ WITHOUT aerial duels -> no aerial metric here
    'errors': 'defense_err',
    'miscontrols': 'possession_carries_mis',
    'dispossessed': 'possession_carries_dis',
}
made = []
for name, col in P90.items():
    if col in base.columns:
        denom = base.season_nineties if col.startswith('us_') else base.nineties
        base[f'{name}_p90'] = pd.to_numeric(base[col], errors='coerce') / denom
        made.append(name)
    else:
        print(f'  [miss] {col} -> {name}_p90 skipped')

# rate stats (not per-90)
if 'misc_aerial_duels_won_pct' in base.columns:
    base['aerial_win_pct'] = pd.to_numeric(base['misc_aerial_duels_won_pct'], errors='coerce')
for src, dst in [('passing_total_cmp_pct','pass_cmp_pct'),('passing_long_cmp_pct','long_pass_cmp_pct'),('defense_challenges_tkl_pct','challenge_win_pct')]:
    if src in base.columns:
        base[dst] = pd.to_numeric(base[src], errors='coerce')
base['np_g_minus_xg'] = pd.to_numeric(base.us_np_goals, errors='coerce') - pd.to_numeric(base.us_np_xg, errors='coerce')
base['tackle_att3rd_share'] = pd.to_numeric(base.defense_tackles_att_3rd, errors='coerce') / pd.to_numeric(base.defense_tackles_tkl, errors='coerce')
base['tackle_def3rd_share'] = pd.to_numeric(base.defense_tackles_def_3rd, errors='coerce') / pd.to_numeric(base.defense_tackles_tkl, errors='coerce')

base['age'] = pd.to_numeric(base.age, errors='coerce')
out = 'data/clean/scout_base.csv'
base.to_csv(out, index=False, encoding='utf-8')

elig = base[(base.nineties >= 10) & base.us_np_xg.notna()]
print(f'per-90 metrics built: {len(made)}')
print(f'eligible (>=900 min & has xG): {len(elig)} player-seasons')
print(f'  of which age<=26: {(elig.age <= 26).sum()}')
print(f'-> {out}  {base.shape}')
