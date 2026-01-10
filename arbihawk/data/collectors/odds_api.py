"""
ODDS-API collector using RapidAPI.
"""

import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
import config
from ..database import Database


class ODDSAPICollector:
    """Collects data from RapidAPI ODDS-API."""
    
    BASE_URL = "https://odds-api1.p.rapidapi.com"
    
    def __init__(self, db: Optional[Database] = None):
        self.api_key = config.ODDS_API_KEY
        if not self.api_key:
            raise ValueError("ODDS_API_KEY not found in environment variables")
        
        self.db = db or Database()
        self.session = requests.Session()
        self.session.headers.update({
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'odds-api1.p.rapidapi.com'
        })
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests to avoid rate limits
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API request with rate limiting."""
        # Rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params or {}, timeout=10)
            self.request_count += 1
            self.last_request_time = time.time()
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error: {e}")
        
        if response.status_code == 429:
            # Rate limited - wait longer and retry once
            wait_time = 5  # Wait 5 seconds for rate limit
            time.sleep(wait_time)
            response = self.session.get(url, params=params or {}, timeout=10)
            self.request_count += 1
            self.last_request_time = time.time()
            
            # If still rate limited, raise error
            if response.status_code == 429:
                raise ValueError(
                    "Rate limit exceeded. Please wait a few minutes before trying again.\n"
                    "Consider reducing the number of fixtures or increasing delays between requests."
                )
        
        # Handle errors with better messages
        if response.status_code == 403:
            error_msg = "403 Forbidden"
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_msg = error_data['message']
            except:
                error_msg = "API subscription issue"
            
            raise ValueError(
                f"API Error: {error_msg}\n\n"
                f"To fix this:\n"
                f"1. Go to https://rapidapi.com/hub\n"
                f"2. Search for 'ODDS-API' (by RapidAPI)\n"
                f"3. Subscribe to a plan (Basic/Pro/Ultra)\n"
                f"4. Make sure your API key matches the subscription\n"
                f"5. Wait a few minutes after subscribing for activation"
            )
        elif response.status_code == 401:
            raise ValueError(
                "401 Unauthorized - Invalid API key\n"
                "Please check your ODDS_API_KEY in the .env file"
            )
        
        response.raise_for_status()
        
        try:
            return response.json()
        except ValueError:
            raise ValueError(f"Invalid JSON response from API: {response.text[:200]}")
    
    def get_sports(self) -> List[Dict[str, Any]]:
        """Get list of available sports."""
        data = self._make_request("/sports")
        # Handle both direct list response and wrapped response
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data:
            return data['data']
        else:
            return []
    
    def get_soccer_sport_id(self) -> Optional[int]:
        """Get soccer/football sport ID."""
        sports = self.get_sports()
        for sport in sports:
            # Check slug (most reliable)
            if sport.get('slug') == 'soccer':
                return sport.get('sportId')
            # Check sportName as fallback
            if 'soccer' in sport.get('sportName', '').lower():
                return sport.get('sportId')
        return None
    
    def get_tournaments(self, sport_id: int) -> List[Dict[str, Any]]:
        """Get tournaments for a sport."""
        data = self._make_request("/tournaments", params={'sportId': sport_id})
        return data.get('data', [])
    
    def get_fixtures(self, sport_id: int, from_date: str, to_date: str,
                    tournament_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """Get fixtures for a sport and date range (max 10 days)."""
        params = {
            'sportId': sport_id,
            'from': from_date,
            'to': to_date
        }
        if tournament_ids:
            params['tournamentIds'] = ','.join(map(str, tournament_ids))
        
        data = self._make_request("/fixtures", params=params)
        # Handle both direct list response and wrapped response
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data:
            return data['data']
        else:
            return []
    
    def get_odds(self, fixture_id: str, bookmakers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get odds for a fixture."""
        params = {'fixtureId': fixture_id}
        if bookmakers:
            params['bookmakers'] = ','.join(bookmakers)
        
        data = self._make_request("/odds", params=params)
        return data.get('data', {})
    
    def get_scores(self, fixture_id: str) -> Dict[str, Any]:
        """Get scores for a fixture."""
        data = self._make_request("/scores", params={'fixtureId': fixture_id})
        return data.get('data', {})
    
    def get_settlements(self, fixture_id: str) -> Dict[str, Any]:
        """Get settlements for a fixture."""
        data = self._make_request("/settlements", params={'fixtureId': fixture_id})
        return data.get('data', {})
    
    def _parse_fixture(self, fixture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse fixture data into database format."""
        # Map statusId to status string (3 = scheduled, 4 = live, 5 = finished, etc.)
        status_map = {
            3: 'scheduled',
            4: 'live',
            5: 'finished',
            6: 'cancelled',
            7: 'postponed'
        }
        status_id = fixture_data.get('statusId', 3)
        status = status_map.get(status_id, 'scheduled')
        
        return {
            'fixture_id': fixture_data.get('fixtureId'),
            'sport_id': fixture_data.get('sportId'),
            'tournament_id': fixture_data.get('tournamentId'),
            'tournament_name': fixture_data.get('tournamentName'),
            'home_team_id': str(fixture_data.get('participant1Id', '')),
            'home_team_name': fixture_data.get('participant1Name', ''),
            'away_team_id': str(fixture_data.get('participant2Id', '')),
            'away_team_name': fixture_data.get('participant2Name', ''),
            'start_time': fixture_data.get('startTime'),
            'status': status
        }
    
    def _parse_odds(self, odds_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse odds data into database format."""
        odds_list = []
        bookmakers = odds_data.get('bookmakers', [])
        
        for bookmaker in bookmakers:
            bookmaker_id = bookmaker.get('id')
            bookmaker_name = bookmaker.get('name')
            markets = bookmaker.get('markets', [])
            
            for market in markets:
                market_id = market.get('id')
                market_name = market.get('name')
                outcomes = market.get('outcomes', [])
                
                for outcome in outcomes:
                    odds_list.append({
                        'bookmaker_id': bookmaker_id,
                        'bookmaker_name': bookmaker_name,
                        'market_id': market_id,
                        'market_name': market_name,
                        'outcome_id': outcome.get('id'),
                        'outcome_name': outcome.get('name'),
                        'odds_value': outcome.get('price')
                    })
        
        return odds_list
    
    def collect_fixtures(self, sport_id: int, from_date: str, to_date: str,
                        tournament_ids: Optional[List[int]] = None,
                        incremental: bool = True) -> int:
        """Collect fixtures and store in database."""
        collected = 0
        
        # Split date range into 10-day chunks (API limit)
        start = parse_date(from_date)
        end = parse_date(to_date)
        current = start
        
        while current <= end:
            chunk_end = min(current + timedelta(days=10), end)
            from_str = current.strftime('%Y-%m-%d')
            to_str = chunk_end.strftime('%Y-%m-%d')
            
            try:
                fixtures = self.get_fixtures(sport_id, from_str, to_str, tournament_ids)
                
                for fixture_data in fixtures:
                    fixture = self._parse_fixture(fixture_data)
                    fixture_id = fixture['fixture_id']
                    
                    # Skip if exists and incremental mode
                    if incremental and self.db.fixture_exists(fixture_id):
                        continue
                    
                    self.db.insert_fixture(fixture)
                    collected += 1
                
                current = chunk_end + timedelta(days=1)
            except Exception as e:
                print(f"Error collecting fixtures for {from_str} to {to_str}: {e}")
                current = chunk_end + timedelta(days=1)
                continue
        
        return collected
    
    def collect_odds(self, fixture_id: str, bookmakers: Optional[List[str]] = None) -> bool:
        """Collect odds for a fixture."""
        try:
            odds_data = self.get_odds(fixture_id, bookmakers)
            if not odds_data:
                return False
            
            odds_list = self._parse_odds(odds_data)
            if odds_list:
                self.db.insert_odds(fixture_id, odds_list)
                return True
        except Exception as e:
            print(f"Error collecting odds for fixture {fixture_id}: {e}")
        
        return False
    
    def collect_scores(self, fixture_id: str) -> bool:
        """Collect scores for a fixture."""
        try:
            score_data = self.get_scores(fixture_id)
            if not score_data:
                return False
            
            self.db.insert_score(fixture_id, {
                'home_score': score_data.get('homeScore'),
                'away_score': score_data.get('awayScore'),
                'status': score_data.get('status')
            })
            return True
        except Exception as e:
            print(f"Error collecting scores for fixture {fixture_id}: {e}")
        
        return False
    
    def collect_settlements(self, fixture_id: str) -> bool:
        """Collect settlements for a fixture."""
        try:
            settlement_data = self.get_settlements(fixture_id)
            if not settlement_data:
                return False
            
            self.db.insert_settlement(fixture_id, {
                'home_score': settlement_data.get('homeScore'),
                'away_score': settlement_data.get('awayScore'),
                'status': settlement_data.get('status')
            })
            return True
        except Exception as e:
            print(f"Error collecting settlements for fixture {fixture_id}: {e}")
        
        return False

