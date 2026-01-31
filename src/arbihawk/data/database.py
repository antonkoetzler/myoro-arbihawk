"""
SQLite database for storing fixtures, odds, scores, and betting data.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import pandas as pd
import numpy as np
from contextlib import contextmanager
import config


def _json_safe(obj: Any) -> Any:
    """Convert numpy/pandas types to native Python for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    return obj


class Database:
    """SQLite database manager for betting data."""
    
    SCHEMA_VERSION = 7  # Increment when schema changes
    
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
                    model_market TEXT,
                    FOREIGN KEY (fixture_id) REFERENCES fixtures(fixture_id)
                )
            """)
            
            # Model versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL DEFAULT 'betting',
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
            
            # Run history table - stores complete run results for debugging
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_type TEXT NOT NULL,
                    domain TEXT NOT NULL DEFAULT 'betting',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds REAL,
                    success INTEGER DEFAULT 0,
                    stopped INTEGER DEFAULT 0,
                    skipped INTEGER DEFAULT 0,
                    skip_reason TEXT,
                    result_data TEXT,
                    errors TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_start_time ON fixtures(start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_tournament ON fixtures(tournament_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_teams_time ON fixtures(home_team_name, away_team_name, start_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_home_team_id ON fixtures(home_team_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fixtures_away_team_id ON fixtures(away_team_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_odds_fixture ON odds(fixture_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds(bookmaker_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scores_fixture ON scores(fixture_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_settlements_fixture_market ON bet_settlements(fixture_id, market_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bet_history_fixture ON bet_history(fixture_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bet_history_result ON bet_history(result)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bet_history_model_market ON bet_history(model_market)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_market ON model_versions(market)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(market, is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_domain_market ON model_versions(domain, market)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_versions_domain_active ON model_versions(domain, market, is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type_time ON metrics(metric_type, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_history_type_time ON run_history(run_type, started_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_history_domain_time ON run_history(domain, started_at)")
            
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
                # Check if table exists first
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='bet_history'
                """)
                table_exists = cursor.fetchone() is not None
                
                if table_exists:
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
            # Check if table exists first
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='ingestion_metadata'
            """)
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
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
        
        # Migration 5: Add domain column to model_versions
        if current_version < 5:
            try:
                # Check if table exists first
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='model_versions'
                """)
                table_exists = cursor.fetchone() is not None
                
                if table_exists:
                    # Check if column already exists
                    cursor.execute("PRAGMA table_info(model_versions)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'domain' not in columns:
                        # Add domain column with default 'betting' for existing rows
                        cursor.execute("ALTER TABLE model_versions ADD COLUMN domain TEXT DEFAULT 'betting'")
                        # Update existing rows to have 'betting' domain
                        cursor.execute("UPDATE model_versions SET domain = 'betting' WHERE domain IS NULL")
                        # Add composite indexes for performance
                        cursor.execute("""
                            CREATE INDEX IF NOT EXISTS idx_model_versions_domain_market 
                            ON model_versions(domain, market)
                        """)
                        cursor.execute("""
                            CREATE INDEX IF NOT EXISTS idx_model_versions_domain_active 
                            ON model_versions(domain, market, is_active)
                        """)
                        # Update schema version
                        cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (5,))
            except sqlite3.OperationalError as e:
                # Column might already exist, ignore
                if "duplicate column name" not in str(e).lower():
                    raise
        
        # Migration 6: Add trading tables (stocks, crypto, price_history, indicators, trades, positions, portfolio)
        if current_version < 6:
            try:
                # Check if tables already exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stocks'")
                stocks_exists = cursor.fetchone() is not None
                
                if not stocks_exists:
                    # Create stocks table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS stocks (
                            symbol TEXT PRIMARY KEY,
                            name TEXT,
                            sector TEXT,
                            industry TEXT,
                            market_cap REAL,
                            exchange TEXT,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create crypto table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS crypto (
                            symbol TEXT PRIMARY KEY,
                            name TEXT,
                            market_cap REAL,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create price_history table (unified for stocks and crypto)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS price_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT NOT NULL,
                            asset_type TEXT NOT NULL,
                            timestamp TEXT NOT NULL,
                            open REAL,
                            high REAL,
                            low REAL,
                            close REAL,
                            volume REAL,
                            UNIQUE(symbol, asset_type, timestamp)
                        )
                    """)
                    
                    # Create indicators table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS indicators (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT NOT NULL,
                            asset_type TEXT NOT NULL,
                            timestamp TEXT NOT NULL,
                            rsi REAL,
                            macd REAL,
                            macd_signal REAL,
                            macd_histogram REAL,
                            sma_20 REAL,
                            sma_50 REAL,
                            sma_200 REAL,
                            bollinger_upper REAL,
                            bollinger_lower REAL,
                            bollinger_middle REAL,
                            atr REAL,
                            volume_sma REAL,
                            UNIQUE(symbol, asset_type, timestamp)
                        )
                    """)
                    
                    # Create trades table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS trades (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT NOT NULL,
                            asset_type TEXT NOT NULL,
                            trade_type TEXT NOT NULL,
                            order_type TEXT NOT NULL,
                            quantity REAL NOT NULL,
                            price REAL NOT NULL,
                            total_cost REAL NOT NULL,
                            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                            strategy TEXT,
                            model_confidence REAL,
                            notes TEXT
                        )
                    """)
                    
                    # Create positions table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS positions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT NOT NULL,
                            asset_type TEXT NOT NULL,
                            quantity REAL NOT NULL,
                            avg_entry_price REAL NOT NULL,
                            current_price REAL,
                            unrealized_pnl REAL,
                            entry_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                            strategy TEXT,
                            stop_loss REAL,
                            take_profit REAL,
                            UNIQUE(symbol, asset_type)
                        )
                    """)
                    
                    # Create portfolio table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS portfolio (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                            cash_balance REAL NOT NULL,
                            total_position_value REAL,
                            total_portfolio_value REAL,
                            unrealized_pnl REAL,
                            realized_pnl REAL
                        )
                    """)
                    
                    # Create indexes for performance
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_price_history_symbol_time 
                        ON price_history(symbol, asset_type, timestamp)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_price_history_asset_time 
                        ON price_history(asset_type, timestamp)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_indicators_symbol_time 
                        ON indicators(symbol, asset_type, timestamp)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_trades_symbol_time 
                        ON trades(symbol, asset_type, timestamp)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_trades_strategy 
                        ON trades(strategy)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_positions_symbol 
                        ON positions(symbol, asset_type)
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_portfolio_timestamp 
                        ON portfolio(timestamp)
                    """)
                    
                    # Update schema version
                    cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (6,))
            except sqlite3.OperationalError as e:
                # Table might already exist, ignore
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                    raise
        
        # Migration 7: Add run_history table
        if current_version < 7:
            try:
                # Check if table already exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='run_history'")
                table_exists = cursor.fetchone() is not None
                
                if not table_exists:
                    # Create run_history table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS run_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            run_type TEXT NOT NULL,
                            domain TEXT NOT NULL DEFAULT 'betting',
                            started_at TEXT NOT NULL,
                            completed_at TEXT,
                            duration_seconds REAL,
                            success INTEGER DEFAULT 0,
                            stopped INTEGER DEFAULT 0,
                            skipped INTEGER DEFAULT 0,
                            skip_reason TEXT,
                            result_data TEXT,
                            errors TEXT,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_history_type_time ON run_history(run_type, started_at)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_history_domain_time ON run_history(domain, started_at)")
                    # Update schema version
                    cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (7,))
            except sqlite3.OperationalError as e:
                # Table might already exist, ignore
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
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
                     home_team_id: Optional[str] = None,
                     away_team_id: Optional[str] = None,
                     limit: Optional[int] = None) -> pd.DataFrame:
        """Get fixtures matching criteria. Uses indexed columns when filters provided."""
        with self._get_connection() as conn:
            query = "SELECT * FROM fixtures WHERE 1=1"
            params: List[Any] = []

            if sport_id is not None:
                query += " AND sport_id = ?"
                params.append(sport_id)

            if tournament_id is not None:
                query += " AND tournament_id = ?"
                params.append(tournament_id)

            if from_date:
                query += " AND start_time >= ?"
                params.append(from_date)

            if to_date:
                query += " AND start_time <= ?"
                params.append(to_date)

            if home_team_id is not None and home_team_id != "":
                query += " AND home_team_id = ?"
                params.append(home_team_id)

            if away_team_id is not None and away_team_id != "":
                query += " AND away_team_id = ?"
                params.append(away_team_id)

            query += " ORDER BY start_time"

            if limit is not None and limit > 0:
                query += " LIMIT ?"
                params.append(limit)

            return pd.read_sql_query(query, conn, params=params)
    
    def fixture_exists(self, fixture_id: str) -> bool:
        """Check if fixture exists in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM fixtures WHERE fixture_id = ?", (fixture_id,))
            return cursor.fetchone() is not None
    
    def get_fixture_by_id(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        """Get a single fixture by fixture_id. Returns dict or None."""
        with self._get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM fixtures WHERE fixture_id = ?", conn, params=(fixture_id,)
            )
        if df.empty:
            return None
        row = df.iloc[0]
        return dict(row) if row is not None else None
    
    def find_score_by_teams_and_date(
        self,
        home_team: str,
        away_team: str,
        start_time: Optional[str] = None,
        min_match_score: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a score row by teams + date (for settlement fallback when score is under synthetic ID).
        Fetches scores, parses synthetic IDs, uses match_identity.same_match. Returns first match as dict or None.
        """
        from .match_identity import parse_synthetic_id, synthetic_id_matches_fixture, get_aliases_and_min_score
        aliases, default_min = get_aliases_and_min_score()
        threshold = min_match_score if min_match_score is not None else default_min
        scores_df = self.get_scores()
        if scores_df.empty:
            return None
        for _, row in scores_df.iterrows():
            fid = row.get("fixture_id")
            fid_str = str(fid) if fid else ""
            if not parse_synthetic_id(fid_str):
                continue
            if synthetic_id_matches_fixture(
                fid_str,
                home_team,
                away_team,
                start_time,
                min_score=threshold,
                aliases_map=aliases,
            ):
                return {
                    "fixture_id": fid,
                    "home_score": row.get("home_score"),
                    "away_score": row.get("away_score"),
                    "status": row.get("status"),
                }
        return None
    
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
    
    def get_scores(self,
                   fixture_id: Optional[str] = None,
                   fixture_ids: Optional[List[str]] = None) -> pd.DataFrame:
        """Get scores. Single fixture_id or batch fixture_ids (IN clause)."""
        with self._get_connection() as conn:
            query = "SELECT * FROM scores WHERE 1=1"
            params: List[Any] = []

            if fixture_id is not None and fixture_id != "":
                query += " AND fixture_id = ?"
                params.append(fixture_id)
            elif fixture_ids is not None and len(fixture_ids) > 0:
                placeholders = ",".join("?" * len(fixture_ids))
                query += f" AND fixture_id IN ({placeholders})"
                params.extend(fixture_ids)

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
    
    def checksum_exists(self, source: str, checksum: str) -> bool:
        """Check if a checksum already exists for a source.
        
        Args:
            source: Source identifier
            checksum: MD5 checksum to check
            
        Returns:
            True if checksum exists, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM ingestion_metadata
                WHERE source = ? AND checksum = ?
            """, (source, checksum))
            result = cursor.fetchone()
            return result[0] > 0 if result else False
    
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
    
    def insert_model_version(self, domain: str, market: str, model_path: str,
                              training_samples: int, cv_score: float,
                              performance_metrics: Optional[Dict] = None) -> int:
        """
        Insert a new model version.
        
        Args:
            domain: Domain type ('betting' or 'trading')
            market: Market/strategy type (e.g., '1x2', 'momentum', 'swing')
            model_path: Path to saved model file
            training_samples: Number of training samples
            cv_score: Cross-validation score
            performance_metrics: Additional metrics
            
        Returns:
            Version ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            metrics_json = json.dumps(_json_safe(performance_metrics)) if performance_metrics else None
            
            cursor.execute("""
                INSERT INTO model_versions 
                (domain, market, model_path, training_samples, cv_score, is_active, performance_metrics)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (domain, market, model_path, training_samples, cv_score, metrics_json))
            
            return cursor.lastrowid
    
    def set_active_model(self, version_id: int, domain: str, market: str) -> None:
        """
        Set a model version as active (deactivates others for same domain and market).
        
        Args:
            version_id: Version ID to activate
            domain: Domain type ('betting' or 'trading')
            market: Market/strategy type
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Deactivate all models for this domain and market
            cursor.execute("""
                UPDATE model_versions SET is_active = 0 
                WHERE domain = ? AND market = ?
            """, (domain, market))
            
            # Activate the specified version
            cursor.execute("""
                UPDATE model_versions SET is_active = 1 WHERE version_id = ?
            """, (version_id,))
    
    def get_active_model(self, domain: str, market: str) -> Optional[Dict[str, Any]]:
        """
        Get the active model for a domain and market.
        
        Args:
            domain: Domain type ('betting' or 'trading')
            market: Market/strategy type
            
        Returns:
            Active model version dict or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM model_versions 
                WHERE domain = ? AND market = ? AND is_active = 1
            """, (domain, market))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_model_versions(self, domain: Optional[str] = None,
                           market: Optional[str] = None,
                           limit: int = 100) -> pd.DataFrame:
        """
        Get model versions.
        
        Args:
            domain: Filter by domain (optional, None = all domains)
            market: Filter by market (optional, None = all markets)
            limit: Maximum versions to return
            
        Returns:
            DataFrame of model versions
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM model_versions WHERE 1=1"
            params = []
            
            if domain:
                query += " AND domain = ?"
                params.append(domain)
            
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
    # RUN HISTORY OPERATIONS
    # =========================================================================
    
    def _convert_to_json_serializable(self, obj: Any) -> Any:
        """
        Recursively convert numpy/pandas types to native Python types for JSON serialization.
        
        Args:
            obj: Object to convert (dict, list, or primitive)
            
        Returns:
            Object with numpy/pandas types converted to native Python types
        """
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: self._convert_to_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int_, np.intc, np.intp, np.int8,
                             np.int16, np.int32, np.int64, np.uint8, np.uint16,
                             np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def insert_run_history(self, run_type: str, domain: str, started_at: str,
                          completed_at: Optional[str] = None,
                          duration_seconds: Optional[float] = None,
                          success: bool = False, stopped: bool = False,
                          skipped: bool = False, skip_reason: Optional[str] = None,
                          result_data: Optional[Dict[str, Any]] = None,
                          errors: Optional[List[str]] = None) -> int:
        """
        Insert a run history record.
        
        Args:
            run_type: Type of run (collection, training, betting, full_run, trading_collection, etc.)
            domain: Domain (betting or trading)
            started_at: ISO timestamp when run started
            completed_at: ISO timestamp when run completed (None if still running)
            duration_seconds: Duration in seconds
            success: Whether run succeeded
            stopped: Whether run was stopped by user
            skipped: Whether run was skipped
            skip_reason: Reason for skipping (if skipped)
            result_data: Full result dictionary as JSON
            errors: List of error messages
            
        Returns:
            Run history record ID
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Convert numpy/pandas types before JSON serialization
            result_data_serializable = self._convert_to_json_serializable(result_data) if result_data else None
            errors_serializable = self._convert_to_json_serializable(errors) if errors else None
            result_json = json.dumps(result_data_serializable) if result_data_serializable else None
            errors_json = json.dumps(errors_serializable) if errors_serializable else None
            
            cursor.execute("""
                INSERT INTO run_history 
                (run_type, domain, started_at, completed_at, duration_seconds,
                 success, stopped, skipped, skip_reason, result_data, errors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_type, domain, started_at, completed_at, duration_seconds,
                1 if success else 0, 1 if stopped else 0, 1 if skipped else 0,
                skip_reason, result_json, errors_json
            ))
            return cursor.lastrowid
    
    def get_run_history(self, run_type: Optional[str] = None,
                        domain: Optional[str] = None,
                        limit: int = 100,
                        from_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get run history records.
        
        Args:
            run_type: Filter by run type (optional)
            domain: Filter by domain (optional)
            limit: Maximum records to return
            from_date: Filter by start date (ISO format, optional)
            
        Returns:
            DataFrame with run history records
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM run_history WHERE 1=1"
            params = []
            
            if run_type:
                query += " AND run_type = ?"
                params.append(run_type)
            
            if domain:
                query += " AND domain = ?"
                params.append(domain)
            
            if from_date:
                query += " AND started_at >= ?"
                params.append(from_date)
            
            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)
            
            df = pd.read_sql_query(query, conn, params=params)
            return df
    
    def cleanup_old_run_history(self, retention_months: int = 18) -> int:
        """Delete run history older than retention period."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM run_history 
                WHERE started_at < datetime('now', '-' || ? || ' months')
            """, (retention_months,))
            return cursor.rowcount
    
    # =========================================================================
    # STOCK OPERATIONS
    # =========================================================================
    
    def insert_stock(self, stock_data: Dict[str, Any]) -> None:
        """
        Insert or update a stock.
        
        Args:
            stock_data: Dict with symbol, name, sector, industry, market_cap, exchange
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO stocks 
                (symbol, name, sector, industry, market_cap, exchange)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                stock_data['symbol'],
                stock_data.get('name'),
                stock_data.get('sector'),
                stock_data.get('industry'),
                stock_data.get('market_cap'),
                stock_data.get('exchange')
            ))
    
    def get_stocks(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get stocks.
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            DataFrame of stocks
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM stocks WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            return pd.read_sql_query(query, conn, params=params)
    
    # =========================================================================
    # CRYPTO OPERATIONS
    # =========================================================================
    
    def insert_crypto(self, crypto_data: Dict[str, Any]) -> None:
        """
        Insert or update a crypto.
        
        Args:
            crypto_data: Dict with symbol, name, market_cap
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO crypto 
                (symbol, name, market_cap)
                VALUES (?, ?, ?)
            """, (
                crypto_data['symbol'],
                crypto_data.get('name'),
                crypto_data.get('market_cap')
            ))
    
    def get_crypto(self, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Get crypto.
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            DataFrame of crypto
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM crypto WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            return pd.read_sql_query(query, conn, params=params)
    
    # =========================================================================
    # PRICE HISTORY OPERATIONS
    # =========================================================================
    
    def insert_price_history(self, symbol: str, asset_type: str, price_data: Dict[str, Any]) -> int:
        """
        Insert price history record.
        
        Args:
            symbol: Stock/crypto symbol
            asset_type: 'stock' or 'crypto'
            price_data: Dict with timestamp, open, high, low, close, volume
            
        Returns:
            Record ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO price_history 
                (symbol, asset_type, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                asset_type,
                price_data['timestamp'],
                price_data.get('open'),
                price_data.get('high'),
                price_data.get('low'),
                price_data.get('close'),
                price_data.get('volume')
            ))
            return cursor.lastrowid
    
    def insert_price_history_batch(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert multiple price history records in a batch.
        
        Args:
            records: List of dicts with symbol, asset_type, timestamp, open, high, low, close, volume
            
        Returns:
            Number of records inserted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for record in records:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO price_history 
                        (symbol, asset_type, timestamp, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record['symbol'],
                        record['asset_type'],
                        record['timestamp'],
                        record.get('open'),
                        record.get('high'),
                        record.get('low'),
                        record.get('close'),
                        record.get('volume')
                    ))
                    count += 1
                except Exception as e:
                    # Log error but continue with other records
                    import logging
                    logging.warning(f"Error inserting price history record: {e}")
                    continue
            return count
    
    def get_price_history(self, symbol: Optional[str] = None,
                          asset_type: Optional[str] = None,
                          from_date: Optional[str] = None,
                          to_date: Optional[str] = None,
                          limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get price history.
        
        Args:
            symbol: Filter by symbol (optional)
            asset_type: Filter by asset_type ('stock' or 'crypto', optional)
            from_date: Filter from date (ISO format, optional)
            to_date: Filter to date (ISO format, optional)
            limit: Maximum records to return (optional)
            
        Returns:
            DataFrame of price history
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM price_history WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if asset_type:
                query += " AND asset_type = ?"
                params.append(asset_type)
            
            if from_date:
                query += " AND timestamp >= ?"
                params.append(from_date)
            
            if to_date:
                query += " AND timestamp <= ?"
                params.append(to_date)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    # =========================================================================
    # INDICATORS OPERATIONS
    # =========================================================================
    
    def insert_indicator(self, symbol: str, asset_type: str, indicator_data: Dict[str, Any]) -> int:
        """
        Insert indicator record.
        
        Args:
            symbol: Stock/crypto symbol
            asset_type: 'stock' or 'crypto'
            indicator_data: Dict with timestamp and indicator values (rsi, macd, etc.)
            
        Returns:
            Record ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO indicators 
                (symbol, asset_type, timestamp, rsi, macd, macd_signal, macd_histogram,
                 sma_20, sma_50, sma_200, bollinger_upper, bollinger_lower, bollinger_middle,
                 atr, volume_sma)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                asset_type,
                indicator_data['timestamp'],
                indicator_data.get('rsi'),
                indicator_data.get('macd'),
                indicator_data.get('macd_signal'),
                indicator_data.get('macd_histogram'),
                indicator_data.get('sma_20'),
                indicator_data.get('sma_50'),
                indicator_data.get('sma_200'),
                indicator_data.get('bollinger_upper'),
                indicator_data.get('bollinger_lower'),
                indicator_data.get('bollinger_middle'),
                indicator_data.get('atr'),
                indicator_data.get('volume_sma')
            ))
            return cursor.lastrowid
    
    def insert_indicators_batch(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert multiple indicator records in a batch.
        
        Args:
            records: List of dicts with symbol, asset_type, timestamp, and indicator values
            
        Returns:
            Number of records inserted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for record in records:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO indicators 
                        (symbol, asset_type, timestamp, rsi, macd, macd_signal, macd_histogram,
                         sma_20, sma_50, sma_200, bollinger_upper, bollinger_lower, bollinger_middle,
                         atr, volume_sma)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record['symbol'],
                        record['asset_type'],
                        record['timestamp'],
                        record.get('rsi'),
                        record.get('macd'),
                        record.get('macd_signal'),
                        record.get('macd_histogram'),
                        record.get('sma_20'),
                        record.get('sma_50'),
                        record.get('sma_200'),
                        record.get('bollinger_upper'),
                        record.get('bollinger_lower'),
                        record.get('bollinger_middle'),
                        record.get('atr'),
                        record.get('volume_sma')
                    ))
                    count += 1
                except Exception as e:
                    import logging
                    logging.warning(f"Error inserting indicator record: {e}")
                    continue
            return count
    
    def get_indicators(self, symbol: Optional[str] = None,
                       asset_type: Optional[str] = None,
                       from_date: Optional[str] = None,
                       to_date: Optional[str] = None,
                       limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get indicators.
        
        Args:
            symbol: Filter by symbol (optional)
            asset_type: Filter by asset_type (optional)
            from_date: Filter from date (ISO format, optional)
            to_date: Filter to date (ISO format, optional)
            limit: Maximum records to return (optional)
            
        Returns:
            DataFrame of indicators
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM indicators WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if asset_type:
                query += " AND asset_type = ?"
                params.append(asset_type)
            
            if from_date:
                query += " AND timestamp >= ?"
                params.append(from_date)
            
            if to_date:
                query += " AND timestamp <= ?"
                params.append(to_date)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    # =========================================================================
    # TRADES OPERATIONS
    # =========================================================================
    
    def insert_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Insert a trade record.
        
        Args:
            trade_data: Dict with symbol, asset_type, trade_type/direction, order_type, 
                       quantity, price, total_cost, strategy, model_confidence, notes, pnl
            
        Returns:
            Trade ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Support both 'trade_type' and 'direction' field names
            trade_type = trade_data.get('trade_type', trade_data.get('direction', 'buy'))
            
            # Calculate total_cost if not provided
            total_cost = trade_data.get('total_cost')
            if total_cost is None:
                quantity = trade_data.get('quantity', 0)
                price = trade_data.get('price', 0)
                total_cost = quantity * price
            
            cursor.execute("""
                INSERT INTO trades 
                (symbol, asset_type, trade_type, order_type, quantity, price, total_cost,
                 strategy, model_confidence, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data['symbol'],
                trade_data.get('asset_type', 'stock'),
                trade_type,
                trade_data.get('order_type', 'market'),
                trade_data.get('quantity', 0),
                trade_data.get('price', 0),
                total_cost,
                trade_data.get('strategy'),
                trade_data.get('model_confidence'),
                trade_data.get('notes', f"P&L: {trade_data.get('pnl', 0)}")
            ))
            return cursor.lastrowid
    
    def get_trades(self, symbol: Optional[str] = None,
                   asset_type: Optional[str] = None,
                   strategy: Optional[str] = None,
                   from_date: Optional[str] = None,
                   to_date: Optional[str] = None,
                   limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get trades.
        
        Args:
            symbol: Filter by symbol (optional)
            asset_type: Filter by asset_type (optional)
            strategy: Filter by strategy (optional)
            from_date: Filter from date (ISO format, optional)
            to_date: Filter to date (ISO format, optional)
            limit: Maximum records to return (optional)
            
        Returns:
            DataFrame of trades
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if asset_type:
                query += " AND asset_type = ?"
                params.append(asset_type)
            
            if strategy:
                query += " AND strategy = ?"
                params.append(strategy)
            
            if from_date:
                query += " AND timestamp >= ?"
                params.append(from_date)
            
            if to_date:
                query += " AND timestamp <= ?"
                params.append(to_date)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    # =========================================================================
    # POSITIONS OPERATIONS
    # =========================================================================
    
    def insert_position(self, position_data: Dict[str, Any]) -> int:
        """
        Insert or update a position.
        
        Args:
            position_data: Dict with symbol, asset_type, quantity, avg_entry_price,
                         current_price, unrealized_pnl, strategy, stop_loss, take_profit
            
        Returns:
            Position ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO positions 
                (symbol, asset_type, quantity, avg_entry_price, current_price, unrealized_pnl,
                 strategy, stop_loss, take_profit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data['symbol'],
                position_data['asset_type'],
                position_data['quantity'],
                position_data['avg_entry_price'],
                position_data.get('current_price'),
                position_data.get('unrealized_pnl'),
                position_data.get('strategy'),
                position_data.get('stop_loss'),
                position_data.get('take_profit')
            ))
            return cursor.lastrowid
    
    def update_position(self, symbol: str, asset_type: str, updates: Dict[str, Any]) -> None:
        """
        Update a position.
        
        Args:
            symbol: Stock/crypto symbol
            asset_type: 'stock' or 'crypto'
            updates: Dict with fields to update (current_price, unrealized_pnl, quantity, etc.)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build UPDATE query dynamically
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key in ['current_price', 'unrealized_pnl', 'quantity', 'avg_entry_price',
                          'strategy', 'stop_loss', 'take_profit']:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return  # No valid fields to update
            
            params.extend([symbol, asset_type])
            query = f"""
                UPDATE positions 
                SET {', '.join(set_clauses)}
                WHERE symbol = ? AND asset_type = ?
            """
            cursor.execute(query, params)
    
    def get_positions(self, symbol: Optional[str] = None,
                     asset_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get positions.
        
        Args:
            symbol: Filter by symbol (optional)
            asset_type: Filter by asset_type (optional)
            
        Returns:
            DataFrame of positions
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM positions WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if asset_type:
                query += " AND asset_type = ?"
                params.append(asset_type)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def delete_position(self, symbol: str, asset_type: str) -> None:
        """
        Delete a position (when closing it).
        
        Args:
            symbol: Stock/crypto symbol
            asset_type: 'stock' or 'crypto'
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM positions 
                WHERE symbol = ? AND asset_type = ?
            """, (symbol, asset_type))
    
    # =========================================================================
    # PORTFOLIO OPERATIONS
    # =========================================================================
    
    def insert_portfolio_snapshot(self, snapshot_data: Dict[str, Any]) -> int:
        """
        Insert a portfolio snapshot.
        
        Args:
            snapshot_data: Dict with cash_balance, total_position_value, total_portfolio_value,
                          unrealized_pnl, realized_pnl
            
        Returns:
            Snapshot ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO portfolio 
                (cash_balance, total_position_value, total_portfolio_value, unrealized_pnl, realized_pnl)
                VALUES (?, ?, ?, ?, ?)
            """, (
                snapshot_data['cash_balance'],
                snapshot_data.get('total_position_value'),
                snapshot_data.get('total_portfolio_value'),
                snapshot_data.get('unrealized_pnl'),
                snapshot_data.get('realized_pnl')
            ))
            return cursor.lastrowid
    
    def get_portfolio_snapshots(self, from_date: Optional[str] = None,
                                to_date: Optional[str] = None,
                                limit: int = 1000) -> pd.DataFrame:
        """
        Get portfolio snapshots.
        
        Args:
            from_date: Filter from date (ISO format, optional)
            to_date: Filter to date (ISO format, optional)
            limit: Maximum records to return
            
        Returns:
            DataFrame of portfolio snapshots
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM portfolio WHERE 1=1"
            params = []
            
            if from_date:
                query += " AND timestamp >= ?"
                params.append(from_date)
            
            if to_date:
                query += " AND timestamp <= ?"
                params.append(to_date)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def get_latest_portfolio_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest portfolio snapshot.
        
        Returns:
            Latest snapshot dict or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM portfolio 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    # Aliases for trading system compatibility
    def get_portfolio(self, limit: int = 1000) -> pd.DataFrame:
        """Alias for get_portfolio_snapshots for trading compatibility."""
        return self.get_portfolio_snapshots(limit=limit)
    
    def insert_portfolio(self, data: Dict[str, Any]) -> int:
        """Alias for insert_portfolio_snapshot for trading compatibility."""
        # Map trading system fields to portfolio snapshot fields
        snapshot_data = {
            'cash_balance': data.get('cash_balance', 0),
            'total_position_value': 0,  # Will be calculated
            'total_portfolio_value': data.get('total_value', data.get('cash_balance', 0)),
            'unrealized_pnl': data.get('unrealized_pnl', 0),
            'realized_pnl': data.get('realized_pnl', 0)
        }
        return self.insert_portfolio_snapshot(snapshot_data)
    
    # =========================================================================
    # TRADING POSITION OPERATIONS (Extended)
    # =========================================================================
    
    def open_position(self, position_data: Dict[str, Any]) -> int:
        """
        Open a new trading position.
        
        Args:
            position_data: Dict with symbol, asset_type, strategy, direction,
                          quantity, entry_price, stop_loss, take_profit, etc.
                          
        Returns:
            Position ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO positions 
                (symbol, asset_type, quantity, avg_entry_price, current_price, unrealized_pnl,
                 strategy, stop_loss, take_profit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data['symbol'],
                position_data.get('asset_type', 'stock'),
                position_data['quantity'],
                position_data.get('entry_price', position_data.get('avg_entry_price')),
                position_data.get('current_price', position_data.get('entry_price')),
                position_data.get('unrealized_pnl', 0),
                position_data.get('strategy'),
                position_data.get('stop_loss'),
                position_data.get('take_profit')
            ))
            return cursor.lastrowid
    
    def close_position(self, position_id: int, close_price: float, pnl: float) -> None:
        """
        Close a position by ID.
        
        Args:
            position_id: Position ID to close
            close_price: Closing price
            pnl: Realized P&L from this position
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Delete the position (positions table tracks open positions)
            cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
    
    def update_position_price(self, position_id: int, current_price: float, 
                               unrealized_pnl: float) -> None:
        """
        Update position current price and unrealized P&L.
        
        Args:
            position_id: Position ID
            current_price: Current market price
            unrealized_pnl: Current unrealized P&L
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions 
                SET current_price = ?, unrealized_pnl = ?
                WHERE id = ?
            """, (current_price, unrealized_pnl, position_id))
    
    def get_positions(self, symbol: Optional[str] = None,
                     asset_type: Optional[str] = None,
                     status: Optional[str] = None) -> pd.DataFrame:
        """
        Get positions.
        
        Args:
            symbol: Filter by symbol (optional)
            asset_type: Filter by asset_type (optional)
            status: 'open' or 'closed' (optional, currently all positions are open)
            
        Returns:
            DataFrame of positions
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM positions WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if asset_type:
                query += " AND asset_type = ?"
                params.append(asset_type)
            
            # Note: status filtering not needed since we only store open positions
            # closed positions are deleted and recorded as trades
            
            return pd.read_sql_query(query, conn, params=params)
    
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
                      'model_versions', 'metrics', 'ingestion_metadata',
                      'stocks', 'crypto', 'price_history', 'indicators', 
                      'trades', 'positions', 'portfolio']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            
            return stats
    
    def reset_database(self, preserve_models: bool = True) -> Dict[str, Any]:
        """
        Reset database by clearing all data tables.
        
        Preserves schema and optionally model_versions. Creates a backup
        before resetting.
        
        Args:
            preserve_models: If True, keep model_versions table intact
            
        Returns:
            Dict with reset results (records_deleted, backup_path, etc.)
        """
        from data.backup import DatabaseBackup
        
        backup = DatabaseBackup()
        backup_path = backup.create_backup("pre_reset")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Disable foreign keys temporarily for faster deletion
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Tables to clear (in dependency order)
            tables_to_clear = [
                'bet_history',
                'bet_settlements',
                'odds',
                'scores',
                'fixtures',
                'ingestion_metadata',
                'metrics',
                'dismissed_errors'
            ]
            
            # Add model_versions if not preserving models
            if not preserve_models:
                tables_to_clear.append('model_versions')
            
            records_deleted = {}
            total_deleted = 0
            
            for table in tables_to_clear:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_before = cursor.fetchone()[0]
                cursor.execute(f"DELETE FROM {table}")
                records_deleted[table] = count_before
                total_deleted += count_before
            
            # Reset auto-increment counters
            for table in tables_to_clear:
                try:
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
                except:
                    pass  # Table might not use auto-increment
            
            # Re-enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Commit transaction before VACUUM (VACUUM can't run in transaction)
            conn.commit()
            
            # Vacuum to reclaim space (runs outside transaction)
            cursor.execute("VACUUM")
            
            return {
                "success": True,
                "backup_path": backup_path,
                "records_deleted": records_deleted,
                "total_deleted": total_deleted,
                "preserved_models": preserve_models,
                "model_versions_kept": self.get_model_versions(domain=None).shape[0] if preserve_models else 0
            }
    
    def reset_betting_domain(self, preserve_models: bool = True) -> Dict[str, Any]:
        """
        Reset only betting-related data: bet_history, bet_settlements, odds, scores,
        fixtures, ingestion_metadata, metrics, dismissed_errors. Optionally model_versions.
        Creates backup first. Trading tables (stocks, crypto, portfolio, etc.) are untouched.
        """
        from data.backup import DatabaseBackup
        backup = DatabaseBackup(db_path=self.db_path)
        backup_path = backup.create_backup("pre_reset_betting")
        tables = [
            'bet_history', 'bet_settlements', 'odds', 'scores', 'fixtures',
            'ingestion_metadata', 'metrics', 'dismissed_errors'
        ]
        if not preserve_models:
            tables.append('model_versions')
        records_deleted = {}
        total_deleted = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = OFF")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_before = cursor.fetchone()[0]
                cursor.execute(f"DELETE FROM {table}")
                records_deleted[table] = count_before
                total_deleted += count_before
            for table in tables:
                try:
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
                except Exception:
                    pass
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            cursor.execute("VACUUM")
        return {
            "success": True,
            "domain": "betting",
            "backup_path": backup_path,
            "records_deleted": records_deleted,
            "total_deleted": total_deleted,
        }
    
    def reset_trading_domain(self) -> Dict[str, Any]:
        """
        Reset only trading-related data: stocks, crypto, price_history, indicators,
        trades, positions, portfolio. Creates backup first. Betting tables are untouched.
        """
        from data.backup import DatabaseBackup
        backup = DatabaseBackup(db_path=self.db_path)
        backup_path = backup.create_backup("pre_reset_trading")
        tables = ['trades', 'positions', 'portfolio', 'indicators', 'price_history', 'stocks', 'crypto']
        records_deleted = {}
        total_deleted = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = OFF")
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count_before = cursor.fetchone()[0]
                    cursor.execute(f"DELETE FROM {table}")
                    records_deleted[table] = count_before
                    total_deleted += count_before
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
                except Exception:
                    pass
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            cursor.execute("VACUUM")
        return {
            "success": True,
            "domain": "trading",
            "backup_path": backup_path,
            "records_deleted": records_deleted,
            "total_deleted": total_deleted,
        }
    
    def sync_from_production(self, production_db_path: str) -> Dict[str, Any]:
        """
        Sync all data from production database to this database (one-way).
        
        This is used to copy production data to debug database for testing.
        Clears existing data in target database first, then copies all data.
        
        Args:
            production_db_path: Path to production database
            
        Returns:
            Dict with sync results (records_copied, etc.)
        """
        from pathlib import Path
        
        prod_path = Path(production_db_path)
        if not prod_path.exists():
            raise ValueError(f"Production database not found: {production_db_path}")
        
        # Tables to sync (in dependency order)
        tables_to_sync = [
            'fixtures',
            'scores',
            'odds',
            'ingestion_metadata',
            'bet_history',
            'bet_settlements',
            'metrics',
            'dismissed_errors',
            'model_versions'
        ]
        
        records_copied = {}
        total_copied = 0
        
        # Connect to both databases
        with sqlite3.connect(production_db_path) as prod_conn:
            prod_conn.row_factory = sqlite3.Row
            
            with self._get_connection() as target_conn:
                target_cursor = target_conn.cursor()
                prod_cursor = prod_conn.cursor()
                
                # Disable foreign keys for faster insertion
                target_cursor.execute("PRAGMA foreign_keys = OFF")
                
                # Clear target database first (except schema)
                for table in tables_to_sync:
                    target_cursor.execute(f"DELETE FROM {table}")
                    target_cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
                
                # Copy data from production to target
                for table in tables_to_sync:
                    # Get all rows from production
                    prod_cursor.execute(f"SELECT * FROM {table}")
                    rows = prod_cursor.fetchall()
                    
                    if len(rows) == 0:
                        records_copied[table] = 0
                        continue
                    
                    # Get column names
                    columns = [description[0] for description in prod_cursor.description]
                    placeholders = ','.join(['?' for _ in columns])
                    columns_str = ','.join(columns)
                    
                    # Insert into target
                    insert_sql = f"INSERT OR REPLACE INTO {table} ({columns_str}) VALUES ({placeholders})"
                    target_cursor.executemany(insert_sql, [tuple(row) for row in rows])
                    
                    records_copied[table] = len(rows)
                    total_copied += len(rows)
                
                # Re-enable foreign keys
                target_cursor.execute("PRAGMA foreign_keys = ON")
        
        return {
            "success": True,
            "records_copied": records_copied,
            "total_copied": total_copied,
            "source_db": str(production_db_path),
            "target_db": self.db_path
        }
