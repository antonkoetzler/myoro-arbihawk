"""
Pytest configuration and fixtures for Arbihawk tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import Database
from data.ingestion import DataIngestionService
import config


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create temporary database file
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_arbihawk.db"
    
    # Create database instance
    db = Database(db_path=str(db_path))
    
    yield db
    
    # Cleanup - close any open connections
    try:
        with db._get_connection() as conn:
            conn.close()
    except:
        pass
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def ingestion_service(temp_db):
    """Create ingestion service with test database."""
    return DataIngestionService(db=temp_db)


@pytest.fixture
def sample_betano_data():
    """Sample Betano fixture data for testing."""
    return [
        {
            "league_id": 1,
            "league_name": "Premier League",
            "fixtures": [
                {
                    "fixture_id": "test_fixture_1",
                    "home_team_id": "1",
                    "home_team_name": "Manchester United",
                    "away_team_id": "2",
                    "away_team_name": "Liverpool",
                    "start_time": "2025-01-15T15:00:00Z",
                    "status": "scheduled",
                    "odds": [
                        {
                            "market_id": "1x2",
                            "market_name": "Match Result",
                            "outcome_id": "home",
                            "outcome_name": "Home",
                            "odds_value": 2.5
                        },
                        {
                            "market_id": "1x2",
                            "market_name": "Match Result",
                            "outcome_id": "draw",
                            "outcome_name": "Draw",
                            "odds_value": 3.2
                        },
                        {
                            "market_id": "1x2",
                            "market_name": "Match Result",
                            "outcome_id": "away",
                            "outcome_name": "Away",
                            "odds_value": 2.8
                        }
                    ]
                }
            ]
        }
    ]


@pytest.fixture
def sample_flashscore_data():
    """Sample FlashScore match data for testing."""
    return {
        "matches": [
            {
                "home_team_name": "Manchester United",
                "away_team_name": "Liverpool",
                "home_score": 2,
                "away_score": 1,
                "start_time": "2025-01-15T15:00:00Z",
                "match_date": "2025-01-15",
                "status": "finished"
            }
        ]
    }
