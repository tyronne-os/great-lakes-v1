# 🔗 Tank01 RapidAPI Integration Setup

**Purpose:** Bootstrap the data lake with Tank01 during development  
**Timeline:** Weeks 1-2 (replacement with free sources in Weeks 5-8)  
**Cost:** $0 (you have developer account)  
**Status:** 🟢 Ready to Integrate

---

## 1️⃣ TANK01 API CREDENTIALS

### Get Your API Key

1. Visit: https://rapidapi.com/tank01/api/tank01-nfl-live-in-game-real-time-statistics-nfl
2. Subscribe to **Free Tier** (3,000 calls/month)
3. Copy your API key from dashboard
4. Add to vault:

```bash
echo "TANK01_RAPIDAPI_KEY=your_api_key_here" >> /vault/.env.production
chmod 600 /vault/.env.production
```

### Verify Connectivity

```bash
curl --request GET \
  --url 'https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLBettingOdds?gameDate=20260907&itemFormat=list&impliedTotals=true&playerProps=true' \
  --header 'Content-Type: application/json' \
  --header 'x-rapidapi-host: tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com' \
  --header 'x-rapidapi-key: YOUR_KEY_HERE'
```

---

## 2️⃣ TANK01 ENDPOINTS (Bootstrap Phase)

### Endpoint 1: /getNFLBettingOdds
```
GET /getNFLBettingOdds
Params:
  - gameDate: YYYYMMDD (e.g., 20260907)
  - itemFormat: "list" or "json"
  - impliedTotals: true/false
  - playerProps: true/false

Returns: Multi-sportsbook spreads, totals, moneylines
Example Sportsbooks: DraftKings, FanDuel, BetMGM, Caesars

Response:
{
  "status": 200,
  "sportsbook_count": 4,
  "games": [
    {
      "gameID": "2026090710",
      "matchup": "KC@BAL",
      "bookmakers": {
        "draftkings": {
          "spread": -3.5,
          "spreadOdds": -110,
          "moneyline": -165,
          "overUnder": 47.5
        },
        "fanduel": {
          "spread": -3.5,
          "spreadOdds": -105,
          "moneyline": -160,
          "overUnder": 47.0
        }
        // ... BetMGM, Caesars
      }
    }
  ]
}
```

### Endpoint 2: /getNFLPlayerProps
```
GET /getNFLPlayerProps
Params:
  - gameID: Game identifier
  - playerID: (optional) specific player
  - statType: "passing_yards", "rushing_yards", "receiving_yards", "points"

Returns: Player prop over/under lines
Example Response:
{
  "status": 200,
  "props": [
    {
      "playerID": "3139477",
      "name": "Patrick Mahomes",
      "market": "Passing Yards",
      "overLine": 268.5,
      "underLine": 268.5,
      "overOdds": -115,
      "underOdds": -105,
      "sportsbooks": {
        "draftkings": {...},
        "fanduel": {...}
      }
    }
  ]
}
```

---

## 3️⃣ TANK01 DATA SCHEMA (For SQL Agent)

### Tables to Create (PostgreSQL)

```sql
-- Bronze Layer: Raw Tank01 data (as-is from API)
CREATE TABLE tank01_betting_odds_raw (
    ingestion_id SERIAL PRIMARY KEY,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    game_date DATE,
    game_id STRING,
    matchup STRING,
    home_team STRING,
    away_team STRING,
    sportsbook_name STRING,
    spread FLOAT,
    spread_odds INT,
    moneyline INT,
    over_under FLOAT,
    raw_json JSONB
);

CREATE TABLE tank01_player_props_raw (
    ingestion_id SERIAL PRIMARY KEY,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    game_id STRING,
    player_id INT,
    player_name STRING,
    market_type STRING,  -- 'passing_yards', 'rushing_yards', etc.
    over_line FLOAT,
    under_line FLOAT,
    over_odds INT,
    under_odds INT,
    sportsbook_name STRING,
    raw_json JSONB
);

-- Silver Layer: Normalized Tank01 data
CREATE TABLE sportsbook_consensus_odds (
    game_id STRING,
    game_date DATE,
    home_team STRING,
    away_team STRING,
    market_type STRING,  -- 'spread', 'moneyline', 'over_under'
    consensus_line FLOAT,
    min_line FLOAT,
    max_line FLOAT,
    avg_odds INT,
    num_sportsbooks INT,
    PRIMARY KEY (game_id, market_type)
);

CREATE TABLE player_props_consensus (
    player_id INT,
    player_name STRING,
    game_id STRING,
    market_type STRING,
    consensus_over_line FLOAT,
    consensus_under_line FLOAT,
    avg_over_odds INT,
    avg_under_odds INT,
    num_sportsbooks INT,
    PRIMARY KEY (player_id, game_id, market_type)
);

-- Gold Layer: Edges + Predictions
CREATE TABLE sportsbook_edges (
    edge_id SERIAL PRIMARY KEY,
    game_id STRING,
    game_date DATE,
    market_type STRING,
    sportsbook_line FLOAT,
    model_prediction FLOAT,
    model_confidence FLOAT,
    edge_pct FLOAT,  -- (model - implied) * 100
    kelly_fraction FLOAT,
    recommended_wager FLOAT,
    edge_direction STRING,  -- 'OVER', 'UNDER', 'MONEYLINE'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4️⃣ PYTHON CLIENT (Tank01 + FastAPI)

### Installation
```bash
pip install httpx asyncio
```

### Client Code (Already in main.py)
```python
class Tank01Ingester:
    BASE_URL = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
        }
    
    async def fetch_betting_odds(self, game_date: str = None) -> dict:
        """Fetch /getNFLBettingOdds data"""
        # Implementation in main.py
        pass
    
    async def fetch_player_props(self, game_id: str = None) -> dict:
        """Fetch /getNFLPlayerProps data"""
        # Implementation in main.py
        pass
