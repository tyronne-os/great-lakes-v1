"""RotoWire prop lake and defensive scan-gap ranking.

Inputs are normalized CSV or JSON exports from a prop board and a team-defense
feature table. The scanner is deliberately source-agnostic after ingestion so
RotoWire can remain the market-discovery source without becoming the model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

import duckdb


PROP_ALIASES = {
    "season": ("season", "year"),
    "player_name": ("player_name", "player", "name"),
    "player_id": ("player_id", "playerid", "id"),
    "team": ("team", "team_abbr", "teamabbrev"),
    "opponent": ("opponent", "opp", "opponent_team"),
    "market": ("market", "prop", "stat_type", "category"),
    "position": ("position", "pos"),
    "targets": ("targets", "target_count", "receiving_targets"),
    "target_share": ("target_share", "target_pct", "targets_pct"),
    "target_rank": ("target_rank", "team_target_rank", "target_order", "receiver_rank"),
    "line": ("line", "prop_line", "odds_line"),
    "projection": ("projection", "projected_value", "roto_projection", "proj"),
    "over_odds": ("over_odds", "over_price", "over"),
    "under_odds": ("under_odds", "under_price", "under"),
    "game_id": ("game_id", "event_id"),
    "captured_at": ("captured_at", "retrieved_at", "timestamp"),
}

DEFENSE_ALIASES = {
    "season": ("season", "year"),
    "team": ("team", "team_abbr", "teamabbrev"),
    "points_allowed_pg": ("points_allowed_pg", "opponent_points_per_game", "opp_points_pg"),
    "passing_yards_allowed_pg": ("passing_yards_allowed_pg", "opponent_passing_yards_per_game"),
    "rushing_yards_allowed_pg": ("rushing_yards_allowed_pg", "opponent_rushing_yards_per_game"),
    "sack_pct": ("sack_pct", "sack_percentage"),
    "interceptions_pg": ("interceptions_pg", "opponent_interceptions_per_game"),
    "red_zone_allowed_pct": ("red_zone_allowed_pct", "opponent_red_zone_scoring_pct"),
}


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _normalize_record(record: dict[str, Any], aliases: dict[str, tuple[str, ...]]) -> dict[str, Any]:
    keyed = {_key(k): v for k, v in record.items()}
    normalized: dict[str, Any] = {}
    for target, names in aliases.items():
        for name in names:
            if _key(name) in keyed and keyed[_key(name)] not in (None, ""):
                normalized[target] = keyed[_key(name)]
                break
    return normalized


def _read_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            for key in ("props", "data", "rows", "records"):
                if isinstance(value.get(key), list):
                    return value[key]
            return [value]
        return value
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _market_kind(market: str) -> str:
    value = market.lower()
    if "pass" in value:
        return "passing"
    if "rush" in value:
        return "rushing"
    if "receiv" in value or "reception" in value or "target" in value:
        return "receiving"
    if "tackle" in value or "sack" in value or "interception" in value:
        return "defense"
    return "general"


def _target_role(prop: dict[str, Any]) -> str:
    position = str(prop.get("position", "")).upper()
    rank = _number(prop.get("target_rank"))
    if position in {"WR", "WIDE RECEIVER", "TE", "TIGHT END"} and rank == 2:
        return "secondary_target"
    if rank == 1:
        return "primary_target"
    return "unclassified"


def _defense_score(row: dict[str, Any], kind: str) -> float:
    """Higher means a tougher defense for the selected player market."""
    fields = {
        "passing": ("passing_yards_allowed_pg", "points_allowed_pg", "sack_pct"),
        "rushing": ("rushing_yards_allowed_pg", "points_allowed_pg"),
        "receiving": ("passing_yards_allowed_pg", "points_allowed_pg", "sack_pct"),
        "defense": ("points_allowed_pg", "red_zone_allowed_pct"),
        "general": ("points_allowed_pg",),
    }[kind]
    values = [_number(row.get(field)) for field in fields]
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else 0.0


def _percentile(value: float, values: list[float]) -> float:
    if not values or value == 0:
        return 0.5
    return sum(item <= value for item in values) / len(values)


def scan_gap(props: Iterable[dict[str, Any]], defenses: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    defense_rows = [_normalize_record(row, DEFENSE_ALIASES) for row in defenses]
    defense_by_key = {
        (int(_number(row.get("season")) or 0), str(row.get("team", "")).upper()): row
        for row in defense_rows
    }
    results = []

    for raw_prop in props:
        prop = _normalize_record(raw_prop, PROP_ALIASES)
        season = int(_number(prop.get("season")) or 0)
        market = str(prop.get("market", "unknown"))
        line = _number(prop.get("line"))
        projection = _number(prop.get("projection"))
        if line is None or projection is None:
            continue
        opponent = str(prop.get("opponent", "")).upper()
        defense = defense_by_key.get((season, opponent), {})
        if not defense:
            defense = defense_by_key.get((0, opponent), {})
        kind = _market_kind(market)
        target_role = _target_role(prop)
        strength = _defense_score(defense, kind)
        defense_values = [
            _defense_score(row, kind)
            for row in defense_rows
            if int(_number(row.get("season")) or 0) == season
        ] or [_defense_score(row, kind) for row in defense_rows]
        strength_pct = _percentile(strength, defense_values)
        raw_gap = projection - line
        # Tough defense suppresses offensive projections; the adjustment is
        # intentionally modest until historical calibration supplies weights.
        suppression = max(0.0, strength_pct - 0.5) * max(abs(line) * 0.08, 1.0)
        adjusted_projection = projection - suppression if kind != "defense" else projection + suppression
        adjusted_gap = adjusted_projection - line
        direction = "OVER" if adjusted_gap > 0 else "UNDER"
        gap_score = min(abs(adjusted_gap) / max(abs(line), 1.0), 1.0)
        edge_score = round(50 + 35 * gap_score * (0.75 + 0.5 * abs(strength_pct - 0.5)), 2)
        # WR2 target volume is the core discovery signal. It is a modest
        # ranking bonus, not a probability shortcut, until backtests calibrate it.
        if target_role == "secondary_target" and kind in {"receiving", "general"}:
            edge_score = round(min(100.0, edge_score + 4.0), 2)
        results.append({
            **prop,
            "season": season,
            "target_role": target_role,
            "targets": _number(prop.get("targets")),
            "target_share": _number(prop.get("target_share")),
            "target_rank": _number(prop.get("target_rank")),
            "opponent_defense_strength": round(strength, 4),
            "opponent_defense_percentile": round(strength_pct, 4),
            "raw_gap": round(raw_gap, 4),
            "adjusted_projection": round(adjusted_projection, 4),
            "adjusted_gap": round(adjusted_gap, 4),
            "direction": direction,
            "scan_score": edge_score,
            "status": "WATCH" if edge_score >= 65 else "PASS",
        })

    return sorted(results, key=lambda row: row["scan_score"], reverse=True)


def init_db(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS raw_rotowire_props (
            season INTEGER, player_name VARCHAR, player_id VARCHAR, team VARCHAR, opponent VARCHAR,
            position VARCHAR, targets DOUBLE, target_share DOUBLE, target_rank INTEGER,
            market VARCHAR, line DOUBLE, projection DOUBLE, over_odds DOUBLE,
            under_odds DOUBLE, game_id VARCHAR, captured_at TIMESTAMP,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS team_defense_features (
            season INTEGER, team VARCHAR, points_allowed_pg DOUBLE,
            passing_yards_allowed_pg DOUBLE, rushing_yards_allowed_pg DOUBLE,
            sack_pct DOUBLE, interceptions_pg DOUBLE, red_zone_allowed_pct DOUBLE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (season, team)
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS prop_scan_results (
            season INTEGER, player_name VARCHAR, player_id VARCHAR, team VARCHAR, opponent VARCHAR,
            market VARCHAR, target_role VARCHAR, targets DOUBLE, target_share DOUBLE, target_rank INTEGER,
            line DOUBLE, projection DOUBLE, adjusted_projection DOUBLE,
            adjusted_gap DOUBLE, opponent_defense_percentile DOUBLE,
            direction VARCHAR, scan_score DOUBLE, status VARCHAR,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def run(props_path: Path, defense_path: Path, database_path: Path) -> list[dict[str, Any]]:
    props = _read_records(props_path)
    defenses = _read_records(defense_path)
    results = scan_gap(props, defenses)
    with duckdb.connect(str(database_path)) as connection:
        init_db(connection)
        for row in results:
            connection.execute("""
                INSERT INTO prop_scan_results
                (season, player_name, player_id, team, opponent, market, target_role, targets,
                 target_share, target_rank, line, projection,
                 adjusted_projection, adjusted_gap, opponent_defense_percentile,
                 direction, scan_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [row.get(field) for field in (
                "season", "player_name", "player_id", "team", "opponent", "market",
                "target_role", "targets", "target_share", "target_rank", "line", "projection",
                "adjusted_projection", "adjusted_gap",
                "opponent_defense_percentile", "direction", "scan_score", "status"
            )])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan RotoWire props for defensive scan gaps")
    parser.add_argument("--props", type=Path, required=True, help="RotoWire CSV or JSON export")
    parser.add_argument("--defense", type=Path, required=True, help="Team defense CSV or JSON export")
    parser.add_argument("--database", type=Path, default=Path("sports_lake.duckdb"))
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    for row in run(args.props, args.defense, args.database)[:args.limit]:
        print(json.dumps(row, default=str))


if __name__ == "__main__":
    main()
