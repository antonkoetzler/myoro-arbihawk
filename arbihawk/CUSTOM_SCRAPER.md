# Custom Scraper Requirements

This document outlines the essential data you need to scrape for the betting prediction system. Only include data that is actually used for training and prediction.

## Terminology

- **Fixture**: A scheduled match/game between two teams
- **Odds**: The betting price for an outcome (e.g., 2.10 means bet $1 to win $2.10)
- **Market**: A type of bet (e.g., 1x2, over/under, btts)
- **Outcome**: A specific result you can bet on (e.g., "Home win", "Over 2.5 goals")
- **Bookmaker**: A betting company (e.g., Bet365, Pinnacle)
- **BTTS**: Both Teams To Score (betting on whether both teams score)
- **Over/Under**: Betting on total goals above/below a threshold (usually 2.5)
- **Decimal odds**: Odds format where 2.10 = bet $1 to win $2.10 total

## Essential Data to Scrape

### 1. Fixtures (Matches)

**What you need:**

- Unique match identifier
- Home team identifier and name
- Away team identifier and name
- Match start date/time
- Match status (to identify completed matches)

**Required Fields:**

```python
{
    'fixture_id': str,           # Unique identifier (e.g., "12345")
    'home_team_id': str,          # Team identifier (e.g., "team_123")
    'home_team_name': str,        # Team name (e.g., "Arsenal")
    'away_team_id': str,          # Team identifier (e.g., "team_456")
    'away_team_name': str,        # Team name (e.g., "Chelsea")
    'start_time': str,            # ISO datetime (e.g., "2024-01-15T15:00:00Z")
    'status': str                 # 'scheduled', 'live', 'finished', 'cancelled', 'postponed'
}
```

**Why needed:**

- Fixtures are the base data structure
- Team IDs are used to calculate form, head-to-head, and home/away performance
- Start time is used to filter matches by date
- Status is used to identify completed matches (for training)

**Example snippet:**

```python
def get_fixtures(self, from_date: str, to_date: str) -> List[Dict]:
    """Get fixtures in date range."""
    # Your scraping logic here
    return [
        {
            'fixture_id': 'match_123',
            'home_team_id': 'arsenal',
            'home_team_name': 'Arsenal',
            'away_team_id': 'chelsea',
            'away_team_name': 'Chelsea',
            'start_time': '2024-01-15T15:00:00Z',
            'status': 'finished'
        }
    ]
```

---

### 2. Scores (Match Results)

**What you need:**

- Match identifier (to link to fixture)
- Home team score
- Away team score
- Match status

**Required Fields:**

```python
{
    'fixture_id': str,            # Must match fixture_id from fixtures
    'home_score': int,            # Home team goals (e.g., 2)
    'away_score': int,           # Away team goals (e.g., 1)
    'status': str                # Usually 'finished' for completed matches
}
```

**Why needed:**

- Scores are used to create training labels (home_win/draw/away_win, over/under, btts)
- Scores are used to calculate team form, head-to-head stats, and home/away performance
- Only needed for completed matches (status = 'finished')

**Example snippet:**

```python
def get_scores(self, fixture_id: str) -> Dict:
    """Get final score for a completed match."""
    # Your scraping logic here
    return {
        'fixture_id': 'match_123',
        'home_score': 2,
        'away_score': 1,
        'status': 'finished'
    }
```

---

### 3. Odds (Betting Odds)

**What you need:**

- Match identifier (to link to fixture)
- Bookmaker identifier and name
- Market type (1x2, over_under, btts)
- Outcome identifier and name
- Odds value (decimal format)

**Required Fields:**

```python
{
    'fixture_id': str,            # Must match fixture_id from fixtures
    'bookmaker_id': str,          # Bookmaker identifier (e.g., "bet365")
    'bookmaker_name': str,        # Bookmaker name (e.g., "Bet365")
    'market_id': str,             # Market type: '1x2', 'over_under', 'btts'
    'market_name': str,           # Market display name (e.g., "1X2", "Over/Under")
    'outcome_id': str,            # Outcome identifier (e.g., "1", "over_2.5", "yes")
    'outcome_name': str,          # Outcome name (e.g., "Home", "Over 2.5", "Yes")
    'odds_value': float           # Decimal odds (e.g., 2.10)
}
```

