"""Pull ALL FBref season stats for the 2026 World Cup (every stat type,
players + teams + schedule). Mirrors scripts/pull.py but for INT-World Cup.
Output: data/worldcup/{players,teams}/<stat>.csv, data/worldcup/schedule.csv
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from fbref_full import FBref, FULL_TYPES  # noqa: E402

CACHE = Path("data/_cache")
wc = FBref(leagues="INT-World Cup", seasons="2026", data_dir=CACHE)


def pull(kind, method):
    outdir = Path(f"data/worldcup/{kind}")
    outdir.mkdir(parents=True, exist_ok=True)
    for st in FULL_TYPES:
        try:
            df = getattr(wc, method)(st)
            df.to_csv(outdir / f"{st}.csv")
            print(f"[OK] {kind}/{st}: {df.shape}", flush=True)
        except Exception as e:
            print(f"[FAIL] {kind}/{st}: {type(e).__name__}: {e}", flush=True)


pull("players", "read_player_season_stats")
pull("teams", "read_team_season_stats")

try:
    sch = wc.read_schedule()
    Path("data/worldcup").mkdir(parents=True, exist_ok=True)
    sch.to_csv("data/worldcup/schedule.csv")
    print(f"[OK] schedule: {sch.shape}", flush=True)
except Exception as e:
    print(f"[FAIL] schedule: {type(e).__name__}: {e}", flush=True)

print("DONE", flush=True)
