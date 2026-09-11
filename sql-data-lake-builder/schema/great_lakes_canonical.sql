-- GREAT LAKES V1 canonical DuckDB schema.
-- Training boundary: 2023-2025. Keep 2026 for out-of-sample evaluation.
-- This file defines storage contracts only; prediction logic belongs above it.

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- One row per source pull or local file load.
CREATE TABLE IF NOT EXISTS bronze.ingestion_runs (
    run_id VARCHAR PRIMARY KEY,
    source_name VARCHAR NOT NULL,
    source_kind VARCHAR NOT NULL,
    source_uri VARCHAR,
    season INTEGER,
    week INTEGER,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    row_count INTEGER,
    content_hash VARCHAR,
    status VARCHAR NOT NULL,
    error_message VARCHAR
);

-- Immutable raw payload references. Large Parquet files stay on disk/object storage.
CREATE TABLE IF NOT EXISTS bronze.raw_snapshots (
    snapshot_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    source_name VARCHAR NOT NULL,
    source_uri VARCHAR,
    file_path VARCHAR,
    file_format VARCHAR,
    captured_at TIMESTAMP NOT NULL,
    content_hash VARCHAR,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS silver.sports (
    sport_id VARCHAR PRIMARY KEY,
    sport_name VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS silver.leagues (
    league_id VARCHAR PRIMARY KEY,
    sport_id VARCHAR NOT NULL,
    league_name VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS silver.teams (
    team_id VARCHAR PRIMARY KEY,
    league_id VARCHAR NOT NULL,
    team_name VARCHAR NOT NULL,
    abbreviation VARCHAR,
    conference VARCHAR,
    division VARCHAR,
    valid_from_season INTEGER,
    valid_to_season INTEGER
);

CREATE TABLE IF NOT EXISTS silver.players (
    player_id VARCHAR PRIMARY KEY,
    league_id VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    position VARCHAR,
    birth_date DATE,
    active BOOLEAN,
    valid_from_season INTEGER,
    valid_to_season INTEGER
);

CREATE TABLE IF NOT EXISTS silver.games (
    game_id VARCHAR PRIMARY KEY,
    league_id VARCHAR NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER,
    game_date DATE,
    home_team_id VARCHAR,
    away_team_id VARCHAR,
    home_score INTEGER,
    away_score INTEGER,
    venue VARCHAR,
    status VARCHAR,
    source_name VARCHAR NOT NULL,
    source_updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.player_team_stints (
    season INTEGER NOT NULL,
    week INTEGER,
    player_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    position VARCHAR,
    roster_status VARCHAR,
    snap_share DOUBLE,
    route_share DOUBLE,
    PRIMARY KEY (season, week, player_id, team_id)
);

-- Flexible normalized stat observations. One row per entity/metric/time grain.
CREATE TABLE IF NOT EXISTS silver.stat_observations (
    observation_id VARCHAR PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER,
    game_id VARCHAR,
    team_id VARCHAR,
    opponent_team_id VARCHAR,
    player_id VARCHAR,
    stat_group VARCHAR NOT NULL,
    stat_name VARCHAR NOT NULL,
    stat_value DOUBLE,
    unit VARCHAR,
    split_type VARCHAR,
    source_name VARCHAR NOT NULL,
    source_captured_at TIMESTAMP,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.player_target_logs (
    season INTEGER NOT NULL,
    week INTEGER,
    game_id VARCHAR,
    team_id VARCHAR,
    player_id VARCHAR NOT NULL,
    target_rank INTEGER,
    targets INTEGER NOT NULL,
    target_share DOUBLE,
    third_down_targets INTEGER,
    red_zone_targets INTEGER,
    goal_to_go_targets INTEGER,
    source_name VARCHAR NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.team_playcalling_tendencies (
    season INTEGER NOT NULL,
    week INTEGER,
    team_id VARCHAR NOT NULL,
    offensive_plays INTEGER,
    pass_attempts INTEGER,
    rush_attempts INTEGER,
    pass_rate DOUBLE,
    rush_rate DOUBLE,
    third_down_plays INTEGER,
    third_down_pass_rate DOUBLE,
    red_zone_plays INTEGER,
    red_zone_pass_rate DOUBLE,
    goal_to_go_plays INTEGER,
    goal_to_go_rush_rate DOUBLE,
    second_target_share DOUBLE,
    source_name VARCHAR NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, week, team_id)
);

CREATE TABLE IF NOT EXISTS silver.touchdown_scoring_logs (
    season INTEGER NOT NULL,
    week INTEGER,
    game_id VARCHAR NOT NULL,
    scoring_team_id VARCHAR,
    opponent_team_id VARCHAR,
    scorer_id VARCHAR,
    scorer_type VARCHAR,
    touchdown_count INTEGER NOT NULL,
    red_zone_touchdowns INTEGER NOT NULL,
    goal_to_go_touchdowns INTEGER NOT NULL,
    third_down_touchdowns INTEGER NOT NULL,
    source_name VARCHAR NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.opponent_touchdown_logs (
    season INTEGER NOT NULL,
    week INTEGER,
    game_id VARCHAR NOT NULL,
    defense_team_id VARCHAR NOT NULL,
    scoring_team_id VARCHAR,
    opponent_touchdowns INTEGER NOT NULL,
    red_zone_touchdowns_allowed INTEGER NOT NULL,
    goal_to_go_touchdowns_allowed INTEGER NOT NULL,
    third_down_touchdowns_allowed INTEGER NOT NULL,
    source_name VARCHAR NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.official_assignments (
    season INTEGER NOT NULL,
    week INTEGER,
    game_id VARCHAR NOT NULL,
    official_id VARCHAR,
    official_name VARCHAR,
    role VARCHAR,
    source_name VARCHAR NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, week, game_id, official_id, role)
);

-- Market snapshots preserve line movement and source timing.
CREATE TABLE IF NOT EXISTS silver.market_snapshots (
    market_snapshot_id VARCHAR PRIMARY KEY,
    captured_at TIMESTAMP NOT NULL,
    game_id VARCHAR,
    season INTEGER NOT NULL,
    week INTEGER,
    sportsbook VARCHAR,
    player_id VARCHAR,
    team_id VARCHAR,
    opponent_team_id VARCHAR,
    market_type VARCHAR NOT NULL,
    selection VARCHAR NOT NULL,
    line DOUBLE,
    american_odds INTEGER,
    projection DOUBLE,
    source_name VARCHAR NOT NULL
);

-- Features available to model training; no prediction is stored here.
CREATE TABLE IF NOT EXISTS gold.model_features (
    feature_row_id VARCHAR PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER,
    game_id VARCHAR,
    player_id VARCHAR,
    team_id VARCHAR,
    opponent_team_id VARCHAR,
    feature_set VARCHAR NOT NULL,
    features JSON NOT NULL,
    as_of_timestamp TIMESTAMP NOT NULL,
    source_max_timestamp TIMESTAMP,
    data_quality_score DOUBLE,
    is_out_of_sample BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS gold.prediction_runs (
    prediction_run_id VARCHAR PRIMARY KEY,
    model_name VARCHAR NOT NULL,
    model_version VARCHAR NOT NULL,
    training_cutoff_season INTEGER,
    created_at TIMESTAMP NOT NULL,
    calibration_method VARCHAR,
    notes VARCHAR
);

CREATE TABLE IF NOT EXISTS gold.predictions (
    prediction_id VARCHAR PRIMARY KEY,
    prediction_run_id VARCHAR NOT NULL,
    feature_row_id VARCHAR NOT NULL,
    game_id VARCHAR,
    player_id VARCHAR,
    market_type VARCHAR NOT NULL,
    selection VARCHAR NOT NULL,
    model_probability DOUBLE NOT NULL,
    market_probability DOUBLE,
    vig_free_probability DOUBLE,
    expected_value DOUBLE,
    uncertainty DOUBLE,
    confidence_score DOUBLE,
    decision VARCHAR NOT NULL,
    reason_codes JSON,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.prediction_results (
    prediction_id VARCHAR PRIMARY KEY,
    settled_at TIMESTAMP,
    actual_value DOUBLE,
    won BOOLEAN,
    profit_loss DOUBLE,
    closing_line DOUBLE,
    closing_american_odds INTEGER
);

CREATE INDEX IF NOT EXISTS idx_stat_observations_lookup
    ON silver.stat_observations (season, week, team_id, player_id, stat_name);
CREATE INDEX IF NOT EXISTS idx_targets_lookup
    ON silver.player_target_logs (season, week, team_id, target_rank);
CREATE INDEX IF NOT EXISTS idx_market_lookup
    ON silver.market_snapshots (season, week, game_id, player_id, market_type);
CREATE INDEX IF NOT EXISTS idx_predictions_decision
    ON gold.predictions (created_at, decision, market_type);
