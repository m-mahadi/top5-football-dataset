"""All Barcelona Champions League shots, both campaigns (24/25 + 25/26), from
SofaScore's free shotmap API. Gives shot-taking spots + per-shot xG for the
European nights Understat/FBref can't cover.
Output: data/barcelona/sofascore_ucl_shots.csv
"""
import time
import datetime as dt
import pandas as pd
import tls_requests

TEAM = 2817  # FC Barcelona
# league phase = "UEFA Champions League"; knockouts add ", Knockout Phase/stage"
COMP_PREFIX = 'UEFA Champions League'
BASE = 'https://api.sofascore.com/api/v1'


def season_tag(ts):
    d = dt.datetime.utcfromtimestamp(ts)
    yr = d.year if d.month >= 8 else d.year - 1
    return f'{str(yr)[2:]}{str(yr + 1)[2:]}'  # e.g. 2425


# 1) collect all finished UCL matches by paging back through team events
matches = {}
for page in range(0, 16):
    r = tls_requests.get(f'{BASE}/team/{TEAM}/events/last/{page}', timeout=25)
    if r.status_code != 200:
        continue
    evs = r.json().get('events', [])
    if not evs:
        break
    for e in evs:
        if not e.get('tournament', {}).get('name', '').startswith(COMP_PREFIX):
            continue
        if e.get('status', {}).get('type') != 'finished':
            continue
        ts = e.get('startTimestamp', 0)
        tag = season_tag(ts)
        if tag not in ('2425', '2526'):
            continue
        matches[e['id']] = e
    time.sleep(0.2)

print(f'UCL finished matches found (both campaigns): {len(matches)}')

# 2) pull each shotmap, flatten to rows (shots for AND against)
rows = []
for eid, e in sorted(matches.items(), key=lambda kv: kv[1]['startTimestamp']):
    home, away = e['homeTeam']['name'], e['awayTeam']['name']
    date = dt.datetime.utcfromtimestamp(e['startTimestamp']).strftime('%Y-%m-%d')
    tag = season_tag(e['startTimestamp'])
    stage = 'knockout' if 'Knockout' in e.get('tournament', {}).get('name', '') else 'league_phase'
    rnd = (e.get('roundInfo', {}) or {}).get('name') or ''
    j = tls_requests.get(f'{BASE}/event/{eid}/shotmap', timeout=25).json()
    sm = j.get('shotmap', [])
    for s in sm:
        pc = s.get('playerCoordinates', {}) or {}
        rows.append({
            'season': tag, 'date': date, 'match_id': eid,
            'stage': stage, 'round': rnd,
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
    print(f'  {date} {tag} {home} v {away}: {len(sm)} shots')
    time.sleep(0.2)

df = pd.DataFrame(rows)
out = 'data/barcelona/sofascore_ucl_shots.csv'
df.to_csv(out, index=False)
barca = df[df.team.str.contains('Barcelona', case=False, na=False)]
print(f'\nTotal shots: {len(df)} ({len(barca)} by Barca) across {df.match_id.nunique()} matches')
print('per season:', df.groupby('season').match_id.nunique().to_dict(), 'matches')
print('xG coverage:', f'{df.xg.notna().mean()*100:.0f}% of shots have xg')
print(f'-> {out}')