```

---

## 5️⃣ FASTAPI ENDPOINTS (Pre-configured)

### Running the Server
```bash
pip install fastapi uvicorn
cd /home/hunt/Downloads/FOR\ SQL
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Endpoints
```bash
# Test 1: Get sportsbook odds (Tank01 bootstrap)
curl -X GET "http://localhost:8000/v1/odds/sportsbooks" \
     -H "x-frontal-key: fl_live_99a8b7c6d5e4f321"

# Test 2: Get player props
curl -X GET "http://localhost:8000/v1/props/player-lines?game_id=2026090710" \
     -H "x-frontal-key: fl_live_99a8b7c6d5e4f321"

# Test 3: Get parlay master slip
curl -X GET "http://localhost:8000/v1/parlay-master/daily-slip?bankroll_profit=250.00" \
     -H "x-frontal-key: fl_live_99a8b7c6d5e4f321"

# Test 4: Get data lake health
curl -X GET "http://localhost:8000/v1/data-lake/health" \
     -H "x-frontal-key: fl_live_99a8b7c6d5e4f321"
```

### API Documentation
```
Interactive Swagger UI: http://localhost:8000/docs
ReDoc UI: http://localhost:8000/redoc
```

---

## 6️⃣ SQL AGENT INVESTIGATION PROTOCOL

### What SQL Agent Should Do

1. **Reverse-Engineer Tank01 Schema**
   ```sql
   -- Analyze raw Tank01 data structure
   SELECT DISTINCT market_type, COUNT(*) as record_count
   FROM tank01_betting_odds_raw
   GROUP BY market_type;
   
   -- Identify sportsbook patterns
   SELECT sportsbook_name, AVG(spread_odds) as avg_odds
   FROM tank01_betting_odds_raw
   GROUP BY sportsbook_name;
   ```

2. **Identify Schema Transformation Rules**
   ```sql
   -- Find consensus line calculation
   SELECT 
       game_id,
       AVG(spread) as consensus_spread,
       MIN(spread) as min_spread,
       MAX(spread) as max_spread
   FROM tank01_betting_odds_raw
   WHERE sportsbook_name IN ('draftkings', 'fanduel', 'betmgm', 'caesars')
   GROUP BY game_id;
   ```

3. **Build Silver Layer Views**
   ```sql
   -- Create normalized view for downstream
   CREATE VIEW sportsbook_consensus_normalized AS
   SELECT 
       game_id,
       game_date,
       market_type,
       AVG(spread)::FLOAT as consensus_line,
       MIN(spread_odds) as min_odds,
       MAX(spread_odds) as max_odds,
       COUNT(DISTINCT sportsbook_name) as num_books
   FROM tank01_betting_odds_raw
   GROUP BY game_id, game_date, market_type;
   ```

4. **Document Edge Detection Formula**
   ```
   Edge % = (Model Predicted Probability - Implied Odds Probability) * 100
   
   Example:
   - DraftKings spreads team at -3.5 (implied 58% win prob)
   - Your model evaluates team at 74% win prob
   - Edge = (0.74 - 0.58) * 100 = +16% positive expected value
   ```

