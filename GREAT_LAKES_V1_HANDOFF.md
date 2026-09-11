# GREAT LAKES V1

## Handoff Brief

This repository is the working handoff for the Great Lakes sports data lake and
prop-value research system. It is designed to continue in another coding agent
or extension without losing the decisions made during the first build phase.

## Objective

Build a multi-sport, evidence-driven probability and market-value system for
NFL, MLB, WNBA, and college football. The first production slice is NFL player
props, with special attention to:

- WR2 target opportunity and target-share gaps
- RB red-zone and goal-to-go touchdown usage
- Third-down target and touchdown tendencies
- Opponent touchdown allowance by situation
- Coach/team play-calling fingerprints
- Under markets, regression, fatigue, and human performance volatility

The system must produce calibrated probabilities, expected value, confidence,
and a no-bet/pass result. It must not present ordinary sports outcomes as
certain.

## Current Architecture

```text
RotoWire prop board and TeamRankings schema references
                    |
                    v
          Raw CSV/JSON/Parquet snapshots
                    |
                    v
                  DuckDB
          /                         \
 NFLverse play-by-play              Prop scan results
          |                           |
          v                           v
 Touchdown logs                 Probability/EV layer
 Play-calling tendencies        React/API dashboard
```

DuckDB is the local analytical engine. NFLverse is the historical NFL source.
RotoWire is the market/prop discovery layer. TeamRankings pages define feature
vocabulary and chart semantics; they are not assumed to be the permanent live
source.

## Completed Work

### Environment

- DuckDB `1.5.5` installed in `sql-data-lake-builder/venv`.
- Podman works rootless with `crun`; Docker is not required.
- The existing goclone image builds and runs with Podman.
- Hugging Face token is available through the vault-backed `HF_TOKEN` variable.

### Prop Scan

- `sql-data-lake-builder/src/prop_gap_scanner.py`
- `sql-data-lake-builder/schema/prop_gap_lake.sql`
- `sql-data-lake-builder/cli.py` command: `scan-gaps`

The scanner ingests RotoWire-style CSV/JSON exports and defensive features,
then calculates an adjusted projection, defensive percentile, scan gap,
direction, scan score, and `WATCH`/`PASS` status.

Target fields include `targets`, `target_share`, `target_rank`, and `target_role`.
The WR2/secondary-target role receives a small ranking bonus for receiving
markets. This bonus is intentionally not a probability shortcut until it is
backtested.

Run it with:

```bash
cd sql-data-lake-builder
venv/bin/python cli.py scan-gaps \
  --props path/to/rotowire_props.csv \
  --defense path/to/team_defense.csv \
  --database output/sports_lake.duckdb
```

### Touchdown Logs

- `sql-data-lake-builder/src/nfl_touchdown_logs.py`
- `sql-data-lake-builder/schema/nfl_touchdown_logs.sql`
- `sql-data-lake-builder/src/nflverse_touchdown_ingest.py`

The lake contains NFLverse-derived tables:

- `nfl_touchdown_scoring_log`
- `nfl_opponent_touchdown_log`
- `nfl_touchdown_team_rollup`

The loaded training seasons are 2023, 2024, and 2025. 2026 remains reserved
for out-of-sample evaluation.

Verified season counts:

| Season | Scoring logs | Opponent logs |
|---|---:|---:|
| 2023 | 1,192 | 585 |
| 2024 | 1,247 | 588 |
| 2025 | 1,237 | 588 |

The source files are cached in `sql-data-lake-builder/output/nflverse/` and the
local DuckDB file is `sql-data-lake-builder/output/sports_lake.duckdb`.

### Play-Calling Tendencies

The next local module is `sql-data-lake-builder/src/nfl_playcalling_tendency.py`,
with schema in `sql-data-lake-builder/schema/nfl_playcalling_tendency.sql`.
It is intended to derive pass rate, rush rate, red-zone calls, goal-to-go calls,
third-down calls, target concentration, and secondary-target share from PBP.

## Core Modeling Rules

### Probability

- 50% means neutral/no validated edge.
- Scores above 50% require evidence, adequate sample size, and calibration.
- 100% is reserved for deterministic data conditions, not ordinary picks.
- Every model output must include data quality, sample size, uncertainty, and
  the reason for a pass/no-bet decision.

### FIBBO Human-Performance Layer

Track season, L10, L5, and L3 windows. Classify a slump as performance, role,
matchup, health, or variance before calling it a rebound signal. Do not assume a
player is "due" without stable opportunity and a historical analogue.

### Market and EV

Normalize American odds, remove vig where both sides are available, compare the
model probability to the market probability, and calculate EV. Parlays require
correlation handling; multiplying leg probabilities is invalid for correlated
legs without testing that assumption.

### Touchdowns

For an RB 2+ touchdown market, prioritize:

```text
red-zone target share
+ goal-to-go carries/targets
+ third-down usage
+ team touchdown expectation
+ coach play-calling fingerprint
+ opponent red-zone TD allowance
+ recent role stability
+ player touchdown conversion rate
```

## Required Next Steps

1. Run the play-calling tendency builder against the cached 2023–2025 PBP.
2. Add third-down targets and red-zone target/carry features to the prop schema.
3. Build an RB 2+ touchdown probability baseline using a Poisson or negative
   binomial model, then calibrate it out of sample.
4. Add referee crew joins by `game_id` where the source provides officials.
5. Add a RotoWire export adapter and snapshot every line with `captured_at`.
6. Backtest 2023–2024, tune on 2025, and reserve 2026 for evaluation.
7. Add explicit `BET`, `WATCH`, `PASS`, and `DATA_INSUFFICIENT` states.
8. Build a React dashboard/API surface; avoid Gradio and keep model inference
   separate from ingestion.

## Handoff Prompt

> You are continuing GREAT LAKES V1. Read `GREAT_LAKES_V1_HANDOFF.md` first.
> Preserve the 2023–2025 training boundary and keep 2026 out-of-sample. Work
> from the existing DuckDB/NFLverse touchdown logs, prop-gap scanner, and
> play-calling tendency modules. The next task is to finish the tendency build,
> derive RB red-zone/goal-to-go/third-down usage, and validate an RB 2+ TD
> probability baseline. Do not scrape new sites when a structured source exists.
> Keep raw snapshots auditable, use calibrated probabilities, and return PASS
> when evidence is insufficient.

## Important Boundaries

- Do not commit credentials, `.env` files, vault files, or private model data.
- Do not upload the local DuckDB database or Parquet cache unless explicitly
  intended; use Git LFS or external private storage for large artifacts.
- Do not claim a source is live, unlimited, or production-ready without a test.
- Do not use an LLM as the numerical probability engine. Use it for extraction,
  classification, explanation, and research assistance around validated data.