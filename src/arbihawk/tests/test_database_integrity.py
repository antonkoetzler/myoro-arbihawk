"""
Test suite for database integrity.
Tests foreign key constraints, data consistency, and validation.
"""
import pytest
from data.database import Database


class TestDatabaseIntegrity:
    """Test database integrity and constraints."""
    
    def test_no_orphaned_odds(self, temp_db):
        """Test that all odds reference existing fixtures."""
        # Create fixture
        temp_db.insert_fixture({
            "fixture_id": "test_fixture_integrity",
            "home_team_name": "Team A",
            "away_team_name": "Team B",
            "start_time": "2025-01-20T15:00:00Z",
            "status": "scheduled"
        })
        
        # Insert odds
        temp_db.insert_odds("test_fixture_integrity", [
            {
                "bookmaker_id": "betano",
                "bookmaker_name": "Betano",
                "market_id": "1x2",
                "market_name": "Match Result",
                "outcome_id": "home",
                "outcome_name": "Home",
                "odds_value": 2.5
            }
        ])
        
        # Check for orphaned odds
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM odds o
                LEFT JOIN fixtures f ON o.fixture_id = f.fixture_id
                WHERE f.fixture_id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            assert orphaned == 0
    
    def test_no_orphaned_scores(self, temp_db):
        """Test that all scores reference existing fixtures."""
        # Create fixture
        temp_db.insert_fixture({
            "fixture_id": "test_fixture_scores",
            "home_team_name": "Team A",
            "away_team_name": "Team B",
            "start_time": "2025-01-20T15:00:00Z",
            "status": "finished"
        })
        
        # Insert score
        temp_db.insert_score("test_fixture_scores", {
            "home_score": 2,
            "away_score": 1,
            "status": "finished"
        })
        
        # Check for orphaned scores
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM scores s
                LEFT JOIN fixtures f ON s.fixture_id = f.fixture_id
                WHERE f.fixture_id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            assert orphaned == 0
    
    def test_no_duplicate_fixtures(self, temp_db):
        """Test that fixture_id is unique."""
        # Insert same fixture twice (should replace)
        temp_db.insert_fixture({
            "fixture_id": "duplicate_test",
            "home_team_name": "Team A",
            "away_team_name": "Team B",
            "start_time": "2025-01-20T15:00:00Z",
            "status": "scheduled"
        })
        
        temp_db.insert_fixture({
            "fixture_id": "duplicate_test",
            "home_team_name": "Team A Updated",
            "away_team_name": "Team B",
            "start_time": "2025-01-20T15:00:00Z",
            "status": "scheduled"
        })
        
        # Should only be one fixture
        fixtures = temp_db.get_fixtures()
        duplicate_count = len(fixtures[fixtures["fixture_id"] == "duplicate_test"])
        assert duplicate_count == 1
        
        # Should have updated name
        fixture = fixtures[fixtures["fixture_id"] == "duplicate_test"].iloc[0]
        assert fixture["home_team_name"] == "Team A Updated"
    
    def test_no_duplicate_odds(self, temp_db):
        """Test that odds have unique constraint."""
        # Create fixture
        temp_db.insert_fixture({
            "fixture_id": "test_odds_unique",
            "home_team_name": "Team A",
            "away_team_name": "Team B",
            "start_time": "2025-01-20T15:00:00Z",
            "status": "scheduled"
        })
        
        # Insert same odds twice (should replace)
        odds_data = [{
            "bookmaker_id": "betano",
            "bookmaker_name": "Betano",
            "market_id": "1x2",
            "market_name": "Match Result",
            "outcome_id": "home",
            "outcome_name": "Home",
            "odds_value": 2.5
        }]
        
        temp_db.insert_odds("test_odds_unique", odds_data)
        temp_db.insert_odds("test_odds_unique", odds_data)
        
        # Should only be one odds record
        odds = temp_db.get_odds(fixture_id="test_odds_unique")
        assert len(odds) == 1
    
    def test_trading_tables_exist(self, temp_db):
        """Test that all trading tables are created."""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN 
                ('stocks', 'crypto', 'price_history', 'indicators', 'trades', 'positions', 'portfolio')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'stocks' in tables
            assert 'crypto' in tables
            assert 'price_history' in tables
            assert 'indicators' in tables
            assert 'trades' in tables
            assert 'positions' in tables
            assert 'portfolio' in tables
    
    def test_stock_insert_and_retrieve(self, temp_db):
        """Test inserting and retrieving stocks."""
        temp_db.insert_stock({
            'symbol': 'AAPL',
            'name': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'market_cap': 3000000000000,
            'exchange': 'NASDAQ'
        })
        
        stocks = temp_db.get_stocks()
        assert len(stocks) == 1
        assert stocks.iloc[0]['symbol'] == 'AAPL'
        assert stocks.iloc[0]['name'] == 'Apple Inc.'
    
    def test_crypto_insert_and_retrieve(self, temp_db):
        """Test inserting and retrieving crypto."""
        temp_db.insert_crypto({
            'symbol': 'BTC',
            'name': 'Bitcoin',
            'market_cap': 800000000000
        })
        
        crypto = temp_db.get_crypto()
        assert len(crypto) == 1
        assert crypto.iloc[0]['symbol'] == 'BTC'
        assert crypto.iloc[0]['name'] == 'Bitcoin'
    
    def test_price_history_insert_and_retrieve(self, temp_db):
        """Test inserting and retrieving price history."""
        # Insert stock
        temp_db.insert_stock({
            'symbol': 'AAPL',
            'name': 'Apple Inc.'
        })
        
        # Insert price history
        temp_db.insert_price_history('AAPL', 'stock', {
            'timestamp': '2025-01-20T16:00:00Z',
            'open': 150.0,
            'high': 152.0,
            'low': 149.0,
            'close': 151.0,
            'volume': 1000000
        })
        
        price_history = temp_db.get_price_history(symbol='AAPL', asset_type='stock')
        assert len(price_history) == 1
        assert price_history.iloc[0]['close'] == 151.0
        assert price_history.iloc[0]['volume'] == 1000000
    
    def test_price_history_unique_constraint(self, temp_db):
        """Test that price_history has unique constraint on (symbol, asset_type, timestamp)."""
        temp_db.insert_price_history('AAPL', 'stock', {
            'timestamp': '2025-01-20T16:00:00Z',
            'open': 150.0,
            'high': 152.0,
            'low': 149.0,
            'close': 151.0,
            'volume': 1000000
        })
        
        # Insert same record again (should replace)
        temp_db.insert_price_history('AAPL', 'stock', {
            'timestamp': '2025-01-20T16:00:00Z',
            'open': 150.5,
            'high': 152.5,
            'low': 149.5,
            'close': 151.5,
            'volume': 1100000
        })
        
        price_history = temp_db.get_price_history(symbol='AAPL', asset_type='stock')
        assert len(price_history) == 1
        assert price_history.iloc[0]['close'] == 151.5  # Should be updated value
    
    def test_trade_insert_and_retrieve(self, temp_db):
        """Test inserting and retrieving trades."""
        trade_id = temp_db.insert_trade({
            'symbol': 'AAPL',
            'asset_type': 'stock',
            'trade_type': 'buy',
            'order_type': 'market',
            'quantity': 10,
            'price': 150.0,
            'total_cost': 1500.0,
            'strategy': 'momentum',
            'model_confidence': 0.65
        })
        
        assert trade_id is not None
        
        trades = temp_db.get_trades(symbol='AAPL')
        assert len(trades) == 1
        assert trades.iloc[0]['trade_type'] == 'buy'
        assert trades.iloc[0]['quantity'] == 10
    
    def test_position_insert_update_delete(self, temp_db):
        """Test position operations."""
        # Insert position
        position_id = temp_db.insert_position({
            'symbol': 'AAPL',
            'asset_type': 'stock',
            'quantity': 10,
            'avg_entry_price': 150.0,
            'current_price': 151.0,
            'unrealized_pnl': 10.0,
            'strategy': 'momentum',
            'stop_loss': 145.0,
            'take_profit': 160.0
        })
        
        assert position_id is not None
        
        # Get position
        positions = temp_db.get_positions(symbol='AAPL')
        assert len(positions) == 1
        assert positions.iloc[0]['quantity'] == 10
        
        # Update position
        temp_db.update_position('AAPL', 'stock', {
            'current_price': 152.0,
            'unrealized_pnl': 20.0
        })
        
        positions = temp_db.get_positions(symbol='AAPL')
        assert positions.iloc[0]['current_price'] == 152.0
        assert positions.iloc[0]['unrealized_pnl'] == 20.0
        
        # Delete position
        temp_db.delete_position('AAPL', 'stock')
        positions = temp_db.get_positions(symbol='AAPL')
        assert len(positions) == 0
    
    def test_position_unique_constraint(self, temp_db):
        """Test that positions have unique constraint on (symbol, asset_type)."""
        temp_db.insert_position({
            'symbol': 'AAPL',
            'asset_type': 'stock',
            'quantity': 10,
            'avg_entry_price': 150.0
        })
        
        # Insert same position again (should replace)
        temp_db.insert_position({
            'symbol': 'AAPL',
            'asset_type': 'stock',
            'quantity': 15,
            'avg_entry_price': 155.0
        })
        
        positions = temp_db.get_positions(symbol='AAPL')
        assert len(positions) == 1
        assert positions.iloc[0]['quantity'] == 15
    
    def test_portfolio_snapshot(self, temp_db):
        """Test portfolio snapshot operations."""
        snapshot_id = temp_db.insert_portfolio_snapshot({
            'cash_balance': 10000.0,
            'total_position_value': 5000.0,
            'total_portfolio_value': 15000.0,
            'unrealized_pnl': 100.0,
            'realized_pnl': 200.0
        })
        
        assert snapshot_id is not None
        
        # Get latest snapshot
        latest = temp_db.get_latest_portfolio_snapshot()
        assert latest is not None
        assert latest['cash_balance'] == 10000.0
        assert latest['total_portfolio_value'] == 15000.0
        
        # Get all snapshots
        snapshots = temp_db.get_portfolio_snapshots()
        assert len(snapshots) == 1
    
    def test_trading_indexes_exist(self, temp_db):
        """Test that trading table indexes are created."""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_%'
                AND name IN (
                    'idx_price_history_symbol_time',
                    'idx_price_history_asset_time',
                    'idx_indicators_symbol_time',
                    'idx_trades_symbol_time',
                    'idx_trades_strategy',
                    'idx_positions_symbol',
                    'idx_portfolio_timestamp'
                )
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            assert 'idx_price_history_symbol_time' in indexes
            assert 'idx_price_history_asset_time' in indexes
            assert 'idx_indicators_symbol_time' in indexes
            assert 'idx_trades_symbol_time' in indexes
            assert 'idx_trades_strategy' in indexes
            assert 'idx_positions_symbol' in indexes
            assert 'idx_portfolio_timestamp' in indexes


