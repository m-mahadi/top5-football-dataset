"""FBref subclass that unlocks every season stat page.

soccerdata 1.9.1 hardcodes read_{player,team}_season_stats to 5 stat types, but
the fetch+parse is generic (URL/table id derive from stat_type). We copy the two
methods verbatim and change exactly two things:
  1. widen the allowed stat_type list to FBref's full set
  2. map keeper_adv -> page "keepersadv" (its only nonstandard page slug)
ponytail: verbatim copy so upstream parse fixes still apply on version bump; if
soccerdata adds these types natively, delete this file and use sd.FBref directly.
"""
from lxml import html, etree
import pandas as pd
import soccerdata as sd
from soccerdata.fbref import (
    FBREF_API, BIG_FIVE_DICT, TEAMNAME_REPLACEMENTS,
    _parse_table, _concat, _fix_nation_col, standardize_colnames,
)

FULL_TYPES = [
    "standard", "shooting", "passing", "passing_types", "gca",
    "defense", "possession", "playing_time", "misc", "keeper", "keeper_adv",
]


def _page_for(stat_type):
    return {
        "standard": "stats",
        "playing_time": "playingtime",
        "keeper": "keepers",
        "keeper_adv": "keepersadv",
    }.get(stat_type, stat_type)


def _read_player_season_stats(self, stat_type="standard"):
        if stat_type not in FULL_TYPES:
            raise TypeError(f"Invalid argument: stat_type should be in {FULL_TYPES}")
        page = _page_for(stat_type)
        seasons = self.read_seasons()
        players = []
        for (lkey, skey), season in seasons.iterrows():
            big_five = lkey == "Big 5 European Leagues Combined"
            filepath = self.data_dir / f"players_{lkey}_{skey}_{stat_type}.html"
            url = (
                FBREF_API
                + "/".join(season.url.split("/")[:-1])
                + f"/{page}"
                + ("/players/" if big_five else "/")
                + season.url.split("/")[-1]
            )
            reader = self.get(url, filepath)
            tree = html.parse(reader)
            for elem in tree.xpath("//td[@data-stat='comp_level']//span"):
                elem.getparent().remove(elem)
            if big_five:
                (html_table,) = tree.xpath(f"//table[@id='stats_{stat_type}']")
                df_table = _parse_table(html_table)
                df_table[("Unnamed: league", "league")] = (
                    df_table.xs("Comp", axis=1, level=1).squeeze().map(BIG_FIVE_DICT)
                )
                df_table[("Unnamed: season", "season")] = skey
                df_table.drop("Comp", axis=1, level=1, inplace=True)
            else:
                (el,) = tree.xpath(f"//comment()[contains(.,'div_stats_{stat_type}')]")
                parser = etree.HTMLParser(recover=True)
                (html_table,) = etree.fromstring(el.text, parser).xpath(
                    f"//table[contains(@id, 'stats_{stat_type}')]"
                )
                df_table = _parse_table(html_table)
                df_table[("Unnamed: league", "league")] = lkey
                df_table[("Unnamed: season", "season")] = skey
            df_table = _fix_nation_col(df_table)
            players.append(df_table)
        df = _concat(players, key=["league", "season"])
        df = df[df.Player != "Player"]
        return (
            df.drop("Matches", axis=1, level=0)
            .drop("Rk", axis=1, level=0)
            .rename(columns={"Squad": "team"})
            .replace({"team": TEAMNAME_REPLACEMENTS})
            .pipe(standardize_colnames, cols=["Player", "Nation", "Pos", "Age", "Born"])
            .set_index(["league", "season", "team", "player"])
            .sort_index()
        )

def _read_team_season_stats(self, stat_type="standard", opponent_stats=False):
        if stat_type not in FULL_TYPES:
            raise ValueError(f"Invalid argument: stat_type should be in {FULL_TYPES}")
        page = _page_for(stat_type)
        stat_type = stat_type + ("_against" if opponent_stats else "_for")
        seasons = self.read_seasons()
        teams = []
        for (lkey, skey), season in seasons.iterrows():
            big_five = lkey == "Big 5 European Leagues Combined"
            tournament = season["format"] == "elimination"
            filepath = self.data_dir / f"teams_{lkey}_{skey}_{stat_type if big_five else page}.html"
            url = (
                FBREF_API
                + "/".join(season.url.split("/")[:-1])
                + (f"/{page}/squads/" if big_five else f"/{page}/" if tournament else "/")
                + season.url.split("/")[-1]
            )
            reader = self.get(url, filepath)
            tree = html.parse(reader)
            xp = f"//table[@id='stats_teams_{stat_type}' or @id='stats_squads_{stat_type}']"
            tables = tree.xpath(xp)
            if not tables:
                # Big-5 combined pages hide advanced tables inside HTML comments.
                comments = tree.xpath(f"//comment()[contains(.,'stats_squads_{stat_type}')]")
                if comments:
                    parser = etree.HTMLParser(recover=True)
                    tables = etree.fromstring(comments[0].text, parser).xpath(xp)
            if not tables:
                # Individual-league overview pages simply lack the advanced squad
                # tables (passing/defense/possession/gca/keeper_adv). Skip them.
                # ponytail: skip-not-crash; POR/NED team-advanced is out of scope.
                continue
            (html_table,) = tables
            df_table = _parse_table(html_table)
            df_table["league"] = lkey
            df_table["season"] = skey
            df_table["url"] = html_table.xpath(".//*[@data-stat='team']/a/@href")
            if big_five:
                df_table["league"] = (
                    df_table.xs("Comp", axis=1, level=1).squeeze().map(BIG_FIVE_DICT)
                )
                df_table.drop("Comp", axis=1, level=1, inplace=True)
                df_table.drop("Rk", axis=1, level=1, inplace=True)
            teams.append(df_table)
        if not teams:
            return pd.DataFrame()  # advanced type absent for these leagues (POR/NED)
        return (
            _concat(teams, key=["league", "season"])
            .rename(columns={"Squad": "team", "# Pl": "players_used"})
            .replace({"team": TEAMNAME_REPLACEMENTS})
            .set_index(["league", "season", "team"])
            .sort_index()
        )


# Patch onto the real FBref class (name must stay "FBref" for league filtering).
sd.FBref.read_player_season_stats = _read_player_season_stats
sd.FBref.read_team_season_stats = _read_team_season_stats
FBref = sd.FBref
