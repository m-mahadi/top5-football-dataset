"""Pull Understat player-season xG data for the top-5 leagues, both seasons.
Understat = xG-native, exactly the Big 5, no login. Fills FBref's missing xG.
Output: data/understat/players_<season>.csv
"""
import os
import pandas as pd
import soccerdata as sd

LEAGUES = ['ENG-Premier League', 'ESP-La Liga', 'ITA-Serie A',
           'GER-Bundesliga', 'FRA-Ligue 1']
SEASONS = ['2425', '2526']
OUT = 'data/understat'
os.makedirs(OUT, exist_ok=True)

for season in SEASONS:
    us = sd.Understat(leagues=LEAGUES, seasons=season)
    df = us.read_player_season_stats()
    path = f'{OUT}/players_{season}.csv'
    df.to_csv(path)
    print(f'{season}: {df.shape[0]} players -> {path}')

# ponytail: player-season is the deliverable; per-shot events skipped, add if needed
