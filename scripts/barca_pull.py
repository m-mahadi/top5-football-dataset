"""Max Barcelona data under Hansi Flick (24/25 + 25/26 La Liga).
Understat = per-shot + per-match xG; FBref = per-match stat logs.
Output: data/barcelona/*.csv
"""
import os
import pandas as pd
import soccerdata as sd

SEASONS = ['2425', '2526']
OUT = 'data/barcelona'
os.makedirs(OUT, exist_ok=True)


def only_barca(df):
    # match any index/column level or 'team' col containing Barcelona
    if 'team' in df.columns:
        return df[df['team'].astype(str).str.contains('Barcelona', case=False, na=False)]
    for lvl in range(df.index.nlevels):
        vals = df.index.get_level_values(lvl).astype(str)
        if vals.str.contains('Barcelona', case=False).any():
            return df[vals.str.contains('Barcelona', case=False)]
    return df  # shot events etc. filtered separately


def save(df, name):
    p = f'{OUT}/{name}.csv'
    df.to_csv(p)
    print(f'  {name}: {df.shape} -> {p}')


us = sd.Understat(leagues='ESP-La Liga', seasons=SEASONS)

print('Understat:')
# per-match team xG (both teams every match); keep Barca matches
tm = us.read_team_match_stats()
save(only_barca(tm), 'understat_team_matches')

# per-shot events for the whole league, keep shots by/against Barca
shots = us.read_shot_events().reset_index()
mask = shots.apply(lambda r: r.astype(str).str.contains('Barcelona', case=False).any(), axis=1)
save(shots[mask], 'understat_shots')

# Barca players per match
pm = us.read_player_match_stats()
save(only_barca(pm), 'understat_player_matches')

# season schedule (results + match xG)
sch = us.read_schedule().reset_index()
smask = sch.apply(lambda r: r.astype(str).str.contains('Barcelona', case=False).any(), axis=1)
save(sch[smask], 'understat_schedule')

print('Understat done.')
