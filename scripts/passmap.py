"""Barcelona average passing-network map (La Liga, both Flick seasons).
Nodes = each regular player's mean pitch position, sized by touches/match.
SofaScore gives node positions + touch counts, not pass edges, so this is the
positional network (no pass lines). Attacking left -> right.
Output: output/barca_avg_passmap.png
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

os.makedirs('output', exist_ok=True)
L, W = 105, 68
d = pd.read_csv('data/barcelona/sofascore_passing_network.csv')
d = d[d.competition == 'LaLiga'].copy()

g = d.groupby('player').agg(x=('avg_x', 'mean'), y=('avg_y', 'mean'),
                            touches=('touches', 'mean'), apps=('match_id', 'nunique')).reset_index()
g = g[g.apps >= 15].sort_values('touches', ascending=False).head(14)  # core XI + rotation
# SofaScore coords are 0-100; scale to pitch metres
g['px'] = g.x / 100 * L
g['py'] = g.y / 100 * W


def pitch(ax):
    ax.set_facecolor('#0b6b3a')
    ax.plot([0, L, L, 0, 0], [0, 0, W, W, 0], color='white', lw=1.5)
    ax.plot([L / 2, L / 2], [0, W], color='white', lw=1.2)
    c = plt.Circle((L / 2, W / 2), 9.15, color='white', fill=False, lw=1.2); ax.add_patch(c)
    for x0, sgn in [(0, 1), (L, -1)]:
        ax.plot([x0, x0 + sgn * 16.5, x0 + sgn * 16.5, x0],
                [13.85, 13.85, 54.15, 54.15], color='white', lw=1.1)
    ax.set_xlim(-3, L + 3); ax.set_ylim(-3, W + 3); ax.set_aspect('equal'); ax.axis('off')


fig, ax = plt.subplots(figsize=(12, 8)); pitch(ax)
# faint proximity lines between nearby regulars to suggest network shape
import itertools
core = g.head(11)
for (i, a), (j, b) in itertools.combinations(core.iterrows(), 2):
    dist = ((a.px - b.px) ** 2 + (a.py - b.py) ** 2) ** 0.5
    if dist < 28:
        ax.plot([a.px, b.px], [a.py, b.py], color='white', alpha=0.12, lw=1)

ax.scatter(g.px, g.py, s=g.touches * 6, c='#a50044', alpha=0.9,
           edgecolors='#ffcb05', lw=1.5, zorder=3)
for _, r in g.iterrows():
    surname = r.player.split()[-1]
    ax.text(r.px, r.py - 2.6, surname, color='white', ha='center', va='top',
            fontsize=8.5, zorder=4, fontweight='bold')

ax.set_title('Barcelona · average passing-network positions · La Liga 24/25 + 25/26\n'
             'node = mean position (attacking →), size = touches per match · '
             '(SofaScore: node layout, no pass edges)',
             color='white', fontsize=12)
ax.text(1, -2.5, 'own goal', color='white', alpha=0.5, fontsize=7)
ax.text(L - 1, -2.5, 'attack', color='white', alpha=0.5, fontsize=7, ha='right')
fig.patch.set_facecolor('#0b6b3a')
fig.savefig('output/barca_avg_passmap.png', dpi=145, bbox_inches='tight')
print('players shown:', len(g))
print(g[['player', 'apps', 'touches']].round(1).to_string(index=False))
print('-> output/barca_avg_passmap.png')
