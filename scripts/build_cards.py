"""Build the human-facing layer on top of the flat dataset.

Produces data/master/players.json: one nested object per player with identity,
EA attributes, real match output per season, on-ball/defensive detail, and
PERCENTILE RANKS within position group (what makes a card readable at a glance).
The flat CSV stays the machine/ML surface; this is the presentation surface.
"""
import json
import math
import os

import numpy as np
import pandas as pd

m = pd.read_csv('data/master/player_seasons.csv', low_memory=False)
m['season'] = m.season.astype(str)
n = m.season_nineties.replace(0, np.nan)

# ---- derived per-90s used for percentile ranks ----
D = {
    'npxg_p90': m.us_np_xg / n,
    'xa_p90': m.us_xa / n,
    'xgchain_p90': m.us_xg_chain / n,
    'shots_p90': m.us_shots / n,
    'key_passes_p90': m.ss_keyPasses / n,
    'press_att3rd_p90': m.ss_possessionWonAttThird / n,
    'recoveries_p90': m.ss_ballRecovery / n,
    'tackles_p90': m.ss_tackles / n,
    'interceptions_p90': m.ss_interceptions / n,
    'clearances_p90': m.ss_clearances / n,
    'dribbles_p90': m.ss_successfulDribbles / n,
    'fouled_p90': m.ss_wasFouled / n,
    'touches_p90': m.ss_touches / n,
    'final_third_passes_p90': m.ss_accurateFinalThirdPasses / n,
    'opp_half_passes_p90': m.ss_accurateOppositionHalfPasses / n,
    'pass_acc': m.ss_accuratePassesPercentage,
    'aerial_pct': m.ss_aerialDuelsWonPercentage,
    'ground_duel_pct': m.ss_groundDuelsWonPercentage,
}
for k, v in D.items():
    m[k] = v


def group(pos):
    p = str(pos)
    if 'GK' in p:
        return 'GK'
    if 'DF' in p:
        return 'DF'
    if 'MF' in p:
        return 'MF'
    return 'FW'


m['pos_group'] = m.pos.map(group)

# percentiles among players with a real sample, within position group
PCT = list(D)
elig = m.season_nineties >= 8
for c in PCT:
    m['pct_' + c] = np.nan
    for gname, idx in m[elig].groupby('pos_group').groups.items():
        m.loc[idx, 'pct_' + c] = m.loc[idx, c].rank(pct=True) * 100

ATTR = {
    'technical': {
        'crossing': 'fifa_crossing', 'finishing': 'fifa_finishing',
        'heading': 'fifa_heading_accuracy', 'short_passing': 'fifa_short_passing',
        'volleys': 'fifa_volleys', 'dribbling': 'fifa_dribbling',
        'curve': 'fifa_curve', 'fk_accuracy': 'fifa_fk_accuracy',
        'long_passing': 'fifa_long_passing', 'ball_control': 'fifa_ball_control',
        'shot_power': 'fifa_shot_power', 'long_shots': 'fifa_long_shots',
        'standing_tackle': 'fifa_standing_tackle',
        'sliding_tackle': 'fifa_sliding_tackle', 'penalties': 'fifa_penalties',
    },
    'mental': {
        'aggression': 'fifa_aggression', 'interceptions': 'fifa_interceptions',
        'att_positioning': 'fifa_attack_position', 'vision': 'fifa_vision',
        'composure': 'fifa_composure', 'def_awareness': 'fifa_defensive_awareness',
        'reactions': 'fifa_reactions',
    },
    'physical': {
        'acceleration': 'fifa_acceleration', 'sprint_speed': 'fifa_sprint_speed',
        'pace': 'fifa_pace', 'agility': 'fifa_agility', 'balance': 'fifa_balance',
        'jumping': 'fifa_jumping', 'stamina': 'fifa_stamina',
        'strength': 'fifa_strength',
    },
}
ONBALL = {
    'touches': 'ss_touches', 'passes': 'ss_totalPasses',
    'pass_accuracy': 'ss_accuratePassesPercentage',
    'own_half_passes': 'ss_accurateOwnHalfPasses',
    'opp_half_passes': 'ss_accurateOppositionHalfPasses',
    'final_third_passes': 'ss_accurateFinalThirdPasses',
    'long_balls': 'ss_accurateLongBalls', 'key_passes': 'ss_keyPasses',
    'big_chances_created': 'ss_bigChancesCreated',
    'dribbles': 'ss_successfulDribbles', 'dispossessed': 'ss_dispossessed',
}
DEF = {
    'press_won_att_third': 'ss_possessionWonAttThird',
    'ball_recoveries': 'ss_ballRecovery', 'tackles': 'ss_tackles',
    'tackles_won': 'ss_tacklesWon', 'interceptions': 'ss_interceptions',
    'clearances': 'ss_clearances', 'blocked_shots': 'ss_blockedShots',
    'aerials_won': 'ss_aerialDuelsWon', 'aerial_pct': 'ss_aerialDuelsWonPercentage',
    'ground_duel_pct': 'ss_groundDuelsWonPercentage', 'was_fouled': 'ss_wasFouled',
    'fouls': 'ss_fouls', 'dribbled_past': 'ss_dribbledPast',
    'error_to_shot': 'ss_errorLeadToShot', 'error_to_goal': 'ss_errorLeadToGoal',
}


