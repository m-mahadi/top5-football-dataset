"""Re-pull team stats with the fixed parser, then fill mislabeled Bundesliga.

soccerdata's BIG_FIVE_DICT has a mojibake key for 'Fußball-Bundesliga', so Big-5
pulls leave Bundesliga rows with league=NaN. In these pulls the only unmapped
league is Bundesliga -> fill NaN with GER-Bundesliga.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from fbref_full import FBref, FULL_TYPES  # noqa: E402

SEASONS = ["2024-2025", "2025-2026"]
CACHE = Path("data/_cache")
big5 = FBref(leagues="Big 5 European Leagues Combined", seasons=SEASONS, data_dir=CACHE)
extra = FBref(leagues=["POR-Primeira Liga", "NED-Eredivisie"], seasons=SEASONS, data_dir=CACHE)

# 1. Re-pull teams (cached HTML -> just re-parses; advanced types now Big-5-only)
for st in FULL_TYPES:
    try:
        df = pd.concat([big5.read_team_season_stats(st), extra.read_team_season_stats(st)])
        df.to_csv(Path("data/teams") / f"{st}.csv")
        print(f"[team OK] {st}: {df.shape}", flush=True)
    except Exception as e:
        print(f"[team FAIL] {st}: {type(e).__name__}: {e}", flush=True)


# 2. Fill NaN league -> GER-Bundesliga in every CSV
def fill_bundesliga(path, n_index):
    df = pd.read_csv(path, header=[0, 1], index_col=list(range(n_index)))
    idx = df.index.to_frame()
    n_before = idx["league"].isna().sum()
    if n_before:
        idx["league"] = idx["league"].fillna("GER-Bundesliga")
        df.index = pd.MultiIndex.from_frame(idx)
        df.to_csv(path)
    print(f"[fill] {path.name}: {n_before} rows -> GER-Bundesliga", flush=True)


for p in Path("data/players").glob("*.csv"):
    fill_bundesliga(p, 4)  # league/season/team/player
for p in Path("data/teams").glob("*.csv"):
    fill_bundesliga(p, 3)  # league/season/team

print("DONE", flush=True)
