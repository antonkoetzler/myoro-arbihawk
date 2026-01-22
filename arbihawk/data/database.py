"""
SQLite database for storing fixtures, odds, scores, and betting data.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from contextlib import contextmanager
import config


class Database:
    """SQLite database manager for betting data."""
    
    SCHEMA_VERSION = 4  # Increment when schema changes
    
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
            
            # Schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Ensure migrations run before any other operations
            self._run_migrations(cursor)
            
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
            
            # Ingestion metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    records_count INTEGER DEFAULT 0,
                    checksum TEXT,
                    validation_status TEXT,
                    errors TEXT,
                    dismissed INTEGER DEFAULT 0
                )
            """)
            
            # Dismissed errors table (for tracking dismissed log errors)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dismissed_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_key TEXT NOT NULL UNIQUE,
                    error_type TEXT NOT NULL,
                    dismissed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Bet settlements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bet_settlements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fixture_id TEXT NOT NULL,
                    market_id TEXT,
                    outcome_id TEXT,
                    settled_outcome TEXT,
                    settled_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fixture_id) REFERENCES fixtures(fixture_id),
                    UNIQUE(fixture_id, market_id, outcome_id)
                )
            """)
            
            # Bet history table (for fake money system)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bet_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fixture_id TEXT NOT NULL,
                    market_id TEXT,
                    market_name TEXT,
                    outcome_id TEXT,
                    outcome_name TEXT,
                    odds REAL NOT NULL,
                    stake REAL NOT NULL,
                    placed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    settled_at TEXT,
                    result TEXT DEFAULT 'pending',
                    payout REAL DEFAULT 0,
                    FOREIGN KEY (fixture_id) REFERENCES fixtures(fixture_id)
                )
            """)
            
            # Model versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT NOT NULL,
                    model_path TEXT NOT NULL,
                    trained_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    training_samples INTEGER DEFAULT 0,
                    cv_score REAL,
                    is_active INTEGER DEFAULT 0,
                    performance_metrics TEXT
                )
            """)
            
            # Metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_start_time ON fixtures(start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_tournament ON fixtures(tournament_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_teams_time ON fixtures(home_team_name, away_team_name, start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_odds_fixture ON odds(fixture_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds(bookmaker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_fixture ON scores(fixture_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_settlements_fixture_market ON bet_settlements(fixture_id, market_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bet_history_fixture ON bet_history(fixture_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bet_history_result ON bet_history(result)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_market ON model_versions(market)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(market, is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type_time ON metrics(metric_type, timestamp)")
            
            # Record schema version
            cursor.execute("""
                INSERT OR IGNORE INTO schema_version (version) VALUES (?)
            """, (self.SCHEMA_VERSION,))
            
            # Run migrations
            self._run_migrations(cursor)
    
    def _run_migrations(self, cursor):
        """Run database migrations based on schema version."""
        # Get current schema version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()
        current_version = result[0] if result[0] is not None else 0
        
        # Migration 3: Add model_market column to bet_history
        if current_version < 3:
            try:
                # Check if column already exists
                cursor.execute("PRAGMA table_info(bet_history)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'model_market' not in columns:
                    cursor.execute("ALTER TABLE bet_history ADD COLUMN model_market TEXT")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bet_history_model_market ON bet_history(model_market)")
            except sqlite3.OperationalError as e:
                # Column might already exist, ignore
                if "duplicate column name" not in str(e).lower():
                    raise
        
        # Migration 4: Add dismissed column to ingestion_metadata
        # Always check if column exists, regardless of schema version (handles cases where version was set but migration didn't run)
        try:
            cursor.execute("PRAGMA table_info(ingestion_metadata)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'dismissed' not in columns:
                cursor.execute("ALTER TABLE ingestion_metadata ADD COLUMN dismissed INTEGER DEFAULT 0")
                # Only update version if we actually added the column
                if current_version < 4:
                    cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (4,))
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
        
        # Update schema version after migrations (if not already at target version)
        if current_version < self.SCHEMA_VERSION:
            cursor.execute("SELECT COUNT(*) FROM schema_version WHERE version = ?", (self.SCHEMA_VERSION,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
    
    # =========================================================================
    # FIXTURE OPERATIONS
    # =========================================================================
    
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
    
    def insert_fixtures_batch(self, fixtures: List[Dict[str, Any]]) -> int:
        """Insert multiple fixtures in a batch."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for fixture_data in fixtures:
                try:
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
                    count += 1
                except Exception:
                    pass
            return count
    
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
    
    def fixture_exists(self, fixture_id: str) -> bool:
        """Check if fixture exists in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM fixtures WHERE fixture_id = ?", (fixture_id,))
            return cursor.fetchone() is not None
    
    # =========================================================================
    # ODDS OPERATIONS
    # =========================================================================
    
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
    
    def insert_odds_batch(self, odds_records: List[Dict[str, Any]]) -> int:
        """Insert multiple odds records in a batch."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for odd in odds_records:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO odds
                        (fixture_id, bookmaker_id, bookmaker_name, market_id,
                         market_name, outcome_id, outcome_name, odds_value)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        odd.get('fixture_id'),
                        odd.get('bookmaker_id'),
                        odd.get('bookmaker_name'),
                        odd.get('market_id'),
                        odd.get('market_name'),
                        odd.get('outcome_id'),
                        odd.get('outcome_name'),
                        odd.get('odds_value')
                    ))
                    count += 1
                except Exception:
                    pass
            return count
    
    def get_odds(self, fixture_id: Optional[str] = None,
                 bookmaker_id: Optional[str] = None,
                 market_id: Optional[str] = None,
                 before_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get odds matching criteria.
        
        Args:
            fixture_id: Filter by fixture ID
            bookmaker_id: Filter by bookmaker ID
            market_id: Filter by market ID
            before_date: Only return odds created before this date (ISO format)
        """
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
            
            if before_date:
                query += " AND created_at <= ?"
                params.append(before_date)
            
            query += " ORDER BY created_at DESC"
            
            return pd.read_sql_query(query, conn, params=params)
    
    # =========================================================================
    # SCORE OPERATIONS
    # =========================================================================
    
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
    
    def insert_scores_batch(self, scores: List[Dict[str, Any]]) -> int:
        """Insert multiple scores in a batch."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for score_data in scores:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO scores
                        (fixture_id, home_score, away_score, status)
                        VALUES (?, ?, ?, ?)
                    """, (
                        score_data.get('fixture_id'),
                        score_data.get('home_score'),
                        score_data.get('away_score'),
                        score_data.get('status')
                    ))
                    count += 1
                except Exception:
                    pass
            return count
    
    def get_scores(self, fixture_id: Optional[str] = None) -> pd.DataFrame:
        """Get scores."""
        with self._get_connection() as conn:
            query = "SELECT * FROM scores WHERE 1=1"
            params = []
            
            if fixture_id:
                query += " AND fixture_id = ?"
                params.append(fixture_id)
            
            return pd.read_sql_query(query, conn, params=params)
    
    # =========================================================================
    # INGESTION METADATA OPERATIONS
    # =========================================================================
    
    def insert_ingestion_metadata(self, source: str, records_count: int,
                                   checksum: Optional[str] = None,
                                   validation_status: str = "success",
                                   errors: Optional[str] = None) -> int:
        """Record ingestion metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ingestion_metadata 
                (source, records_count, checksum, validation_status, errors)
                VALUES (?, ?, ?, ?, ?)
            """, (source, records_count, checksum, validation_status, errors))
            return cursor.lastrowid
    
    def get_ingestion_metadata(self, source: Optional[str] = None,
                                limit: int = 100) -> pd.DataFrame:
        """Get ingestion metadata records."""
        with self._get_connection() as conn:
            # Check if dismissed column exists
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(ingestion_metadata)")
            columns = [row[1] for row in cursor.fetchall()]
            has_dismissed = 'dismissed' in columns
            
            # Build query based on whether dismissed column exists
            if has_dismissed:
                query = "SELECT * FROM ingestion_metadata WHERE (dismissed IS NULL OR dismissed = 0)"
            else:
                query = "SELECT * FROM ingestion_metadata WHERE 1=1"
            
            params = []
            
            if source:
                query += " AND source = ?"
                params.append(source)
            
            query += " ORDER BY ingested_at DESC LIMIT ?"
            params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def dismiss_ingestion_error(self, error_id: int) -> None:
        """Mark an ingestion error as dismissed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if dismissed column exists
            cursor.execute("PRAGMA table_info(ingestion_metadata)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'dismissed' in columns:
                cursor.execute("""
                    UPDATE ingestion_metadata 
                    SET dismissed = 1 
                    WHERE id = ?
                """, (error_id,))
    
    def dismiss_log_error(self, error_key: str) -> None:
        """Record a dismissed log error."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO dismissed_errors (error_key, error_type)
                VALUES (?, 'log')
            """, (error_key,))
    
    def get_dismissed_log_errors(self) -> Set[str]:
        """Get set of dismissed log error keys."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT error_key FROM dismissed_errors WHERE error_type = 'log'")
            return {row[0] for row in cursor.fetchall()}
    
    # =========================================================================
    # BET HISTORY OPERATIONS (FAKE MONEY)
    # =========================================================================
    
    def insert_bet(self, bet_data: Dict[str, Any]) -> int:
        """Insert a new bet into history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bet_history 
                (fixture_id, market_id, market_name, outcome_id, outcome_name,
                 odds, stake, result, model_market)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (
                bet_data['fixture_id'],
                bet_data.get('market_id'),
                bet_data.get('market_name'),
                bet_data.get('outcome_id'),
                bet_data.get('outcome_name'),
                bet_data['odds'],
                bet_data['stake'],
                bet_data.get('model_market')
            ))
            return cursor.lastrowid
    
    def settle_bet(self, bet_id: int, result: str, payout: float) -> None:
        """Settle a bet with result and payout."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bet_history 
                SET result = ?, payout = ?, settled_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (result, payout, bet_id))
    
    def get_bet_history(self, result: Optional[str] = None,
                        model_market: Optional[str] = None,
                        market_name: Optional[str] = None,
                        outcome_name: Optional[str] = None,
                        tournament_name: Optional[str] = None,
                        date_from: Optional[str] = None,
                        date_to: Optional[str] = None,
                        limit: int = 100,
                        offset: int = 0) -> pd.DataFrame:
        """Get bet history with optional filtering and pagination."""
        with self._get_connection() as conn:
            query = """
                SELECT 
                    bh.*,
                    f.tournament_name
                FROM bet_history bh
                LEFT JOIN fixtures f ON bh.fixture_id = f.fixture_id
                WHERE 1=1
            """
            params = []
            
            if result:
                query += " AND bh.result = ?"
                params.append(result)
            
            if model_market:
                query += " AND bh.model_market = ?"
                params.append(model_market)
            
            if market_name:
                query += " AND bh.market_name LIKE ?"
                params.append(f"%{market_name}%")
            
            if outcome_name:
                query += " AND bh.outcome_name LIKE ?"
                params.append(f"%{outcome_name}%")
            
            if tournament_name:
                query += " AND f.tournament_name LIKE ?"
                params.append(f"%{tournament_name}%")
            
            if date_from:
                query += " AND DATE(bh.placed_at) >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND DATE(bh.placed_at) <= ?"
                params.append(date_to)
            
            query += " ORDER BY bh.placed_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            return pd.read_sql_query(query, conn, params=params)
    
    def get_bet_history_count(self, result: Optional[str] = None,
                              model_market: Optional[str] = None,
                              market_name: Optional[str] = None,
                              outcome_name: Optional[str] = None,
                              tournament_name: Optional[str] = None,
                              date_from: Optional[str] = None,
                              date_to: Optional[str] = None) -> int:
        """Get total count of bets matching filters."""
        with self._get_connection() as conn:
            query = """
                SELECT COUNT(*) as count
                FROM bet_history bh
                LEFT JOIN fixtures f ON bh.fixture_id = f.fixture_id
                WHERE 1=1
            """
            params = []
            
            if result:
                query += " AND bh.result = ?"
                params.append(result)
            
            if model_market:
                query += " AND bh.model_market = ?"
                params.append(model_market)
            
            if market_name:
                query += " AND bh.market_name LIKE ?"
                params.append(f"%{market_name}%")
            
            if outcome_name:
                query += " AND bh.outcome_name LIKE ?"
                params.append(f"%{outcome_name}%")
            
            if tournament_name:
                query += " AND f.tournament_name LIKE ?"
                params.append(f"%{tournament_name}%")
            
            if date_from:
                query += " AND DATE(bh.placed_at) >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND DATE(bh.placed_at) <= ?"
                params.append(date_to)
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_pending_bets(self) -> pd.DataFrame:
        """Get all pending bets."""
        return self.get_bet_history(result='pending', limit=10000)
    
    def get_bankroll_stats(self, model_market: Optional[str] = None) -> Dict[str, Any]:
        """Get bankroll statistics, optionally filtered by model market."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_clause = ""
            params = []
            if model_market:
                where_clause = " WHERE model_market = ?"
                params = [model_market]
            
            # Total bets
            cursor.execute(f"SELECT COUNT(*) FROM bet_history{where_clause}", params)
            total_bets = cursor.fetchone()[0]
            
            # Settled bets
            settled_where = where_clause + (" AND" if where_clause else " WHERE") + " result != 'pending'"
            cursor.execute(f"SELECT COUNT(*) FROM bet_history{settled_where}", params)
            settled_bets = cursor.fetchone()[0]
            
            # Wins
            wins_where = where_clause + (" AND" if where_clause else " WHERE") + " result = 'win'"
            cursor.execute(f"SELECT COUNT(*) FROM bet_history{wins_where}", params)
            wins = cursor.fetchone()[0]
            
            # Total stake
            cursor.execute(f"SELECT COALESCE(SUM(stake), 0) FROM bet_history{where_clause}", params)
            total_stake = cursor.fetchone()[0]
            
            # Total payout
            cursor.execute(f"SELECT COALESCE(SUM(payout), 0) FROM bet_history{settled_where}", params)
            total_payout = cursor.fetchone()[0]
            
            return {
                "total_bets": total_bets,
                "settled_bets": settled_bets,
                "pending_bets": total_bets - settled_bets,
                "wins": wins,
                "losses": settled_bets - wins,
                "win_rate": wins / settled_bets if settled_bets > 0 else 0,
                "total_stake": total_stake,
                "total_payout": total_payout,
                "profit": total_payout - total_stake,
                "roi": (total_payout - total_stake) / total_stake if total_stake > 0 else 0
            }
    
    def get_bankroll_stats_by_model(self, market: str) -> Dict[str, Any]:
        """Get bankroll statistics for a specific model market."""
        return self.get_bankroll_stats(model_market=market)
    
    # =========================================================================
    # MODEL VERSION OPERATIONS
    # =========================================================================
    
    def insert_model_version(self, market: str, model_path: str,
                              training_samples: int, cv_score: float,
                              performance_metrics: Optional[Dict] = None) -> int:
        """Insert a new model version."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            metrics_json = json.dumps(performance_metrics) if performance_metrics else None
            
            cursor.execute("""
                INSERT INTO model_versions 
                (market, model_path, training_samples, cv_score, is_active, performance_metrics)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (market, model_path, training_samples, cv_score, metrics_json))
            
            return cursor.lastrowid
    
    def set_active_model(self, version_id: int, market: str) -> None:
        """Set a model version as active (deactivates others for same market)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Deactivate all models for this market
            cursor.execute("""
                UPDATE model_versions SET is_active = 0 WHERE market = ?
            """, (market,))
            
            # Activate the specified version
            cursor.execute("""
                UPDATE model_versions SET is_active = 1 WHERE version_id = ?
            """, (version_id,))
    
    def get_active_model(self, market: str) -> Optional[Dict[str, Any]]:
        """Get the active model for a market."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM model_versions 
                WHERE market = ? AND is_active = 1
            """, (market,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_model_versions(self, market: Optional[str] = None,
                           limit: int = 100) -> pd.DataFrame:
        """Get model versions."""
        with self._get_connection() as conn:
            query = "SELECT * FROM model_versions WHERE 1=1"
            params = []
            
            if market:
                query += " AND market = ?"
                params.append(market)
            
            query += " ORDER BY trained_at DESC LIMIT ?"
            params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    # =========================================================================
    # METRICS OPERATIONS
    # =========================================================================
    
    def insert_metric(self, metric_type: str, metric_name: str, value: float,
                       metadata: Optional[Dict] = None) -> int:
        """Insert a metric record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO metrics (metric_type, metric_name, value, metadata)
                VALUES (?, ?, ?, ?)
            """, (metric_type, metric_name, value, metadata_json))
            
            return cursor.lastrowid
    
    def get_metrics(self, metric_type: Optional[str] = None,
                     metric_name: Optional[str] = None,
                     from_date: Optional[str] = None,
                     to_date: Optional[str] = None,
                     limit: int = 1000) -> pd.DataFrame:
        """Get metrics matching criteria."""
        with self._get_connection() as conn:
            query = "SELECT * FROM metrics WHERE 1=1"
            params = []
            
            if metric_type:
                query += " AND metric_type = ?"
                params.append(metric_type)
            
            if metric_name:
                query += " AND metric_name = ?"
                params.append(metric_name)
            
            if from_date:
                query += " AND timestamp >= ?"
                params.append(from_date)
            
            if to_date:
                query += " AND timestamp <= ?"
                params.append(to_date)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def cleanup_old_metrics(self, retention_months: int = 18) -> int:
        """Delete metrics older than retention period."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM metrics 
                WHERE timestamp < datetime('now', '-' || ? || ' months')
            """, (retention_months,))
            return cursor.rowcount
    
    # =========================================================================
    # UTILITY OPERATIONS
    # =========================================================================
    
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
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            tables = ['fixtures', 'odds', 'scores', 'bet_history', 
                      'model_versions', 'metrics', 'ingestion_metadata']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            
            return stats
