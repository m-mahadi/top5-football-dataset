"""Barcelona all-competitions match logs (La Liga + UCL + Copa + Supercopa),
both Flick seasons, from FBref's squad match-log page. soccerdata can't parse
cup comps, but this single page per season carries every match.
Output: data/barcelona/fbref_allcomps_<season>.csv
"""
import io
import re
import pandas as pd
import soccerdata as sd

SQUAD = '206d90db'  # Barcelona on FBref
SEASONS = {'2425': '2024-2025', '2526': '2025-2026'}
fb = sd.FBref(leagues='ESP-La Liga', seasons='2425')  # any valid; we use its fetcher

for tag, sl in SEASONS.items():
    url = f'https://fbref.com/en/squads/{SQUAD}/{sl}/matchlogs/all_comps/schedule/'
    raw = fb.get(url).read()
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', 'ignore')
    # FBref hides the table in an HTML comment; unwrap it
    html = raw.replace('<!--', '').replace('-->', '')
    tables = pd.read_html(io.StringIO(html))
    # the match log has a 'Comp' and 'Opponent' column
    ml = None
    for t in tables:
        cols = [str(c) for c in t.columns]
        if any(c == 'Comp' for c in cols) and any(c == 'Opponent' for c in cols):
            ml = t
            break
    if ml is None:
        print(f'{tag}: match-log table not found ({len(tables)} tables)')
        continue
    ml = ml[ml['Date'].notna() & (ml['Date'] != 'Date')]  # drop spacer/repeat-header rows
    out = f'data/barcelona/fbref_allcomps_{tag}.csv'
    ml.to_csv(out, index=False)
    comps = ', '.join(f'{k}:{v}' for k, v in ml['Comp'].value_counts().items())
    print(f'{tag}: {len(ml)} matches -> {out}  [{comps}]')
