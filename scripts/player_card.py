"""Print everything the project holds on one player, laid out like a Football
Manager profile. Usage: python scripts/player_card.py "Pedri"
"""
import sys
import pandas as pd

NAME = sys.argv[1] if len(sys.argv) > 1 else 'Pedri'
m = pd.read_csv('data/master/player_seasons.csv', low_memory=False)
m['season'] = m.season.astype(str)
rows = m[m.player.str.contains(NAME, case=False, na=False)]
if rows.empty:
    print(f'no player matching "{NAME}"')
    sys.exit()
rows = rows.sort_values('season')
r = rows.iloc[-1]
W = 92


def line(c='-'):
    print(c * W)


def block(title, pairs, cols=3):
    print(f'\n{title}')
    items = [(k, v) for k, v in pairs if pd.notna(v) and str(v) not in ('', 'nan')]
    for i in range(0, len(items), cols):
        chunk = items[i:i + cols]
        print('  ' + ''.join(f'{k:<22}{str(v):<9}' for k, v in chunk))


def g(col, dp=0):
    v = r.get(col)
    if pd.isna(v):
        return None
    return round(float(v), dp) if isinstance(v, (int, float)) and dp else (
        int(v) if isinstance(v, float) and v == int(v) else v)


line('=')
val = f"EUR {r.fifa_value_eur/1e6:.0f}M" if pd.notna(r.get('fifa_value_eur')) else '-'
rel = f"EUR {r.fifa_release_clause_eur/1e6:.0f}M" if pd.notna(r.get('fifa_release_clause_eur')) else '-'
print(f"{r.player}   |   {r.team}   |   {r.league}")
print(f"{r.pos}  ({r.get('fifa_best_position','?')} best)   age {r.age:.0f}   "
      f"{r.get('fifa_height','?')}  {r.get('fifa_foot','?')} footed")
print(f"value {val}   release clause {rel}   contract "
      f"{r.get('fifa_contract_start','?')}-{r.get('fifa_contract_end','?')}   "
      f"OVR {g('fifa_overall_rating')} / POT {g('fifa_potential')}")
if pd.notna(r.get('fifa_playstyles')):
    print(f"PlayStyles: {r.fifa_playstyles}")
line('=')

# ---------------- attributes (SoFIFA / EA FC) ----------------
print('\nATTRIBUTES  (SoFIFA / EA FC 26 - scouted ratings, not measured)')
TECH = [('Crossing', 'fifa_crossing'), ('Finishing', 'fifa_finishing'),
        ('Heading', 'fifa_heading_accuracy'), ('Short passing', 'fifa_short_passing'),
        ('Volleys', 'fifa_volleys'), ('Dribbling', 'fifa_dribbling'),
        ('Curve', 'fifa_curve'), ('FK accuracy', 'fifa_fk_accuracy'),
        ('Long passing', 'fifa_long_passing'), ('Ball control', 'fifa_ball_control'),
        ('Shot power', 'fifa_shot_power'), ('Long shots', 'fifa_long_shots'),
        ('Standing tackle', 'fifa_standing_tackle'), ('Sliding tackle', 'fifa_sliding_tackle'),
        ('Penalties', 'fifa_penalties')]
MENT = [('Aggression', 'fifa_aggression'), ('Interceptions', 'fifa_interceptions'),
        ('Att. positioning', 'fifa_attack_position'), ('Vision', 'fifa_vision'),
        ('Composure', 'fifa_composure'), ('Def. awareness', 'fifa_defensive_awareness'),
        ('Reactions', 'fifa_reactions')]
# NOTE: SoFIFA's list view returns attacking/defensive work rate EMPTY, so they
# are not shown. PlayStyles ("Relentless") partly cover the same ground, and the
# PRESS metric in the shortlists comes from real match data, not these ratings.
PHYS = [('Acceleration', 'fifa_acceleration'), ('Sprint speed', 'fifa_sprint_speed'),
        ('Pace', 'fifa_pace'), ('Agility', 'fifa_agility'), ('Balance', 'fifa_balance'),
        ('Jumping', 'fifa_jumping'), ('Stamina', 'fifa_stamina'),
        ('Strength', 'fifa_strength'), ('Weight', 'fifa_weight')]
for title, spec in [('TECHNICAL', TECH), ('MENTAL', MENT), ('PHYSICAL', PHYS)]:
    block(title, [(k, g(c)) for k, c in spec])
block('SPECIAL', [('Weak foot', g('fifa_weak_foot')), ('Skill moves', g('fifa_skill_moves')),
                  ('Int. reputation', g('fifa_international_reputation')),
                  ('Total stats', g('fifa_total_stats')), ('Growth', g('fifa_growth'))])

# ---------------- real match output ----------------
line()
print('\nMATCH OUTPUT  (FBref + Understat + SofaScore, actual matches played)')
print(f"  {'season':9}{'90s':>6}{'Gls':>5}{'Ast':>5}{'xG':>7}{'npxG':>7}{'xA':>7}"
      f"{'xGChain':>9}{'KeyP':>6}{'Shots':>6}")
for _, s in rows.iterrows():
    def n(c, dp=2):
        v = s.get(c)
        return f'{v:.{dp}f}' if pd.notna(v) else '-'
    print(f"  {s.season_label:9}{s.nineties:>6.1f}{s.get('fb_gls',0):>5.0f}"
          f"{s.get('fb_ast',0):>5.0f}{n('us_xg'):>7}{n('us_np_xg'):>7}{n('us_xa'):>7}"
          f"{n('us_xg_chain'):>9}{s.get('ss_keyPasses',0):>6.0f}"
          f"{s.get('us_shots',0):>6.0f}")

print('\nON-BALL / PASSING  (SofaScore, latest season)')
block('', [('Touches', g('ss_touches')), ('Passes', g('ss_totalPasses')),
           ('Pass acc %', g('ss_accuratePassesPercentage', 1)),
           ('Own-half passes', g('ss_accurateOwnHalfPasses')),
           ('Opp-half passes', g('ss_accurateOppositionHalfPasses')),
           ('Final-third passes', g('ss_accurateFinalThirdPasses')),
           ('Long balls', g('ss_accurateLongBalls')),
           ('Big chances created', g('ss_bigChancesCreated')),
           ('Dribbles', g('ss_successfulDribbles')),
           ('Dispossessed', g('ss_dispossessed')),
           ('Possession lost', g('ss_possessionLost'))])

print('\nDEFENSIVE / PRESSING  (SofaScore, latest season)')
block('', [('Poss. won att 3rd', g('ss_possessionWonAttThird')),
           ('Ball recoveries', g('ss_ballRecovery')),
           ('Tackles', g('ss_tackles')), ('Tackles won', g('ss_tacklesWon')),
           ('Interceptions', g('ss_interceptions')),
           ('Clearances', g('ss_clearances')),
           ('Blocked shots', g('ss_blockedShots')),
           ('Aerials won', g('ss_aerialDuelsWon')),
           ('Aerial win %', g('ss_aerialDuelsWonPercentage', 1)),
           ('Ground duel %', g('ss_groundDuelsWonPercentage', 1)),
           ('Was fouled', g('ss_wasFouled')), ('Fouls', g('ss_fouls')),
           ('Dribbled past', g('ss_dribbledPast')),
           ('Error -> shot', g('ss_errorLeadToShot')),
           ('Error -> goal', g('ss_errorLeadToGoal'))])
line('=')
print(f"columns held for this player: {rows.notna().any().sum()} of {m.shape[1]}")