5. **Build Gold Layer for Predictions**
   ```sql
   INSERT INTO sportsbook_edges (
       game_id, market_type, sportsbook_line, 
       model_prediction, edge_pct, edge_direction
   )
   SELECT 
       sc.game_id,
       sc.market_type,
       sc.consensus_line,
       mp.model_prediction,
       ((mp.model_prediction - sc.consensus_line) * 100) as edge_pct,
       CASE WHEN (mp.model_prediction - sc.consensus_line) > 0 THEN 'OVER' 
            ELSE 'UNDER' END as edge_direction
   FROM sportsbook_consensus_normalized sc
   JOIN model_predictions mp 
       ON sc.game_id = mp.game_id;
   ```

---

## 7️⃣ MIGRATION TIMELINE: Tank01 → Free Sources

### Week 1-2: Bootstrap with Tank01
```
Tank01 RapidAPI → PostgreSQL Bronze Layer
├─ Ingest: /getNFLBettingOdds
├─ Ingest: /getNFLPlayerProps
└─ Load: Football Prophet FastAPI endpoints
```

### Week 3-4: Schema Reverse-Engineering (SQL Agent)
```
SQL Agent investigates:
├─ Tank01 table structure
├─ Consensus odds calculation
├─ Player props normalization
├─ Edge detection formulas
└─ Document: Silver → Gold layer transformation
```

### Week 5-8: Free Source Integration (Parallel)
```
Replace Tank01 with:
├─ ESPN Hidden API (sportsbook odds directly)
├─ Sleeper API (player props + ADP)
├─ Baseball Savant (heatmap + edge zones)
├─ NFLverse (play-by-play context)
└─ Others (nba_api, StatsAPI, SportsReference, pybaseball)
```

### Week 9+: Tank01 Deprecation
```
Once free sources validated:
├─ Remove Tank01 API calls
├─ Archive historical Tank01 data
├─ Redirect endpoints to free sources
└─ Cost: $0/month (from $0 to $0 - no change, but dependency removed)
```

---

## 8️⃣ COST ANALYSIS

### Tank01 RapidAPI Pricing
```
Free Tier: 3,000 calls/month
├─ /getNFLBettingOdds: ~30 games/day * 7 days = 210 calls/week
├─ /getNFLPlayerProps: ~500 props/day * 7 days = 3,500 calls/week
├─ Total: ~3,710 calls/week = ~15,000 calls/month (EXCEEDS FREE TIER)

Pro Tier: $29.99/month
├─ 100,000 calls/month
├─ Recommended for continuous polling

Alternative: Use Free Tier strategically
├─ Ingest only during market hours (Thu-Mon, 9am-11pm)
├─ Cache results in PostgreSQL
├─ Reduce redundant calls
├─ Total: ~3,000 calls/month (within free tier)
```

### Long-Term Cost (Free Sources)
```
All 8 free sources:
├─ NFLverse: $0 (library)
├─ nba_api: $0 (free API)
├─ Baseball Savant: $0 (official MLB)
├─ ESPN Hidden API: $0 (no auth)
├─ Sleeper: $0 (free API)
├─ StatsAPI: $0 (official MLB)
├─ SportsReference: $0 (HTML parsing)
├─ pybaseball: $0 (aggregator)
├─ TOTAL: $0/month
```

---

## 9️⃣ TESTING CHECKLIST

- [ ] Tank01 API key configured in `/vault/.env.production`
- [ ] `main.py` FastAPI server running on localhost:8000
- [ ] `/v1/odds/sportsbooks` endpoint returns mock data (or Tank01 data if key valid)
- [ ] `/v1/props/player-lines` endpoint returns player props
- [ ] `/v1/parlay-master/daily-slip` endpoint returns bankroll strategy
- [ ] `/v1/data-lake/health` endpoint shows all sources ready
- [ ] PostgreSQL tables created (bronze, silver, gold layers)
- [ ] SQL Agent can query Tank01 raw data
- [ ] Odds Normalizer correctly converts American → Implied %
- [ ] Edge detection calculates kelly fraction correctly
- [ ] API documentation at /docs shows all endpoints

---

## 🔟 NEXT STEPS

1. ✅ Get Tank01 API key from RapidAPI
2. ✅ Add to `/vault/.env.production`
3. ✅ Run `uvicorn main:app --reload`
4. ✅ Test endpoints with provided curl commands
5. ✅ Create PostgreSQL tables (bronze/silver/gold)
6. ✅ Let SQL Agent investigate Tank01 schema
7. ✅ Document transformation rules
8. ✅ Begin Week 3: Free source integration

---

**Tank01 is your bootstrap layer. Once free sources are validated, it becomes optional.**

**Timeline: 2 weeks bootstrap → 6 weeks free source build → Cost: $0 ongoing**
