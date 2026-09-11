-- RotoWire prop market + defensive scan-gap lake.
-- Raw source rows remain auditable; scan results are disposable model output.

CREATE TABLE IF NOT EXISTS raw_rotowire_props (
    season INTEGER,
    player_name VARCHAR,
    player_id VARCHAR,
    team VARCHAR,
    opponent VARCHAR,
    market VARCHAR,
    position VARCHAR,
    targets DOUBLE,
    target_share DOUBLE,
    target_rank INTEGER,
    line DOUBLE,
    projection DOUBLE,
    over_odds DOUBLE,
    under_odds DOUBLE,
    game_id VARCHAR,
    captured_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS team_defense_features (
    season INTEGER,
    team VARCHAR,
    points_allowed_pg DOUBLE,
    passing_yards_allowed_pg DOUBLE,
    rushing_yards_allowed_pg DOUBLE,
    sack_pct DOUBLE,
    interceptions_pg DOUBLE,
    red_zone_allowed_pct DOUBLE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, team)
);

CREATE TABLE IF NOT EXISTS prop_scan_results (
    season INTEGER,
    player_name VARCHAR,
    player_id VARCHAR,
    team VARCHAR,
    opponent VARCHAR,
    market VARCHAR,
    target_role VARCHAR,
    targets DOUBLE,
    target_share DOUBLE,
    target_rank INTEGER,
    line DOUBLE,
    projection DOUBLE,
    adjusted_projection DOUBLE,
    adjusted_gap DOUBLE,
    opponent_defense_percentile DOUBLE,
    direction VARCHAR,
    scan_score DOUBLE,
    status VARCHAR,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
