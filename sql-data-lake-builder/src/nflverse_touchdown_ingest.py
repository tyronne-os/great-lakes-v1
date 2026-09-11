"""Download NFLverse play-by-play seasons and build touchdown logs in DuckDB."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import Request, urlopen

import duckdb

from nfl_touchdown_logs import build_touchdown_logs

NFLVERSE_PBP_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "pbp/play_by_play_{season}.parquet"
)


def download_season(season: int, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / f"play_by_play_{season}.parquet"
    if destination.exists() and destination.stat().st_size > 0:
        return destination

    request = Request(NFLVERSE_PBP_URL.format(season=season))
    response = urlopen(request, timeout=120)
    with destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    return destination


def ingest_seasons(seasons: list[int], database_path: Path, cache_dir: Path) -> dict[int, dict[str, int]]:
    paths = [download_season(season, cache_dir) for season in seasons]
    with duckdb.connect(str(database_path)) as connection:
        relations = []
        for season, parquet_path in zip(seasons, paths):
            relation = f"nfl_pbp_{season}"
            path_sql = str(parquet_path).replace("'", "''")
            connection.execute(
                f"CREATE OR REPLACE VIEW {relation} AS SELECT * FROM read_parquet('{path_sql}')"
            )
            relations.append(relation)
        union_sql = " UNION ALL ".join(f"SELECT * FROM {relation}" for relation in relations)
        connection.execute(f"CREATE OR REPLACE VIEW nfl_pbp_training AS {union_sql}")
        summary = build_touchdown_logs(connection, "nfl_pbp_training")
    return {season: summary for season in seasons}


def main() -> None:
    parser = argparse.ArgumentParser(description="Load NFLverse PBP into DuckDB touchdown logs")
    parser.add_argument("--seasons", nargs="+", type=int, default=[2023, 2024, 2025])
    parser.add_argument("--database", type=Path, default=Path("output/sports_lake.duckdb"))
    parser.add_argument("--cache-dir", type=Path, default=Path("output/nflverse"))
    args = parser.parse_args()
    print(ingest_seasons(args.seasons, args.database, args.cache_dir))


if __name__ == "__main__":
    main()
