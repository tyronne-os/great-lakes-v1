"""Derive offensive play-calling tendencies from NFLverse play-by-play."""

from __future__ import annotations

import duckdb


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nfl_playcalling_tendency (
    season INTEGER NOT NULL,
    week INTEGER,
    team VARCHAR NOT NULL,
    offensive_plays INTEGER NOT NULL,
    pass_attempts INTEGER NOT NULL,
    rush_attempts INTEGER NOT NULL,
    pass_rate DOUBLE,
    rush_rate DOUBLE,
    third_down_plays INTEGER NOT NULL,
    third_down_pass_rate DOUBLE,
    red_zone_plays INTEGER NOT NULL,
    red_zone_pass_rate DOUBLE,
    goal_to_go_plays INTEGER NOT NULL,
    goal_to_go_rush_rate DOUBLE,
    total_targets INTEGER NOT NULL,
    unique_target_count INTEGER NOT NULL,
    second_target_share DOUBLE,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, week, team)
);

CREATE TABLE IF NOT EXISTS nfl_team_target_tendency (
    season INTEGER NOT NULL,
    week INTEGER,
    team VARCHAR NOT NULL,
    target_rank INTEGER NOT NULL,
    player_id VARCHAR,
    player_name VARCHAR,
    targets INTEGER NOT NULL,
    target_share DOUBLE,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, week, team, target_rank)
);
"""


def build_playcalling_tendency(
    connection: duckdb.DuckDBPyConnection,
    pbp_relation: str = "nfl_pbp",
) -> dict[str, int]:
    """Build team and target tendency tables from an NFLverse PBP relation."""
    connection.execute(SCHEMA_SQL)
    connection.execute("DELETE FROM nfl_playcalling_tendency")
    connection.execute("DELETE FROM nfl_team_target_tendency")

    connection.execute(f"""
        INSERT INTO nfl_playcalling_tendency
        SELECT
            season,
            week,
            posteam AS team,
            COUNT(*) FILTER (WHERE play_type IN ('pass', 'run'))::INTEGER,
            COUNT(*) FILTER (WHERE pass_attempt = 1)::INTEGER,
            COUNT(*) FILTER (WHERE rush_attempt = 1)::INTEGER,
            COUNT(*) FILTER (WHERE pass_attempt = 1)::DOUBLE /
                NULLIF(COUNT(*) FILTER (WHERE play_type IN ('pass', 'run')), 0),
            COUNT(*) FILTER (WHERE rush_attempt = 1)::DOUBLE /
                NULLIF(COUNT(*) FILTER (WHERE play_type IN ('pass', 'run')), 0),
            COUNT(*) FILTER (WHERE down = 3)::INTEGER,
            COUNT(*) FILTER (WHERE down = 3 AND pass_attempt = 1)::DOUBLE /
                NULLIF(COUNT(*) FILTER (WHERE down = 3), 0),
            COUNT(*) FILTER (WHERE yardline_100 <= 20)::INTEGER,
            COUNT(*) FILTER (WHERE yardline_100 <= 20 AND pass_attempt = 1)::DOUBLE /
                NULLIF(COUNT(*) FILTER (WHERE yardline_100 <= 20), 0),
            COUNT(*) FILTER (WHERE goal_to_go = 1)::INTEGER,
            COUNT(*) FILTER (WHERE goal_to_go = 1 AND rush_attempt = 1)::DOUBLE /
                NULLIF(COUNT(*) FILTER (WHERE goal_to_go = 1), 0),
            COUNT(*) FILTER (WHERE receiver_player_id IS NOT NULL)::INTEGER,
            COUNT(DISTINCT receiver_player_id)::INTEGER,
            NULL,
            CURRENT_TIMESTAMP
        FROM {pbp_relation}
        WHERE posteam IS NOT NULL
        GROUP BY season, week, posteam
    """)

    connection.execute(f"""
        INSERT INTO nfl_team_target_tendency
        WITH targets AS (
            SELECT
                season,
                week,
                posteam AS team,
                receiver_player_id AS player_id,
                receiver_player_name AS player_name,
                COUNT(*)::INTEGER AS targets
            FROM {pbp_relation}
            WHERE posteam IS NOT NULL
              AND receiver_player_id IS NOT NULL
              AND pass_attempt = 1
            GROUP BY 1, 2, 3, 4, 5
        ), ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY season, week, team ORDER BY targets DESC, player_id
                ) AS target_rank,
                targets::DOUBLE / NULLIF(SUM(targets) OVER (PARTITION BY season, week, team), 0)
                    AS target_share
            FROM targets
        )
        SELECT season, week, team, target_rank, player_id, player_name,
               targets, target_share, CURRENT_TIMESTAMP
        FROM ranked
        WHERE target_rank <= 3
    """)
    connection.execute("""
        UPDATE nfl_playcalling_tendency AS tendency
        SET second_target_share = target.share
        FROM (
            SELECT season, week, team, target_share AS share
            FROM nfl_team_target_tendency
            WHERE target_rank = 2
        ) AS target
        WHERE tendency.season = target.season
          AND tendency.week = target.week
          AND tendency.team = target.team
    """)

    return {
        "playcalling_rows": connection.execute("SELECT COUNT(*) FROM nfl_playcalling_tendency").fetchone()[0],
        "target_tendency_rows": connection.execute("SELECT COUNT(*) FROM nfl_team_target_tendency").fetchone()[0],
    }
