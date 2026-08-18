"""SoFIFA (EA FC) pull for the top-5 leagues: market value, wage, release
clause, CONTRACT EXPIRY, plus pace/physical/defensive attributes.

Transfermarkt blocks automated access behind human verification, so this is the
free substitute for the money side. Values are EA's model, not Transfermarkt
quotes; contract dates mirror real ones. Pace here is EA's scouted rating, the
only pace signal available free (matters for Flick's high line).
Output: data/clean/sofifa_players.csv
"""
import re
import time
import lxml.html
import pandas as pd
import tls_requests

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36'}
COLS = ['pi', 'ae', 'hi', 'wi', 'pf', 'oa', 'pt', 'bp', 'vl', 'wg', 'rc', 'jt',
        'le', 'pac', 'sho', 'pas', 'dri', 'def', 'phy', 'ac', 'sp', 'ju', 'sr',
        'he', 'ma', 'sa', 'sl', 'cp', 'ir']
LEAGUES = {13: 'ENG-Premier League', 53: 'ESP-La Liga', 31: 'ITA-Serie A',
           19: 'GER-Bundesliga', 16: 'FRA-Ligue 1'}
SHOW = '&'.join('showCol%5B%5D=' + c for c in COLS)


def money(s):
    m = re.search(r'([\d.]+)\s*([MK])?', str(s).replace(',', ''))
    if not m:
        return None
    v = float(m.group(1))
    return v * {'M': 1e6, 'K': 1e3}.get(m.group(2), 1)


rows = []
for lid, lname in LEAGUES.items():
    offset, got = 0, 0
    while True:
        u = f'https://sofifa.com/players?type=all&lg%5B%5D={lid}&{SHOW}&offset={offset}'
        try:
            r = tls_requests.get(u, headers=H, timeout=30)
        except Exception:
            time.sleep(3)
            continue
        if r.status_code != 200:
            break
        doc = lxml.html.fromstring(r.text)
        heads = [th.text_content().strip() for th in doc.xpath('//table//thead//th')]
        trs = doc.xpath('//table//tbody/tr')
        if not trs:
            break
        for tr in trs:
            cells = [td.text_content().strip() for td in tr.xpath('./td')]
            if len(cells) != len(heads):
                continue
            d = dict(zip(heads, cells))
            tc = d.get('Team & Contract', '')
            yrs = re.findall(r'(20\d\d)', tc)
            name_cell = d.get('Name', '')
            rows.append({
                'league': lname,
                'player': re.split(r'\s{2,}', name_cell)[0].strip(),
                'positions': ' '.join(re.split(r'\s{2,}', name_cell)[1:]).strip(),
                'age': pd.to_numeric(d.get('Age'), errors='coerce'),
                'overall': pd.to_numeric(d.get('Overall rating'), errors='coerce'),
                'potential': pd.to_numeric(d.get('Potential'), errors='coerce'),
                'team': re.sub(r'\s*20\d\d.*$', '', tc).strip(),
                'contract_start': yrs[0] if yrs else None,
                'contract_end': yrs[1] if len(yrs) > 1 else None,
                'sofifa_id': d.get('ID'),
                'value_eur': money(d.get('Value')),
                'wage_eur': money(d.get('Wage')),
                'release_clause_eur': money(d.get('Release clause')),
                'best_position': d.get('Best position'),
                'club_position': d.get('Club position'),
                'height': d.get('Height'), 'foot': d.get('foot'),
                'pace': pd.to_numeric(d.get('Pace / Diving'), errors='coerce'),
                'acceleration': pd.to_numeric(d.get('Acceleration'), errors='coerce'),
                'sprint_speed': pd.to_numeric(d.get('Sprint speed'), errors='coerce'),
                'jumping': pd.to_numeric(d.get('Jumping'), errors='coerce'),
                'strength': pd.to_numeric(d.get('Strength'), errors='coerce'),
                'heading': pd.to_numeric(d.get('Heading accuracy'), errors='coerce'),
                'def_awareness': pd.to_numeric(d.get('Defensive awareness'), errors='coerce'),
                'standing_tackle': pd.to_numeric(d.get('Standing tackle'), errors='coerce'),
                'sliding_tackle': pd.to_numeric(d.get('Sliding tackle'), errors='coerce'),
                'defending': pd.to_numeric(d.get('Defending / Pace'), errors='coerce'),
                'physical': pd.to_numeric(d.get('Physical / Positioning'), errors='coerce'),
                'shooting': pd.to_numeric(d.get('Shooting / Handling'), errors='coerce'),
                'passing': pd.to_numeric(d.get('Passing / Kicking'), errors='coerce'),
                'dribbling': pd.to_numeric(d.get('Dribbling / Reflexes'), errors='coerce'),
            })
        got += len(trs)
        offset += 60
        if len(trs) < 60 or offset > 1800:
            break
        time.sleep(0.25)
    print(f'  {lname}: {got}', flush=True)

df = pd.DataFrame(rows).drop_duplicates('sofifa_id')
df.to_csv('data/clean/sofifa_players.csv', index=False, encoding='utf-8')
print(f'\n{len(df)} players -> data/clean/sofifa_players.csv', flush=True)
print('with contract_end:', df.contract_end.notna().sum(), flush=True)
print('with value:', df.value_eur.notna().sum(), flush=True)
