"""Build NFL touchdown scoring and opponent-TD logs in DuckDB.

The input relation should be an NFLverse/nflfastR play-by-play table with fields
such as season, week, game_id, posteam, defteam, touchdown, td_team,
td_player_id, td_player_name, down, goal_to_go, and yardline_100.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nfl_touchdown_scoring_log (
    season INTEGER NOT NULL,
    week INTEGER,
    game_id VARCHAR NOT NULL,
    game_date DATE,
    scoring_team VARCHAR,
    opponent_team VARCHAR,
    scorer_id VARCHAR,
    scorer_name VARCHAR,
    scorer_type VARCHAR,
    touchdown_count INTEGER NOT NULL,
    red_zone_touchdown BOOLEAN,
    goal_to_go_touchdown BOOLEAN,
    third_down_touchdown BOOLEAN,
    source_row_count INTEGER,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nfl_opponent_touchdown_log (
    season INTEGER NOT NULL,
    week INTEGER,
    game_id VARCHAR NOT NULL,
    game_date DATE,
    defense_team VARCHAR NOT NULL,
    scoring_team VARCHAR,
    opponent_touchdowns INTEGER NOT NULL,
    red_zone_touchdowns_allowed INTEGER NOT NULL,
    goal_to_go_touchdowns_allowed INTEGER NOT NULL,
    third_down_touchdowns_allowed INTEGER NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nfl_touchdown_team_rollup (
    season INTEGER NOT NULL,
    team VARCHAR NOT NULL,
    through_week INTEGER,
    offensive_touchdowns INTEGER NOT NULL,
    defensive_touchdowns_allowed INTEGER NOT NULL,
    red_zone_touchdowns INTEGER NOT NULL,
    red_zone_touchdowns_allowed INTEGER NOT NULL,
    goal_to_go_touchdowns INTEGER NOT NULL,
    goal_to_go_touchdowns_allowed INTEGER NOT NULL,
    third_down_touchdowns INTEGER NOT NULL,
    third_down_touchdowns_allowed INTEGER NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, team, through_week)
);
"""


def _columns(connection: duckdb.DuckDBPyConnection, relation: str) -> set[str]:
    return {
        row[0].lower()
        for row in connection.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
    }


def _expr(columns: set[str], name: str, fallback: str = "NULL") -> str:
    return name if name in columns else fallback


