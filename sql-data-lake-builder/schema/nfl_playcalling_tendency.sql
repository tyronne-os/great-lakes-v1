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