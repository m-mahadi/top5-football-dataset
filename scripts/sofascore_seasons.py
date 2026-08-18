"""Backfill the columns FBref no longer serves, from SofaScore's per-player
season endpoint (111 fields: aerials, clearances, duels, tackles, errors,
own-half vs opposition-half passing).

Resumable: caches the full roster and skips player-seasons already in the
output CSV, so a dropped connection costs nothing.
Output: data/clean/sofascore_player_seasons.csv
"""
import json
import sys
import time
from pathlib import Path
import pandas as pd
import tls_requests

sys.path.insert(0, str(Path(__file__).parent))
from fetch import pmap  # noqa: E402

B = 'https://api.sofascore.com/api/v1'
TOURN = {'ENG-Premier League': 17, 'ESP-La Liga': 8, 'ITA-Serie A': 23,
         'GER-Bundesliga': 35, 'FRA-Ligue 1': 34}
WANT = {'24/25': '2425', '25/26': '2526'}
OUT = Path('data/clean/sofascore_player_seasons.csv')
ROSTER = Path('data/_cache/sofa_roster.json')
ROSTER.parent.mkdir(parents=True, exist_ok=True)


def get(url, tries=4):
    for i in range(tries):
        try:
            r = tls_requests.get(url, timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None


# --- 1. roster (cached, with full metadata so resume needs no re-enumeration) ---
if ROSTER.exists():
    roster = json.loads(ROSTER.read_text(encoding='utf-8'))
    print(f'roster loaded from cache: {len(roster)}', flush=True)
else:
    targets = []
    for lg, tid in TOURN.items():
        js = get(f'{B}/unique-tournament/{tid}/seasons') or {}
        for s in js.get('seasons', []):
            for label, tag in WANT.items():
                if label in s.get('name', ''):
                    targets.append((lg, tid, s['id'], tag))
    print('season targets:', len(targets), flush=True)

    seen, roster = set(), []
    for lg, tid, sid, tag in targets:
        offset, n = 0, 0
        while True:
            js = get(f'{B}/unique-tournament/{tid}/season/{sid}/statistics'
                     f'?limit=100&offset={offset}&order=-rating'
                     f'&accumulation=total&group=summary')
            res = (js or {}).get('results', [])
            if not res:
                break
            for r in res:
                p, t = r.get('player') or {}, r.get('team') or {}
                k = (p.get('id'), tag)
                if p.get('id') and k not in seen:
                    seen.add(k)
                    roster.append({
                        'league': lg, 'season': tag, 'tourn_id': tid,
                        'season_id': sid, 'player_id': p['id'],
                        'player': p.get('name'),
                        'team': (t.get('name') or '').replace('FC ', '').strip(),
                        'position': p.get('position'),
                    })
            n += len(res)
            offset += 100
            if len(res) < 100 or offset > 1200:
                break
            time.sleep(0.15)
        print(f'  {lg} {tag}: {n}', flush=True)
    ROSTER.write_text(json.dumps(roster), encoding='utf-8')
    print('roster cached:', len(roster), flush=True)

# --- 2. resume: skip what the output already has ---
rows, have = [], set()
if OUT.exists():
    prev = pd.read_csv(OUT)
    rows = prev.to_dict('records')
    have = set(zip(prev.player_id, prev.season.astype(str)))
    print(f'resuming: {len(have)} already fetched', flush=True)

todo = [m for m in roster if (m['player_id'], str(m['season'])) not in have]
print(f'to fetch: {len(todo)}', flush=True)

# --- 3. per-player season stats (parallel) ---
def one(meta):
    js = get(f"{B}/player/{meta['player_id']}/unique-tournament/{meta['tourn_id']}"
             f"/season/{meta['season_id']}/statistics/overall")
    st = (js or {}).get('statistics') or {}
    if not st:
        return None
    return {**meta, **{k: v for k, v in st.items()
                       if not isinstance(v, (dict, list))}}


def checkpoint(partial):
    pd.DataFrame(rows + partial).to_csv(OUT, index=False, encoding='utf-8')


fresh = pmap(one, todo, workers=8, label='players', every=200, on_batch=checkpoint)
df = pd.DataFrame(rows + fresh)
df.to_csv(OUT, index=False, encoding='utf-8')
print(f'{len(df)} player-seasons, {df.shape[1]} columns -> {OUT}', flush=True)
key = [c for c in ('aerialDuelsWon', 'clearances', 'interceptions',
                   'accurateOwnHalfPasses', 'errorLeadToShot', 'tacklesWon')
       if c in df.columns]
print('key CB fields present:', key, flush=True)
