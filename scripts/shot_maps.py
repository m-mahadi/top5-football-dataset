"""Barcelona shot-taking + chance-creation spot maps (La Liga, both Flick seasons).
Understat coords: x,y in 0-1. Attacking right; we draw the attacking half.
Output: output/barca_shot_map.png, output/barca_creation_map.png
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

os.makedirs('output', exist_ok=True)
PITCH_L, PITCH_W = 105, 68
s = pd.read_csv('data/barcelona/understat_shots.csv')
b = s[s.team == 'Barcelona'].copy()
# to metres, attacking half only (x from 0.5..1 -> 0..52.5 of the shown half)
b['mx'] = b.location_x * PITCH_L
b['my'] = b.location_y * PITCH_W


def half_pitch(ax):
    ax.set_facecolor('#0b6b3a')
    # outer (right half of pitch: x 52.5..105)
    ax.plot([52.5, 105, 105, 52.5, 52.5], [0, 0, 68, 68, 0], color='white', lw=1.5)
    # penalty box
    ax.plot([105 - 16.5, 105, 105, 105 - 16.5, 105 - 16.5],
            [13.85, 13.85, 54.15, 54.15, 13.85], color='white', lw=1.2)
    # six-yard
    ax.plot([105 - 5.5, 105, 105, 105 - 5.5, 105 - 5.5],
            [24.85, 24.85, 43.15, 43.15, 24.85], color='white', lw=1.2)
    ax.plot([105, 105], [30.34, 37.66], color='white', lw=4)  # goal
    ax.set_xlim(50, 107); ax.set_ylim(-2, 70); ax.set_aspect('equal'); ax.axis('off')


# 1) shot-taking spots: colour goal vs not, size by xG
fig, ax = plt.subplots(figsize=(9, 7)); half_pitch(ax)
goals = b[b.result == 'Goal']; miss = b[b.result != 'Goal']
ax.scatter(miss.mx, miss.my, s=miss.xg * 300 + 8, c='#ffd24d', alpha=0.45,
           edgecolors='none', label=f'shot ({len(miss)})')
ax.scatter(goals.mx, goals.my, s=goals.xg * 300 + 12, c='#e8412f', alpha=0.9,
           edgecolors='white', lw=0.4, label=f'goal ({len(goals)})')
ax.set_title(f'Barcelona shot-taking spots · La Liga 24/25+25/26 · {len(b)} shots '
             f'({b.xg.sum():.0f} xG)', color='white', fontsize=12)
ax.legend(loc='lower left', framealpha=0.3, labelcolor='white')
fig.patch.set_facecolor('#0b6b3a')
fig.savefig('output/barca_shot_map.png', dpi=140, bbox_inches='tight')

# 2) chance-creation: assisted-shot end locations (where created chances landed)
fig, ax = plt.subplots(figsize=(9, 7)); half_pitch(ax)
a = b[b.assist_player.notna()]
sc = ax.scatter(a.mx, a.my, s=a.xg * 300 + 10, c=a.xg, cmap='viridis',
                alpha=0.75, edgecolors='none')
ax.set_title(f'Barcelona created-chance spots (assisted shots) · {len(a)} chances\n'
             f'colour/size = xG of the chance', color='white', fontsize=12)
fig.colorbar(sc, ax=ax, shrink=0.6, label='xG')
fig.patch.set_facecolor('#0b6b3a')
fig.savefig('output/barca_creation_map.png', dpi=140, bbox_inches='tight')
print('wrote output/barca_shot_map.png and output/barca_creation_map.png')
