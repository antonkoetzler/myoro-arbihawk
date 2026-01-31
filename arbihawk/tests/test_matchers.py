"""Tests for ScoreMatcher using central match_identity layer."""
import pytest
from data.matchers import ScoreMatcher
from data.database import Database


class TestScoreMatcher:
    def test_matcher_uses_central_layer_returns_fixture_id(self, temp_db):
        """Matcher uses match_identity; returns fixture_id when match above threshold."""
        temp_db.insert_fixture({
            "fixture_id": "betano_123",
            "home_team_name": "Spezia",
            "away_team_name": "Sampdoria",
            "start_time": "2025-11-30T14:00:00Z",
            "status": "scheduled",
        })
        matcher = ScoreMatcher(db=temp_db)
        fid = matcher.match_score(
            home_team="Spezia",
            away_team="Sampdoria",
            match_time="2025-11-30T14:00:00Z",
        )
        assert fid == "betano_123"

    def test_matcher_returns_none_when_no_fixtures_in_window(self, temp_db):
        """When no fixtures in time window, matcher returns None and logs reason."""
        matcher = ScoreMatcher(db=temp_db)
        fid = matcher.match_score(
            home_team="Spezia",
            away_team="Sampdoria",
            match_time="2025-11-30T14:00:00Z",
        )
        assert fid is None
        unmatched = matcher.get_unmatched()
        assert len(unmatched) == 1
        assert "no fixtures" in unmatched[0]["reason"].lower()

    def test_matcher_returns_none_when_best_below_threshold(self, temp_db):
        """When best combined score below threshold, matcher returns None."""
        temp_db.insert_fixture({
            "fixture_id": "other",
            "home_team_name": "Team X",
            "away_team_name": "Team Y",
            "start_time": "2025-11-30T14:00:00Z",
            "status": "scheduled",
        })
        matcher = ScoreMatcher(db=temp_db)
        fid = matcher.match_score(
            home_team="Spezia",
            away_team="Sampdoria",
            match_time="2025-11-30T14:00:00Z",
        )
        assert fid is None
        unmatched = matcher.get_unmatched()
        assert len(unmatched) == 1
        assert "below threshold" in unmatched[0]["reason"].lower()