**Market Types:**

**1x2 Market:**

```python
{
    'market_id': '1x2',
    'market_name': '1X2',
    'outcome_id': '1',      # or 'X' or '2'
    'outcome_name': 'Home', # or 'Draw' or 'Away'
    'odds_value': 2.10
}
```

**Over/Under Market:**

```python
{
    'market_id': 'over_under',
    'market_name': 'Over/Under',
    'outcome_id': 'over_2.5',  # or 'under_2.5'
    'outcome_name': 'Over 2.5', # or 'Under 2.5'
    'odds_value': 1.85
}
```

**Both Teams To Score (BTTS) Market:**

```python
{
    'market_id': 'btts',
    'market_name': 'Both Teams To Score',
    'outcome_id': 'yes',   # or 'no'
    'outcome_name': 'Yes', # or 'No'
    'odds_value': 1.70
}
```

**Why needed:**

- Odds are used as features in the model (average odds, odds spread)
- Odds are used to calculate expected value for value betting
- Multiple bookmakers allow finding the best odds

**Example snippet:**

```python
def get_odds(self, fixture_id: str) -> List[Dict]:
    """Get odds for a fixture from multiple bookmakers."""
    # Your scraping logic here
    return [
        {
            'fixture_id': 'match_123',
            'bookmaker_id': 'bet365',
            'bookmaker_name': 'Bet365',
            'market_id': '1x2',
            'market_name': '1X2',
            'outcome_id': '1',
            'outcome_name': 'Home',
            'odds_value': 2.10
        },
        {
            'fixture_id': 'match_123',
            'bookmaker_id': 'bet365',
            'bookmaker_name': 'Bet365',
            'market_id': '1x2',
            'market_name': '1X2',
            'outcome_id': 'X',
            'outcome_name': 'Draw',
            'odds_value': 3.50
        },
        # ... more outcomes
    ]
```

---

## Data Relationships

```
Fixture (1) ──→ (N) Scores      (One fixture has one score when finished)
Fixture (1) ──→ (N) Odds         (One fixture has many odds from different bookmakers/markets)
```

**Key Points:**

- `fixture_id` is the primary key linking all data
- Team IDs must be consistent across fixtures (same team = same ID)
- Only scrape scores for matches with `status = 'finished'`
- Odds can be scraped for any fixture (scheduled, live, or finished)

---

## What You DON'T Need to Scrape

These were only needed because of ODDS-API's structure, but aren't used by the system:

- ❌ **Sports list** - Not used (soccer is hardcoded)
- ❌ **Tournaments list** - Not used in features or training
- ❌ **Tournament IDs/names** - Not used in features
- ❌ **Sport IDs** - Not used in features
- ❌ **Settlements** - Not used (scores are sufficient)
- ❌ **Participant IDs** - Only team IDs/names are needed

---

## Integration Points

Your scraper should implement these methods to match the existing interface:

```python
class YourCustomScraper:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
    
    def collect_fixtures(self, from_date: str, to_date: str, 
                        incremental: bool = True) -> int:
        """Collect fixtures and store in database."""
        # 1. Scrape fixtures using get_fixtures()
        # 2. Parse into database format
        # 3. Store using self.db.insert_fixture()
        pass
    
    def collect_odds(self, fixture_id: str, 
                    bookmakers: Optional[List[str]] = None) -> bool:
        """Collect odds for a fixture."""
        # 1. Scrape odds using get_odds()
        # 2. Parse into database format
        # 3. Store using self.db.insert_odds()
        pass
    
    def collect_scores(self, fixture_id: str) -> bool:
        """Collect scores for a completed fixture."""
        # 1. Scrape scores using get_scores()
        # 2. Parse into database format
        # 3. Store using self.db.insert_score()
        pass
```