def build_touchdown_logs(
    connection: duckdb.DuckDBPyConnection,
    pbp_relation: str = "nfl_pbp",
) -> dict[str, int]:
    """Derive touchdown logs from a loaded NFLverse PBP relation."""
    columns = _columns(connection, pbp_relation)
    required = {"season", "game_id", "touchdown"}
    missing = required - columns
    if missing:
        raise ValueError(f"PBP relation is missing required columns: {sorted(missing)}")

    season = _expr(columns, "season")
    week = _expr(columns, "week")
    game_id = _expr(columns, "game_id")
    game_date = _expr(columns, "game_date")
    scoring_team = _expr(columns, "td_team", _expr(columns, "posteam"))
    defense_team = _expr(columns, "defteam")
    scorer_id = _expr(columns, "td_player_id")
    scorer_name = _expr(columns, "td_player_name")
    posteam = _expr(columns, "posteam")
    down = _expr(columns, "down")
    goal_to_go = _expr(columns, "goal_to_go", "0")
    yardline = _expr(columns, "yardline_100")
    touchdown = _expr(columns, "touchdown", "0")

    connection.execute(SCHEMA_SQL)
    connection.execute("DELETE FROM nfl_touchdown_scoring_log")
    connection.execute("DELETE FROM nfl_opponent_touchdown_log")
    connection.execute("DELETE FROM nfl_touchdown_team_rollup")

    connection.execute(f"""
        INSERT INTO nfl_touchdown_scoring_log (
            season, week, game_id, game_date, scoring_team, opponent_team,
            scorer_id, scorer_name, scorer_type, touchdown_count,
            red_zone_touchdown, goal_to_go_touchdown, third_down_touchdown,
            source_row_count
        )
        SELECT
            {season}, {week}, {game_id}, TRY_CAST({game_date} AS DATE),
            {scoring_team}, {defense_team}, {scorer_id}, {scorer_name},
            CASE
                WHEN LOWER(COALESCE(CAST({scorer_name} AS VARCHAR), '')) LIKE '%defensive%'
                    THEN 'defense'
                WHEN ANY_VALUE({posteam}) = {scoring_team} THEN 'offense'
                ELSE 'return'
            END,
            COUNT(*)::INTEGER,
            BOOL_OR(COALESCE({yardline}, 999) <= 20),
            BOOL_OR(COALESCE({goal_to_go}, 0) = 1),
            BOOL_OR(COALESCE({down}, 0) = 3),
            COUNT(*)::INTEGER
        FROM {pbp_relation}
        WHERE COALESCE({touchdown}, 0) = 1
          AND {scoring_team} IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    """)

    connection.execute(f"""
        INSERT INTO nfl_opponent_touchdown_log (
            season, week, game_id, game_date, defense_team, scoring_team,
            opponent_touchdowns, red_zone_touchdowns_allowed,
            goal_to_go_touchdowns_allowed, third_down_touchdowns_allowed
        )
        SELECT
            {season}, {week}, {game_id}, TRY_CAST({game_date} AS DATE),
            {defense_team}, {scoring_team},
            COUNT(*)::INTEGER,
            COUNT(*) FILTER (WHERE COALESCE({yardline}, 999) <= 20)::INTEGER,
            COUNT(*) FILTER (WHERE COALESCE({goal_to_go}, 0) = 1)::INTEGER,
            COUNT(*) FILTER (WHERE COALESCE({down}, 0) = 3)::INTEGER
        FROM {pbp_relation}
        WHERE COALESCE({touchdown}, 0) = 1
          AND {defense_team} IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5, 6
    """)

    connection.execute("""
        INSERT INTO nfl_touchdown_team_rollup
        SELECT
            season,
            team,
            through_week,
            SUM(offensive_touchdowns)::INTEGER,
            SUM(defensive_touchdowns_allowed)::INTEGER,
            SUM(red_zone_touchdowns)::INTEGER,
            SUM(red_zone_touchdowns_allowed)::INTEGER,
            SUM(goal_to_go_touchdowns)::INTEGER,
            SUM(goal_to_go_touchdowns_allowed)::INTEGER,
            SUM(third_down_touchdowns)::INTEGER,
            SUM(third_down_touchdowns_allowed)::INTEGER,
            CURRENT_TIMESTAMP
        FROM (
            SELECT season, scoring_team AS team, MAX(week) AS through_week,
                   SUM(touchdown_count) AS offensive_touchdowns,
                   0 AS defensive_touchdowns_allowed,
                   SUM(red_zone_touchdown::INTEGER) AS red_zone_touchdowns,
                   0 AS red_zone_touchdowns_allowed,
                   SUM(goal_to_go_touchdown::INTEGER) AS goal_to_go_touchdowns,
                   0 AS goal_to_go_touchdowns_allowed,
                   SUM(third_down_touchdown::INTEGER) AS third_down_touchdowns,
                   0 AS third_down_touchdowns_allowed
            FROM nfl_touchdown_scoring_log
            GROUP BY season, scoring_team
            UNION ALL
            SELECT season, defense_team AS team, MAX(week) AS through_week,
                   0, SUM(opponent_touchdowns), 0,
                   SUM(red_zone_touchdowns_allowed), 0,
                   SUM(goal_to_go_touchdowns_allowed), 0,
                   SUM(third_down_touchdowns_allowed)
            FROM nfl_opponent_touchdown_log
            GROUP BY season, defense_team
        ) grouped
        GROUP BY season, team, through_week
    """)

    return {
        "scoring_rows": connection.execute("SELECT COUNT(*) FROM nfl_touchdown_scoring_log").fetchone()[0],
        "opponent_rows": connection.execute("SELECT COUNT(*) FROM nfl_opponent_touchdown_log").fetchone()[0],
        "team_rollups": connection.execute("SELECT COUNT(*) FROM nfl_touchdown_team_rollup").fetchone()[0],
    }


def load_pbp_file(
    database_path: Path,
    pbp_path: Path,
    file_format: str = "parquet",
) -> dict[str, int]:
    """Load an NFLverse CSV/Parquet file and build the touchdown logs."""
    with duckdb.connect(str(database_path)) as connection:
        if file_format == "parquet":
            connection.execute("CREATE OR REPLACE VIEW nfl_pbp AS SELECT * FROM read_parquet(?)", [str(pbp_path)])
        else:
            connection.execute("CREATE OR REPLACE VIEW nfl_pbp AS SELECT * FROM read_csv_auto(?)", [str(pbp_path)])
        return build_touchdown_logs(connection)
