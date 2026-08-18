"""Remaining Understat Barcelona pulls (shots/player_matches/schedule).
team_matches already saved by barca_pull.py. No timeout: shot_events fetches
per-match, so it is slow but caches as it goes.
"""
import os
import pandas as pd
import soccerdata as sd

SEASONS = ['2425', '2526']
OUT = 'data/barcelona'
os.makedirs(OUT, exist_ok=True)
us = sd.Understat(leagues='ESP-La Liga', seasons=SEASONS)


def keep_barca_rows(df):
    df = df.reset_index()
    m = df.apply(lambda r: r.astype(str).str.contains('Barcelona', case=False).any(), axis=1)
    return df[m]


def save(df, name):
    p = f'{OUT}/{name}.csv'
    df.to_csv(p, index=False)
    print(f'{name}: {df.shape} -> {p}', flush=True)


save(keep_barca_rows(us.read_shot_events()), 'understat_shots')
save(keep_barca_rows(us.read_player_match_stats()), 'understat_player_matches')
save(keep_barca_rows(us.read_schedule()), 'understat_schedule')
print('done', flush=True)