**Database Methods Available:**

```python
self.db.insert_fixture(fixture_data: Dict)
self.db.insert_odds(fixture_id: str, odds_list: List[Dict])
self.db.insert_score(fixture_id: str, score_data: Dict)
```

---

## Data Format Examples

### Complete Example: One Match

**Fixture:**

```python
{
    'fixture_id': 'match_12345',
    'home_team_id': 'arsenal',
    'home_team_name': 'Arsenal',
    'away_team_id': 'chelsea',
    'away_team_name': 'Chelsea',
    'start_time': '2024-01-15T15:00:00Z',
    'status': 'finished'
}
```

**Score (if finished):**

```python
{
    'fixture_id': 'match_12345',
    'home_score': 2,
    'away_score': 1,
    'status': 'finished'
}
```

**Odds (multiple entries per fixture):**

```python
[
    # 1x2 market from Bet365
    {
        'fixture_id': 'match_12345',
        'bookmaker_id': 'bet365',
        'bookmaker_name': 'Bet365',
        'market_id': '1x2',
        'market_name': '1X2',
        'outcome_id': '1',
        'outcome_name': 'Home',
        'odds_value': 2.10
    },
    {
        'fixture_id': 'match_12345',
        'bookmaker_id': 'bet365',
        'bookmaker_name': 'Bet365',
        'market_id': '1x2',
        'market_name': '1X2',
        'outcome_id': 'X',
        'outcome_name': 'Draw',
        'odds_value': 3.50
    },
    {
        'fixture_id': 'match_12345',
        'bookmaker_id': 'bet365',
        'bookmaker_name': 'Bet365',
        'market_id': '1x2',
        'market_name': '1X2',
        'outcome_id': '2',
        'outcome_name': 'Away',
        'odds_value': 3.20
    },
    # Over/Under market
    {
        'fixture_id': 'match_12345',
        'bookmaker_id': 'bet365',
        'bookmaker_name': 'Bet365',
        'market_id': 'over_under',
        'market_name': 'Over/Under',
        'outcome_id': 'over_2.5',
        'outcome_name': 'Over 2.5',
        'odds_value': 1.85
    },
    {
        'fixture_id': 'match_12345',
        'bookmaker_id': 'bet365',
        'bookmaker_name': 'Bet365',
        'market_id': 'over_under',
        'market_name': 'Over/Under',
        'outcome_id': 'under_2.5',
        'outcome_name': 'Under 2.5',
        'odds_value': 1.95
    },
    # BTTS market
    {
        'fixture_id': 'match_12345',
        'bookmaker_id': 'bet365',
        'bookmaker_name': 'Bet365',
        'market_id': 'btts',
        'market_name': 'Both Teams To Score',
        'outcome_id': 'yes',
        'outcome_name': 'Yes',
        'odds_value': 1.70
    },
    {
        'fixture_id': 'match_12345',
        'bookmaker_id': 'bet365',
        'bookmaker_name': 'Bet365',
        'market_id': 'btts',
        'market_name': 'Both Teams To Score',
        'outcome_id': 'no',
        'outcome_name': 'No',
        'odds_value': 2.10
    }
]
```

---

## Summary Checklist

**Essential Data:**

- [ ] **Fixtures**: fixture_id, home_team_id, home_team_name, away_team_id, away_team_name, start_time, status
- [ ] **Scores**: fixture_id, home_score, away_score, status (only for finished matches)
- [ ] **Odds**: fixture_id, bookmaker_id, bookmaker_name, market_id, market_name, outcome_id, outcome_name, odds_value

**Markets to Support:**

- [ ] 1x2 (Home/Draw/Away)
- [ ] Over/Under 2.5 goals
- [ ] Both Teams To Score (Yes/No)

**Implementation:**

- [ ] Implement `collect_fixtures()` method
- [ ] Implement `collect_odds()` method
- [ ] Implement `collect_scores()` method
- [ ] Use database methods to store data
- [ ] Ensure team IDs are consistent across fixtures
