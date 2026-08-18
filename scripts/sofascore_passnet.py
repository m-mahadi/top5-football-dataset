"""Barcelona passing-network node layout, both seasons (24/25 + 25/26), all comps,
from SofaScore's free average-positions endpoint. One row per player per match:
average pitch position + touch count (network nodes; SofaScore gives nodes, not
pass edges).
Output: data/barcelona/sofascore_passing_network.csv
"""
import time
import datetime as dt
import pandas as pd
import tls_requests

TEAM = 2817  # FC Barcelona
BASE = 'https://api.sofascore.com/api/v1'


def season_tag(ts):
    d = dt.datetime.utcfromtimestamp(ts)
    yr = d.year if d.month >= 8 else d.year - 1
    return f'{str(yr)[2:]}{str(yr + 1)[2:]}'


# collect all finished Barca matches in the two seasons
matches = {}
for page in range(0, 16):
    r = tls_requests.get(f'{BASE}/team/{TEAM}/events/last/{page}', timeout=25)
    if r.status_code != 200:
        break
    evs = r.json().get('events', [])
    if not evs:
        break
    for e in evs:
        if e.get('status', {}).get('type') != 'finished':
            continue
        if season_tag(e.get('startTimestamp', 0)) in ('2425', '2526'):
            matches[e['id']] = e
    time.sleep(0.2)
print(f'Barca finished matches (2 seasons): {len(matches)}')

rows = []
for eid, e in sorted(matches.items(), key=lambda kv: kv[1]['startTimestamp']):
    home, away = e['homeTeam']['name'], e['awayTeam']['name']
    barca_home = 'Barcelona' in home
    date = dt.datetime.utcfromtimestamp(e['startTimestamp']).strftime('%Y-%m-%d')
    try:
        ap = tls_requests.get(f'{BASE}/event/{eid}/average-positions', timeout=25).json()
    except Exception as ex:
        print(f'  {date} {home} v {away}: ERR {ex}')
        continue
    nodes = ap.get('home' if barca_home else 'away', []) or []
    for n in nodes:
        rows.append({
            'season': season_tag(e['startTimestamp']), 'date': date, 'match_id': eid,
            'competition': e.get('tournament', {}).get('name'),
            'venue': 'H' if barca_home else 'A',
            'opponent': away if barca_home else home,
            'player': (n.get('player') or {}).get('name'),
            'avg_x': n.get('averageX'), 'avg_y': n.get('averageY'),
            'touches': n.get('pointsCount'),
        })
    print(f'  {date} {home} v {away}: {len(nodes)} nodes', flush=True)
    time.sleep(0.15)

df = pd.DataFrame(rows)
out = 'data/barcelona/sofascore_passing_network.csv'
df.to_csv(out, index=False)
print(f'\n{len(df)} player-match nodes across {df.match_id.nunique()} matches')
print('per season:', df.groupby('season').match_id.nunique().to_dict())
print(f'-> {out}')
