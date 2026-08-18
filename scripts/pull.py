"""Pull ALL FBref season stats for the top-7 leagues, 24/25 + 25/26.

Big-5 via the combined endpoint (one fetch covers 5 leagues), Portugal +
Netherlands together. One CSV per stat type, each holding all 7 leagues x both
seasons. Every fetch is independent -> failures are logged, not fatal.
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
READERS = [big5, extra]


def pull(kind, method):
    outdir = Path(f"data/{kind}")
    outdir.mkdir(parents=True, exist_ok=True)
    for st in FULL_TYPES:
        try:
            df = pd.concat([getattr(r, method)(st) for r in READERS])
            df.to_csv(outdir / f"{st}.csv")
            print(f"[OK] {kind}/{st}: {df.shape}", flush=True)
        except Exception as e:
            print(f"[FAIL] {kind}/{st}: {type(e).__name__}: {e}", flush=True)


pull("players", "read_player_season_stats")
pull("teams", "read_team_season_stats")

try:
    sch = pd.concat([r.read_schedule() for r in READERS])
    Path("data/schedule").mkdir(parents=True, exist_ok=True)
    sch.to_csv("data/schedule/matches.csv")
    print(f"[OK] schedule: {sch.shape}", flush=True)
except Exception as e:
    print(f"[FAIL] schedule: {type(e).__name__}: {e}", flush=True)

print("DONE", flush=True)
