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
