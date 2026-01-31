"""
Test suite for data ingestion flow.
Tests the complete ingestion pipeline from scraper output to database.
"""
import json
import pytest
from data.ingestion import DataIngestionService
from data.database import Database


class TestIngestionFlow:
    """Test complete ingestion flow."""
    
    def test_betano_ingestion_creates_fixtures_and_odds(self, ingestion_service, sample_betano_data, temp_db):
        """Test that Betano ingestion creates fixtures and odds correctly."""
        json_str = json.dumps(sample_betano_data)
        result = ingestion_service._ingest_json(json_str, "betano")
        
        assert result["success"] is True
        assert result["records"] == 1
        
        # Verify fixture was created
        fixture = temp_db.get_fixtures(limit=1)
        assert len(fixture) == 1
        assert fixture.iloc[0]["fixture_id"] == "test_fixture_1"
        assert fixture.iloc[0]["home_team_name"] == "Manchester United"
        
        # Verify odds were created
        odds = temp_db.get_odds(fixture_id="test_fixture_1")
        assert len(odds) == 3
        assert set(odds["outcome_name"].tolist()) == {"Home", "Draw", "Away"}
    
    def test_flashscore_ingestion_creates_fixture_for_unmatched(self, ingestion_service, sample_flashscore_data, temp_db):
        """Test that FlashScore ingestion creates fixture records for unmatched scores."""
        json_str = json.dumps(sample_flashscore_data)
        result = ingestion_service._ingest_json(json_str, "flashscore")
        
        assert result["success"] is True
        assert result["records"] == 1
        
        # Verify temp fixture was created
        temp_fixture_id = "flashscore_Manchester_United_Liverpool_2025-01-15"
        assert temp_db.fixture_exists(temp_fixture_id)
        
        # Verify score was created
        scores = temp_db.get_scores(temp_fixture_id)
        assert len(scores) == 1
        assert scores.iloc[0]["home_score"] == 2
        assert scores.iloc[0]["away_score"] == 1
    
    def test_duplicate_ingestion_prevention(self, ingestion_service, sample_betano_data, temp_db):
        """Test that duplicate ingestion is prevented by checksum."""
        json_str = json.dumps(sample_betano_data)
        
        # First ingestion
        result1 = ingestion_service._ingest_json(json_str, "betano")
        assert result1["success"] is True
        assert result1["records"] == 1
        
        # Second ingestion (should be skipped)
        result2 = ingestion_service._ingest_json(json_str, "betano")
        assert result2["success"] is True
        assert result2.get("skipped") is True
        assert result2["records"] == 0
        
        # Verify only one fixture exists
        fixtures = temp_db.get_fixtures()
        assert len(fixtures) == 1
    
    def test_ingestion_preserves_foreign_key_integrity(self, ingestion_service, sample_flashscore_data, temp_db):
        """Test that ingestion maintains foreign key integrity."""
        json_str = json.dumps(sample_flashscore_data)
        result = ingestion_service._ingest_json(json_str, "flashscore")
        
        assert result["success"] is True
        
        # Verify no orphaned records
        temp_fixture_id = "flashscore_Manchester_United_Liverpool_2025-01-15"
        
        # Score should reference existing fixture
        scores = temp_db.get_scores(temp_fixture_id)
        assert len(scores) == 1
        
        # Fixture should exist
        assert temp_db.fixture_exists(temp_fixture_id)
        
        # Check for orphaned records
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM scores s
                LEFT JOIN fixtures f ON s.fixture_id = f.fixture_id
                WHERE f.fixture_id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            assert orphaned == 0, "Found orphaned score records"
