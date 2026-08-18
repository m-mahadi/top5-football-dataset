"""All shots from the 2026 World Cup via SofaScore's free shotmap API.
Per-shot xG + coordinates for every match (FBref has no WC xG).
Output: data/worldcup/sofascore_shots.csv
"""
import time
import datetime as dt
import pandas as pd
import tls_requests

TOURN, SEASON = 16, 58210  # FIFA World Cup 2026
BASE = 'https://api.sofascore.com/api/v1'

# 1) collect every finished match of the tournament season
matches = {}
for page in range(0, 12):
    r = tls_requests.get(f'{BASE}/unique-tournament/{TOURN}/season/{SEASON}/events/last/{page}', timeout=25)
    if r.status_code != 200:
        break
    evs = r.json().get('events', [])
    if not evs:
        break
    for e in evs:
        if e.get('status', {}).get('type') == 'finished':
            matches[e['id']] = e
    time.sleep(0.2)
print(f'WC2026 finished matches: {len(matches)}')

# 2) shotmap per match -> flat rows
rows = []
for eid, e in sorted(matches.items(), key=lambda kv: kv[1]['startTimestamp']):
    home, away = e['homeTeam']['name'], e['awayTeam']['name']
    date = dt.datetime.utcfromtimestamp(e['startTimestamp']).strftime('%Y-%m-%d')
    rnd = (e.get('roundInfo', {}) or {}).get('name') or ''
    try:
        j = tls_requests.get(f'{BASE}/event/{eid}/shotmap', timeout=25).json()
    except Exception as ex:
        print(f'  {date} {home} v {away}: ERR {ex}')
        continue
    sm = j.get('shotmap', []) or []
    for s in sm:
        pc = s.get('playerCoordinates', {}) or {}
        rows.append({
            'date': date, 'match_id': eid, 'round': rnd,
            'match': f'{home} v {away}',
            'team': home if s.get('isHome') else away,
            'opponent': away if s.get('isHome') else home,
            'player': (s.get('player') or {}).get('name'),
            'xg': s.get('xg'), 'xgot': s.get('xgot'),
            'x': pc.get('x'), 'y': pc.get('y'),
            'shot_type': s.get('shotType'), 'goal_type': s.get('goalType'),
            'situation': s.get('situation'), 'body_part': s.get('bodyPart'),
            'minute': s.get('time'),
        })
    print(f'  {date} {home} v {away}: {len(sm)} shots', flush=True)
    time.sleep(0.15)

df = pd.DataFrame(rows)
out = 'data/worldcup/sofascore_shots.csv'
df.to_csv(out, index=False)
print(f'\nTotal shots: {len(df)} across {df.match_id.nunique()} matches')
print('xG coverage:', f'{df.xg.notna().mean()*100:.0f}%')
print(f'-> {out}')