class TestGetFixturesQueryParams:
    """Test get_fixtures filtering (home_team_id, away_team_id, dates, limit)."""

    def test_get_fixtures_filter_home_team_id(self, temp_db):
        temp_db.insert_fixture({
            "fixture_id": "f1", "home_team_id": "team_a", "away_team_id": "team_b",
            "home_team_name": "A", "away_team_name": "B",
            "start_time": "2025-01-10T12:00:00Z", "status": "scheduled"
        })
        temp_db.insert_fixture({
            "fixture_id": "f2", "home_team_id": "team_c", "away_team_id": "team_d",
            "home_team_name": "C", "away_team_name": "D",
            "start_time": "2025-01-11T12:00:00Z", "status": "scheduled"
        })
        df = temp_db.get_fixtures(home_team_id="team_a")
        assert len(df) == 1
        assert df.iloc[0]["fixture_id"] == "f1"

    def test_get_fixtures_filter_away_team_id(self, temp_db):
        temp_db.insert_fixture({
            "fixture_id": "f1", "home_team_id": "team_a", "away_team_id": "team_b",
            "home_team_name": "A", "away_team_name": "B",
            "start_time": "2025-01-10T12:00:00Z", "status": "scheduled"
        })
        temp_db.insert_fixture({
            "fixture_id": "f2", "home_team_id": "team_c", "away_team_id": "team_d",
            "home_team_name": "C", "away_team_name": "D",
            "start_time": "2025-01-11T12:00:00Z", "status": "scheduled"
        })
        df = temp_db.get_fixtures(away_team_id="team_d")
        assert len(df) == 1
        assert df.iloc[0]["fixture_id"] == "f2"

    def test_get_fixtures_empty_string_team_id_no_filter(self, temp_db):
        temp_db.insert_fixture({
            "fixture_id": "f1", "home_team_id": "team_a", "away_team_id": "team_b",
            "home_team_name": "A", "away_team_name": "B",
            "start_time": "2025-01-10T12:00:00Z", "status": "scheduled"
        })
        df = temp_db.get_fixtures(home_team_id="", away_team_id="")
        assert len(df) == 1

    def test_get_fixtures_from_date_to_date(self, temp_db):
        temp_db.insert_fixture({
            "fixture_id": "f1", "home_team_name": "A", "away_team_name": "B",
            "start_time": "2025-01-10T12:00:00Z", "status": "scheduled"
        })
        temp_db.insert_fixture({
            "fixture_id": "f2", "home_team_name": "C", "away_team_name": "D",
            "start_time": "2025-01-15T12:00:00Z", "status": "scheduled"
        })
        temp_db.insert_fixture({
            "fixture_id": "f3", "home_team_name": "E", "away_team_name": "F",
            "start_time": "2025-01-20T12:00:00Z", "status": "scheduled"
        })
        df = temp_db.get_fixtures(from_date="2025-01-12", to_date="2025-01-18")
        assert len(df) == 1
        assert df.iloc[0]["fixture_id"] == "f2"

    def test_get_fixtures_limit(self, temp_db):
        for i in range(5):
            temp_db.insert_fixture({
                "fixture_id": f"f{i}", "home_team_name": "A", "away_team_name": "B",
                "start_time": f"2025-01-{10 + i:02d}T12:00:00Z", "status": "scheduled"
            })
        df = temp_db.get_fixtures(limit=2)
        assert len(df) == 2

    def test_fixtures_indexes_home_away_team_id(self, temp_db):
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name IN
                ('idx_fixtures_home_team_id', 'idx_fixtures_away_team_id')
            """)
            names = [row[0] for row in cursor.fetchall()]
            assert "idx_fixtures_home_team_id" in names
            assert "idx_fixtures_away_team_id" in names


class TestGetScoresQueryParams:
    """Test get_scores fixture_id vs fixture_ids and edge cases."""

    def test_get_scores_fixture_ids_batch(self, temp_db):
        temp_db.insert_fixture({"fixture_id": "s1", "home_team_name": "A", "away_team_name": "B", "start_time": "2025-01-01T12:00:00Z", "status": "finished"})
        temp_db.insert_fixture({"fixture_id": "s2", "home_team_name": "C", "away_team_name": "D", "start_time": "2025-01-02T12:00:00Z", "status": "finished"})
        temp_db.insert_fixture({"fixture_id": "s3", "home_team_name": "E", "away_team_name": "F", "start_time": "2025-01-03T12:00:00Z", "status": "finished"})
        temp_db.insert_score("s1", {"home_score": 1, "away_score": 0, "status": "finished"})
        temp_db.insert_score("s2", {"home_score": 2, "away_score": 2, "status": "finished"})
        temp_db.insert_score("s3", {"home_score": 0, "away_score": 1, "status": "finished"})
        df = temp_db.get_scores(fixture_ids=["s1", "s3"])
        assert len(df) == 2
        assert set(df["fixture_id"].tolist()) == {"s1", "s3"}

    def test_get_scores_single_fixture_id_precedence(self, temp_db):
        temp_db.insert_fixture({"fixture_id": "a", "home_team_name": "A", "away_team_name": "B", "start_time": "2025-01-01T12:00:00Z", "status": "finished"})
        temp_db.insert_fixture({"fixture_id": "b", "home_team_name": "C", "away_team_name": "D", "start_time": "2025-01-02T12:00:00Z", "status": "finished"})
        temp_db.insert_score("a", {"home_score": 1, "away_score": 0, "status": "finished"})
        temp_db.insert_score("b", {"home_score": 2, "away_score": 2, "status": "finished"})
        df = temp_db.get_scores(fixture_id="b", fixture_ids=["a", "b"])
        assert len(df) == 1
        assert df.iloc[0]["fixture_id"] == "b"

    def test_get_scores_empty_fixture_ids_returns_all(self, temp_db):
        temp_db.insert_fixture({"fixture_id": "x", "home_team_name": "A", "away_team_name": "B", "start_time": "2025-01-01T12:00:00Z", "status": "finished"})
        temp_db.insert_score("x", {"home_score": 1, "away_score": 0, "status": "finished"})
        df = temp_db.get_scores(fixture_ids=[])
        assert len(df) == 1

    def test_get_scores_no_args_returns_all(self, temp_db):
        temp_db.insert_fixture({"fixture_id": "y", "home_team_name": "A", "away_team_name": "B", "start_time": "2025-01-01T12:00:00Z", "status": "finished"})
        temp_db.insert_score("y", {"home_score": 1, "away_score": 0, "status": "finished"})
        df = temp_db.get_scores()
        assert len(df) == 1
