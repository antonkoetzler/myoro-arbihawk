"""
SQLite database for storing fixtures, odds, scores, and settlements.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from contextlib import contextmanager
import config


class Database:
    """SQLite database manager for betting data."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Fixtures table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fixtures (
                    fixture_id TEXT PRIMARY KEY,
                    sport_id INTEGER,
                    tournament_id INTEGER,
                    tournament_name TEXT,
                    home_team_id TEXT,
                    home_team_name TEXT,
                    away_team_id TEXT,
                    away_team_name TEXT,
                    start_time TEXT,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Odds table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS odds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fixture_id TEXT,
                    bookmaker_id TEXT,
                    bookmaker_name TEXT,
                    market_id TEXT,
                    market_name TEXT,
                    outcome_id TEXT,
                    outcome_name TEXT,
                    odds_value REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fixture_id) REFERENCES fixtures(fixture_id),
                    UNIQUE(fixture_id, bookmaker_id, market_id, outcome_id)
                )
            """)
            
            # Scores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    fixture_id TEXT PRIMARY KEY,
                    home_score INTEGER,
                    away_score INTEGER,
                    status TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fixture_id) REFERENCES fixtures(fixture_id)
                )
            """)
            
            # Settlements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settlements (
                    fixture_id TEXT PRIMARY KEY,
                    home_score INTEGER,
                    away_score INTEGER,
                    status TEXT,
                    settled_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fixture_id) REFERENCES fixtures(fixture_id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_start_time ON fixtures(start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_tournament ON fixtures(tournament_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_odds_fixture ON odds(fixture_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds(bookmaker_id)")
    
    def insert_fixture(self, fixture_data: Dict[str, Any]) -> None:
        """Insert or update a fixture."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO fixtures 
                (fixture_id, sport_id, tournament_id, tournament_name,
                 home_team_id, home_team_name, away_team_id, away_team_name,
                 start_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fixture_data['fixture_id'],
                fixture_data.get('sport_id'),
                fixture_data.get('tournament_id'),
                fixture_data.get('tournament_name'),
                fixture_data.get('home_team_id'),
                fixture_data.get('home_team_name'),
                fixture_data.get('away_team_id'),
                fixture_data.get('away_team_name'),
                fixture_data.get('start_time'),
                fixture_data.get('status', 'scheduled')
            ))
    
    def insert_odds(self, fixture_id: str, odds_data: List[Dict[str, Any]]) -> None:
        """Insert odds for a fixture."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for odd in odds_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO odds
                    (fixture_id, bookmaker_id, bookmaker_name, market_id,
                     market_name, outcome_id, outcome_name, odds_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fixture_id,
                    odd.get('bookmaker_id'),
                    odd.get('bookmaker_name'),
                    odd.get('market_id'),
                    odd.get('market_name'),
                    odd.get('outcome_id'),
                    odd.get('outcome_name'),
                    odd.get('odds_value')
                ))
    
    def insert_score(self, fixture_id: str, score_data: Dict[str, Any]) -> None:
        """Insert or update a score."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO scores
                (fixture_id, home_score, away_score, status)
                VALUES (?, ?, ?, ?)
            """, (
                fixture_id,
                score_data.get('home_score'),
                score_data.get('away_score'),
                score_data.get('status')
            ))
    
    def insert_settlement(self, fixture_id: str, settlement_data: Dict[str, Any]) -> None:
        """Insert or update a settlement."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO settlements
                (fixture_id, home_score, away_score, status)
                VALUES (?, ?, ?, ?)
            """, (
                fixture_id,
                settlement_data.get('home_score'),
                settlement_data.get('away_score'),
                settlement_data.get('status')
            ))
    
    def get_fixtures(self, 
                     sport_id: Optional[int] = None,
                     tournament_id: Optional[int] = None,
                     from_date: Optional[str] = None,
                     to_date: Optional[str] = None,
                     limit: Optional[int] = None) -> pd.DataFrame:
        """Get fixtures matching criteria."""
        with self._get_connection() as conn:
            query = "SELECT * FROM fixtures WHERE 1=1"
            params = []
            
            if sport_id:
                query += " AND sport_id = ?"
                params.append(sport_id)
            
            if tournament_id:
                query += " AND tournament_id = ?"
                params.append(tournament_id)
            
            if from_date:
                query += " AND start_time >= ?"
                params.append(from_date)
            
            if to_date:
                query += " AND start_time <= ?"
                params.append(to_date)
            
            query += " ORDER BY start_time"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def get_odds(self, fixture_id: Optional[str] = None,
                 bookmaker_id: Optional[str] = None,
                 market_id: Optional[str] = None) -> pd.DataFrame:
        """Get odds matching criteria."""
        with self._get_connection() as conn:
            query = "SELECT * FROM odds WHERE 1=1"
            params = []
            
            if fixture_id:
                query += " AND fixture_id = ?"
                params.append(fixture_id)
            
            if bookmaker_id:
                query += " AND bookmaker_id = ?"
                params.append(bookmaker_id)
            
            if market_id:
                query += " AND market_id = ?"
                params.append(market_id)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def get_scores(self, fixture_id: Optional[str] = None) -> pd.DataFrame:
        """Get scores."""
        with self._get_connection() as conn:
            query = "SELECT * FROM scores WHERE 1=1"
            params = []
            
            if fixture_id:
                query += " AND fixture_id = ?"
                params.append(fixture_id)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def fixture_exists(self, fixture_id: str) -> bool:
        """Check if fixture exists in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM fixtures WHERE fixture_id = ?", (fixture_id,))
            return cursor.fetchone() is not None
    
    def get_last_fetched_date(self, tournament_id: int) -> Optional[str]:
        """Get the latest fixture date for a tournament."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(start_time) FROM fixtures 
                WHERE tournament_id = ?
            """, (tournament_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else None

