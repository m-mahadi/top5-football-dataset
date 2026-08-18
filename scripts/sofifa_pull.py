"""SoFIFA (EA FC 26) full attribute pull for the top-5 leagues.

Grabs every column SoFIFA exposes - the closest free equivalent to a Football
Manager attribute profile: technical (finishing, passing, dribbling, crossing,
first-touch proxy), mental (composure, vision, aggression, work rates,
positioning proxies), physical (pace, acceleration, stamina, strength, jumping,
balance, agility), plus PlayStyles/traits, value, wage, release clause and
contract dates.

Transfermarkt blocks automated access behind human verification, so this is the
substitute for the money side. Ratings are EA's scouted estimates, not measured.
Output: data/clean/sofifa_players.csv
"""
import re
import sys
from pathlib import Path
import lxml.html
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get_text, pmap  # noqa: E402

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36'}
LEAGUES = {13: 'ENG-Premier League', 53: 'ESP-La Liga', 31: 'ITA-Serie A',
           19: 'GER-Bundesliga', 16: 'FRA-Ligue 1'}
# every column code SoFIFA offers (basic/attacking/skill/movement/power/
# mentality/defending/goalkeeping/special)
COLS = ('pi ae by hi wi pf oa pt bo bp gu jt le vl wg rc '
        'ta cr fi he sh vo '
        'ts dr cu fr lo bl '
        'to ac sp ag re ba '
        'tp so ju st sr ln '
        'te ar in po vi pe cm '
        'td ma sa sl '
        'tg gd gh gc gp gr '
        'tt bs wk sk aw dw ir bt pac sho pas dri def phy ps1 tc at cp').split()
SHOW = '&'.join('showCol%5B%5D=' + c for c in COLS)
POS_RE = r'(?:GK|CB|LB|RB|LWB|RWB|CDM|CM|CAM|LM|RM|LW|RW|CF|ST)'


def snake(s):
    s = re.sub(r'[^0-9a-zA-Z]+', '_', str(s)).strip('_').lower()
    return re.sub(r'_+', '_', s) or 'blank'


def money(s):
    m = re.search(r'([\d.]+)\s*([MK])?', str(s).replace(',', ''))
    if not m:
        return None
    return float(m.group(1)) * {'M': 1e6, 'K': 1e3}.get(m.group(2), 1)


PAGES = 12  # 12 x 60 = 720 slots, comfortably above any top-5 squad list


def page(job):
    lid, lname, offset = job
    t = get_text(f'https://sofifa.com/players?type=all&lg%5B%5D={lid}&{SHOW}'
                 f'&offset={offset}')
    if not t:
        return None
    doc = lxml.html.fromstring(t)
    heads = [snake(th.text_content()) for th in doc.xpath('//table//thead//th')]
    out = []
    for tr in doc.xpath('//table//tbody/tr'):
        cells = [td.text_content().strip() for td in tr.xpath('./td')]
        if len(cells) == len(heads):
            d = dict(zip(heads, cells))
            d['league'] = lname
            out.append(d)
    return out or None


jobs = [(lid, lname, o) for lid, lname in LEAGUES.items()
        for o in range(0, PAGES * 60, 60)]
print(f'fetching {len(jobs)} pages in parallel...', flush=True)
rows = pmap(page, jobs, workers=8, label='pages', every=10)
print(f'rows: {len(rows)}', flush=True)

df = pd.DataFrame(rows)

# --- name cell carries trailing position tags: "R. Lewandowski ST" ---
name_col = 'name' if 'name' in df.columns else df.columns[1]


def split_name(v):
    v = re.sub(r'\s+', ' ', str(v)).strip()
    m = re.search(rf'\s((?:{POS_RE})(?:\s+{POS_RE})*)$', v)
    return (v[:m.start()].strip(), m.group(1).strip()) if m else (v, '')


parsed = df[name_col].map(split_name)
df['player'] = [x[0] for x in parsed]
df['positions'] = [x[1] for x in parsed]

# --- "Team & Contract" cell: "Real Madrid 2024 ~ 2029" ---
tc = 'team_contract' if 'team_contract' in df.columns else None
if tc:
    yrs = df[tc].map(lambda s: re.findall(r'(20\d\d)', str(s)))
    df['team'] = df[tc].map(lambda s: re.sub(r'\s*20\d\d.*$', '', str(s)).strip())
    df['contract_start'] = [y[0] if y else None for y in yrs]
    df['contract_end'] = [y[1] if len(y) > 1 else None for y in yrs]

for src, dst in [('value', 'value_eur'), ('wage', 'wage_eur'),
                 ('release_clause', 'release_clause_eur')]:
    if src in df.columns:
        df[dst] = df[src].map(money)

df['surname_key'] = (df.player.str.normalize('NFKD').str.encode('ascii', 'ignore')
                     .str.decode('ascii').str.lower()
                     .str.replace(r'[^a-z ]', '', regex=True).str.split().str[-1])

# numeric-ify the attribute columns (they are plain integers 1-99)
SKIP = {'player', 'positions', 'team', 'league', 'name', 'team_contract', 'value',
        'wage', 'release_clause', 'surname_key', 'foot', 'preferred_foot',
        'best_position', 'club_position', 'body_type', 'joined',
        'loan_date_end', 'height', 'weight', 'playstyles',
        'attacking_work_rate', 'defensive_work_rate', 'acceleration_type'}
for c in df.columns:
    if c in SKIP:
        continue
    conv = pd.to_numeric(df[c], errors='coerce')
    # keep the conversion only if it did not destroy a mostly-text column
    if conv.notna().sum() >= df[c].replace('', pd.NA).notna().sum() * 0.8:
        df[c] = conv
for c in ('contract_start', 'contract_end'):
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce').astype('Int64')

df = df.drop_duplicates('id' if 'id' in df.columns else 'player')
df.to_csv('data/clean/sofifa_players.csv', index=False, encoding='utf-8')
print(f'\n{len(df)} players x {df.shape[1]} cols -> data/clean/sofifa_players.csv')
print('columns:', sorted(df.columns.tolist()))