def clean(v, dp=None):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return round(float(v), 2 if dp is None else dp)
    return str(v)


def pack(spec, row, dp=None):
    out = {}
    for k, col in spec.items():
        val = clean(row.get(col), dp)
        if val is not None:
            out[k] = val
    return out


cards = []
for player, rows in m.groupby('player'):
    rows = rows.sort_values('season')
    last = rows.iloc[-1]
    seasons = []
    for _, r in rows.iterrows():
        seasons.append({
            'season': clean(r.season_label), 'team': clean(r.team),
            'league': clean(r.league), 'nineties': clean(r.nineties, 1),
            'goals': clean(r.get('fb_gls'), 0), 'assists': clean(r.get('fb_ast'), 0),
            'xg': clean(r.us_xg), 'npxg': clean(r.us_np_xg), 'xa': clean(r.us_xa),
            'xg_chain': clean(r.us_xg_chain), 'shots': clean(r.us_shots, 0),
            'on_ball': pack(ONBALL, r, 1), 'defensive': pack(DEF, r, 1),
        })
    pcts = {}
    for c in PCT:
        v = clean(last.get('pct_' + c), 0)
        if v is not None:
            pcts[c] = v
    cards.append({
        'player': player,
        'team': clean(last.team), 'league': clean(last.league),
        'position': clean(last.pos), 'pos_group': clean(last.pos_group),
        'identity': {
            'age': clean(last.age, 0), 'nation': clean(last.get('nation')),
            'height': clean(last.get('fifa_height')),
            'foot': clean(last.get('fifa_foot')),
            'best_position': clean(last.get('fifa_best_position')),
            'overall': clean(last.get('fifa_overall_rating'), 0),
            'potential': clean(last.get('fifa_potential'), 0),
            'value_eur': clean(last.get('fifa_value_eur'), 0),
            'release_clause_eur': clean(last.get('fifa_release_clause_eur'), 0),
            'wage_eur': clean(last.get('fifa_wage_eur'), 0),
            'contract_start': clean(last.get('fifa_contract_start'), 0),
            'contract_end': clean(last.get('fifa_contract_end'), 0),
            'playstyles': clean(last.get('fifa_playstyles')),
        },
        'attributes': {k: pack(v, last, 0) for k, v in ATTR.items()},
        'seasons': seasons,
        'percentiles': pcts,
    })

cards.sort(key=lambda c: -(c['identity'].get('overall') or 0))
with open('data/master/players.json', 'w', encoding='utf-8') as f:
    json.dump(cards, f, ensure_ascii=False, separators=(',', ':'))

size = os.path.getsize('data/master/players.json') / 1e6
print(str(len(cards)) + ' player cards -> data/master/players.json (%.1f MB)' % size)
print('card keys:', list(cards[0]))
print('percentile metrics:', len(PCT))
