import soccerdata as sd
sf = sd.SoFIFA(leagues='ESP-La Liga', versions='latest')
p = sf.read_players()
print('players:', p.shape, flush=True)
print('player cols:', list(p.columns), flush=True)
print(p.head(3).to_string()[:600], flush=True)
r = sf.read_player_ratings(player=list(p.index.get_level_values(-1)[:5]))
print('\nratings:', r.shape, flush=True)
print('rating cols:', list(r.columns)[:40], flush=True)
