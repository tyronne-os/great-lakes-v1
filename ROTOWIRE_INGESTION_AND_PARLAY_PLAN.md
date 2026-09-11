# RotoWire Ingestion and Three-Leg Parlay Plan

## Confirmation

The RotoWire board can be re-engineered into the GREAT LAKES V1 lake and used
as the market-input layer for probability scoring. The system does not need to
copy every statistic shown on the board. It needs the market rows, timestamps,
player identity, opportunity signals, and the matchup features that explain
those markets.

RotoWire remains the market discovery and prop-board source. Structured NFLverse,
ESPN, league feeds, and permitted datasets remain the historical and contextual
sources. The lake keeps the two roles separate.

## Minimal Prop Payload

Capture one immutable record per player/market/sportsbook snapshot:

```text
captured_at
season
week
game_id
player_id
player_name
team
opponent
position
market_type
selection
line
american_odds
sportsbook
projection
source_name
source_uri
```

Priority markets for the first three-leg engine:

- WR2 targets, receptions, and receiving yards
- RB rushing attempts and rushing yards
- RB anytime touchdown and 2+ touchdown
- Passing attempts and passing yards
- Defensive sacks and tackles when role data is reliable

## Context Joins

Each market snapshot is joined to features available as of the capture time:

### Opportunity

- L3, L5, L10, and season targets
- Target share and target rank
- Snap share and route share
- Rushing attempts and red-zone carries
- Goal-to-go carries and targets
- Third-down targets and touches

### Team and Coaching

- Pass rate and rush rate
- Third-down pass rate
- Red-zone pass rate
- Goal-to-go rush rate
- Secondary-target share
- Lead/trail game-script tendencies
- Running-back rotation and touchdown concentration

### Opponent

- Position-specific yards allowed
- Red-zone touchdowns allowed
- Goal-to-go touchdowns allowed
- Third-down conversion/defense
- Pressure, sack, and interception rates
- Opponent target distribution

### Market

- Best available line
- Best available price
- Opening line and current line
- Line movement
- Vig-free probability
- Projection-to-line gap
- Source freshness

## Update Operation

Use a permitted export, partner/API response, or browser-visible feed. Do not
bypass authentication, subscriptions, robots controls, or anti-bot protections.

Recommended cadence:

```text
Normal period                  every 15 minutes
News/injury window             every 5 minutes
One hour before kickoff       every 1-2 minutes
Confirmed inactive/lineup      immediate rescan
Line movement                  immediate new snapshot
```

Each pull should:

1. Create an `ingestion_runs` row.
2. Save the raw response or export reference in `raw_snapshots`.
3. Normalize rows into `silver.market_snapshots`.
4. Resolve players, teams, opponents, and games.
5. Join only features known before `captured_at`.
6. Write a feature row to `gold.model_features`.
7. Run the calibrated probability model.
8. Write a prediction and reason codes to `gold.predictions`.
9. Recheck stale lines, injuries, and role changes before displaying a pick.

## Probability Contract

Every market gets:

```text
model_probability
market_probability
vig_free_probability
expected_value
uncertainty
confidence_score
data_quality
decision
reason_codes
```

Decision values:

- `BET`: passes probability, EV, freshness, and risk thresholds
- `WATCH`: promising but waiting for price, lineup, or confirmation
- `PASS`: insufficient edge or excessive risk
- `DATA_INSUFFICIENT`: missing or stale inputs

A model score is not a guarantee. The system must be allowed to return no play.

## Three-Leg Parlay Engine

The engine must not simply choose the three highest individual scores. It should:

1. Filter out stale or incomplete markets.
2. Require a minimum single-leg edge and confidence.
3. Prefer legs from different games unless a joint model supports correlation.
4. Penalize same-game and same-script dependencies.
5. Reject legs whose role depends on an unconfirmed player status.
6. Compare combined probability against combined market price.
7. Apply a correlation penalty before ranking.
8. Return the top candidates plus rejected-leg explanations.

Example output:

```text
Leg 1: WR2 receptions UNDER
Leg 2: RB goal-line touchdown OVER
Leg 3: opposing QB passing yards UNDER

Status: WATCH
Reason: Legs 1 and 3 share a defensive game-script assumption.
Action: require joint-model validation or replace one leg.
```

## Target Probability Families

### WR2 Opportunity

The WR2 signal is strongest when:

- target rank is consistently second
- target share is rising over L3/L5
- the primary receiver draws shadow/coverage attention
- routes and snaps are stable
- opponent coverage is weak against the WR2 alignment
- the market line has not caught up to the new role

### RB 2+ Touchdowns

Use a count-based baseline such as Poisson or negative binomial, then calibrate:

```text
red-zone opportunities
+ goal-to-go carries
+ third-down usage
+ team touchdown expectation
+ coach tendency
+ opponent TD allowance
+ recent role stability
+ player conversion rate
```

### Unders

Prioritize unders when production is high but opportunity is not, when a favorite
is likely to reduce late-game volume, or when defensive and game-script features
suppress the relevant player role.

## Backtest Boundary

Training and tuning:

- Train: 2023-2024
- Tune/calibrate: 2025
- Evaluate out of sample: 2026

Do not use future line movement, final injury status, or post-kickoff information
when creating a pregame feature row. Every feature must have an `as_of_timestamp`.

## Implementation Location

Use the existing canonical schema:

- `silver.market_snapshots`
- `silver.player_target_logs`
- `silver.team_playcalling_tendencies`
- `silver.touchdown_scoring_logs`
- `silver.opponent_touchdown_logs`
- `gold.model_features`
- `gold.predictions`
- `gold.prediction_results`

The next implementation should add a RotoWire adapter and scheduler, not another
source-specific prediction table.
